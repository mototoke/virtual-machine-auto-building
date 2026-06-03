from __future__ import annotations

import logging

from app.services.vm.models import VirtualMachine, VmPowerAction, VmProvider, VmResizeSpec
from app.services.vm.providers.aws import AwsBackend
from app.services.vm.providers.base import VmProviderBackend
from app.services.vm.providers.proxmox import ProxmoxBackend
from app.services.vm.providers.vsphere import VsphereBackend

logger = logging.getLogger(__name__)


class VmManager:
    def __init__(self) -> None:
        self._backends: dict[VmProvider, VmProviderBackend] = {
            VmProvider.proxmox: ProxmoxBackend(),
            VmProvider.vsphere: VsphereBackend(),
            VmProvider.aws: AwsBackend(),
        }

    def _backend(self, provider: VmProvider) -> VmProviderBackend:
        b = self._backends.get(provider)
        if not b:
            raise ValueError(f"Unknown provider: {provider}")
        return b

    @staticmethod
    def parse_uid(uid: str) -> tuple[VmProvider, str]:
        if ":" not in uid:
            raise ValueError(f"Invalid VM uid: {uid}")
        prov, ext = uid.split(":", 1)
        return VmProvider(prov), ext

    async def list_all(self) -> list[VirtualMachine]:
        results: list[VirtualMachine] = []
        for provider, backend in self._backends.items():
            try:
                results.extend(await backend.list_vms())
            except Exception as exc:  # noqa: BLE001
                logger.warning("list_vms failed for %s: %s", provider.value, exc)
        return sorted(results, key=lambda v: (v.provider.value, v.name))

    async def get(self, uid: str) -> VirtualMachine | None:
        provider, ext = self.parse_uid(uid)
        return await self._backend(provider).get_vm(ext)

    async def power(self, uid: str, action: VmPowerAction) -> None:
        provider, ext = self.parse_uid(uid)
        await self._backend(provider).power(ext, action)

    async def resize(self, uid: str, spec: VmResizeSpec) -> VirtualMachine:
        provider, ext = self.parse_uid(uid)
        return await self._backend(provider).resize(ext, spec)


vm_manager = VmManager()
