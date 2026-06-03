from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

import httpx

from app.config import settings
from app.services.vm.models import VirtualMachine, VmPowerAction, VmPowerState, VmProvider, VmResizeSpec
from app.services.vm.providers.base import VmProviderBackend

_POWER_MAP = {
    "running": VmPowerState.running,
    "stopped": VmPowerState.stopped,
    "paused": VmPowerState.paused,
}


class ProxmoxBackend(VmProviderBackend):
    name = VmProvider.proxmox.value

    def __init__(self) -> None:
        self._base = settings.proxmox_api_url.rstrip("/") + "/api2/json"
        self._token = getattr(settings, "proxmox_api_token", None) or ""

    def _headers(self) -> dict[str, str]:
        if self._token:
            return {"Authorization": f"PVEAPIToken={self._token}"}
        return {}

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            verify=False if settings.proxmox_insecure else True,
            timeout=30.0,
            headers=self._headers(),
        )

    async def _ticket_auth(self, client: httpx.AsyncClient) -> None:
        if self._token:
            return
        resp = await client.post(
            f"{self._base}/access/ticket",
            data={"username": settings.proxmox_user, "password": settings.proxmox_password},
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        client.cookies.set("PVEAuthCookie", data["ticket"])
        client.headers["CSRFPreventionToken"] = data["CSRFPreventionToken"]

    async def _get(self, client: httpx.AsyncClient, path: str) -> Any:
        r = await client.get(urljoin(self._base + "/", path.lstrip("/")))
        r.raise_for_status()
        return r.json().get("data")

    async def _post(self, client: httpx.AsyncClient, path: str, data: dict | None = None) -> Any:
        r = await client.post(urljoin(self._base + "/", path.lstrip("/")), data=data or {})
        r.raise_for_status()
        return r.json().get("data")

    async def _put(self, client: httpx.AsyncClient, path: str, data: dict) -> Any:
        r = await client.put(urljoin(self._base + "/", path.lstrip("/")), data=data)
        r.raise_for_status()
        return r.json().get("data")

    def _parse_ref(self, external_id: str) -> tuple[str, int]:
        if "/" in external_id:
            node, vmid = external_id.split("/", 1)
            return node, int(vmid)
        node, vmid = external_id.split("-", 1)
        return node, int(vmid)

    async def list_vms(self, *, _seed_attempted: bool = False) -> list[VirtualMachine]:
        async with self._build_client() as client:
            await self._ticket_auth(client)
            nodes = await self._get(client, "/nodes") or []
            vms: list[VirtualMachine] = []
            for node_info in nodes:
                node = node_info["node"]
                for item in await self._get(client, f"/nodes/{node}/qemu") or []:
                    vmid = item["vmid"]
                    ext = f"{node}/{vmid}"
                    detail = await self._get_vm_with_client(client, ext)
                    if detail:
                        vms.append(detail)
            if not vms and not _seed_attempted:
                await self._ensure_demo(client)
                return await self.list_vms(_seed_attempted=True)
            return vms

    async def _get_vm_with_client(self, client: httpx.AsyncClient, external_id: str) -> VirtualMachine | None:
        node, vmid = self._parse_ref(external_id)
        try:
            cfg = await self._get(client, f"/nodes/{node}/qemu/{vmid}/config")
            status = await self._get(client, f"/nodes/{node}/qemu/{vmid}/status/current")
        except httpx.HTTPStatusError:
            return None
        power = _POWER_MAP.get((status or {}).get("status", "unknown"), VmPowerState.unknown)
        disk_gb = _disk_gb_from_config(cfg or {})
        return VirtualMachine(
            provider=VmProvider.proxmox,
            external_id=f"{node}/{vmid}",
            name=(cfg or {}).get("name") or f"vm-{vmid}",
            power_state=power,
            cpus=int((cfg or {}).get("cores", 1)),
            memory_mb=int((cfg or {}).get("memory", 512)),
            disk_gb=disk_gb,
            extra={"node": node, "vmid": vmid},
        )

    async def _ensure_demo(self, client: httpx.AsyncClient) -> None:
        try:
            await self._post(
                client,
                "/nodes/pve-node1/qemu",
                {
                    "vmid": 100,
                    "name": "demo-vm",
                    "cores": 1,
                    "memory": 512,
                    "scsi0": "local-lvm:8",
                    "net0": "virtio,bridge=vmbr0",
                },
            )
        except httpx.HTTPError:
            pass

    async def get_vm(self, external_id: str) -> VirtualMachine | None:
        async with self._build_client() as client:
            await self._ticket_auth(client)
            return await self._get_vm_with_client(client, external_id)

    async def power(self, external_id: str, action: VmPowerAction) -> None:
        node, vmid = self._parse_ref(external_id)
        pve_action = action.value
        if action == VmPowerAction.reset:
            pve_action = "reset"
        async with self._build_client() as client:
            await self._ticket_auth(client)
            await self._post(client, f"/nodes/{node}/qemu/{vmid}/status/{pve_action}")

    async def resize(self, external_id: str, spec: VmResizeSpec) -> VirtualMachine:
        node, vmid = self._parse_ref(external_id)
        async with self._build_client() as client:
            await self._ticket_auth(client)
            payload: dict[str, str] = {}
            if spec.cpus is not None:
                payload["cores"] = str(spec.cpus)
            if spec.memory_mb is not None:
                payload["memory"] = str(spec.memory_mb)
            if payload:
                await self._put(client, f"/nodes/{node}/qemu/{vmid}/config", payload)
            if spec.disk_gb is not None:
                cfg = await self._get(client, f"/nodes/{node}/qemu/{vmid}/config")
                disk_key = _first_disk_key(cfg or {})
                if disk_key:
                    await self._post(
                        client,
                        f"/nodes/{node}/qemu/{vmid}/resize",
                        {"disk": disk_key, "size": f"{spec.disk_gb}G"},
                    )
        vm = await self.get_vm(external_id)
        if not vm:
            raise ValueError(f"VM not found after resize: {external_id}")
        return vm


def _first_disk_key(cfg: dict) -> str | None:
    for k in cfg:
        if re.match(r"^(scsi|virtio|sata|ide)\d+$", k):
            return k
    return None


def _disk_gb_from_config(cfg: dict) -> int | None:
    key = _first_disk_key(cfg)
    if not key:
        return None
    raw = str(cfg.get(key, ""))
    m = re.search(r":(\d+)(?:\s|$)", raw) or re.search(r"size=(\d+)G", raw, re.I)
    if m:
        return int(m.group(1))
    m2 = re.search(r"(\d+)G", raw, re.I)
    return int(m2.group(1)) if m2 else None
