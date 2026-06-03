from __future__ import annotations

import asyncio
import ssl
from urllib.parse import urlparse

from pyVim.connect import Disconnect, SmartConnect
from pyVmomi import vim

from app.config import settings
from app.services.vm.models import VirtualMachine, VmPowerAction, VmPowerState, VmProvider, VmResizeSpec
from app.services.vm.providers.base import VmProviderBackend

_POWER_MAP = {
    "poweredOn": VmPowerState.running,
    "poweredOff": VmPowerState.stopped,
    "suspended": VmPowerState.paused,
}


def _connect():
    parsed = urlparse(settings.vsphere_url)
    host = parsed.hostname or "vcsim"
    port = parsed.port or (443 if parsed.scheme == "https" else 8989)
    path = (parsed.path or "/sdk").rstrip("/")
    if not path.endswith("/sdk"):
        path = path + "/sdk" if path else "/sdk"

    ctx = ssl.create_default_context()
    if settings.vsphere_insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    return SmartConnect(
        host=host,
        port=port,
        user=settings.vsphere_user,
        pwd=settings.vsphere_password,
        sslContext=ctx,
        path=path,
    )


def _list_vms_sync() -> list[VirtualMachine]:
    si = _connect()
    try:
        content = si.RetrieveContent()
        container = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.VirtualMachine], True
        )
        vms: list[VirtualMachine] = []
        for vm in container.view:
            summary = vm.summary
            cfg = vm.config
            runtime = summary.runtime
            power = _POWER_MAP.get(runtime.powerState, VmPowerState.unknown)
            disk_gb = None
            if cfg.hardware.device:
                for dev in cfg.hardware.device:
                    if isinstance(dev, vim.vm.device.VirtualDisk):
                        disk_gb = max(disk_gb or 0, dev.capacityInKB // (1024 * 1024))
            vms.append(
                VirtualMachine(
                    provider=VmProvider.vsphere,
                    external_id=vm._moId,
                    name=summary.config.name,
                    power_state=power,
                    cpus=cfg.hardware.numCPU,
                    memory_mb=cfg.hardware.memoryMB,
                    disk_gb=disk_gb,
                    extra={"uuid": cfg.uuid},
                )
            )
        container.Destroy()
        return vms
    finally:
        Disconnect(si)


def _get_vm_sync(external_id: str) -> VirtualMachine | None:
    for vm in _list_vms_sync():
        if vm.external_id == external_id:
            return vm
    return None


def _find_vm(si, external_id: str):
    content = si.RetrieveContent()
    container = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    try:
        for vm in container.view:
            if vm._moId == external_id:
                return vm
        return None
    finally:
        container.Destroy()


def _power_sync(external_id: str, action: VmPowerAction) -> None:
    si = _connect()
    try:
        vm = _find_vm(si, external_id)
        if vm is None:
            raise ValueError(f"VM not found: {external_id}")
        if action == VmPowerAction.start:
            task = vm.PowerOnVM_Task()
        elif action in (VmPowerAction.stop, VmPowerAction.shutdown):
            task = vm.PowerOffVM_Task()
        elif action == VmPowerAction.reboot:
            task = vm.RebootGuest()
            if task is None:
                vm.ResetVM_Task()
                return
        elif action == VmPowerAction.reset:
            task = vm.ResetVM_Task()
        else:
            raise ValueError(f"Unsupported action: {action}")
        _wait_task(task)
    finally:
        Disconnect(si)


def _resize_sync(external_id: str, spec: VmResizeSpec) -> VirtualMachine:
    si = _connect()
    try:
        vm = _find_vm(si, external_id)
        if vm is None:
            raise ValueError(f"VM not found: {external_id}")
        spec_obj = vim.vm.ConfigSpec()
        if spec.cpus is not None:
            spec_obj.numCPUs = spec.cpus
        if spec.memory_mb is not None:
            spec_obj.memoryMB = spec.memory_mb
        if spec.disk_gb is not None:
            for dev in vm.config.hardware.device:
                if isinstance(dev, vim.vm.device.VirtualDisk):
                    spec_obj.deviceChange = [
                        vim.vm.device.VirtualDeviceSpec(
                            operation=vim.vm.device.VirtualDeviceSpec.Operation.edit,
                            device=dev,
                        )
                    ]
                    dev.capacityInKB = spec.disk_gb * 1024 * 1024
                    break
        if spec_obj.numCPUs or spec_obj.memoryMB or spec_obj.deviceChange:
            task = vm.ReconfigVM_Task(spec=spec_obj)
            _wait_task(task)
    finally:
        Disconnect(si)
    vm_out = _get_vm_sync(external_id)
    if not vm_out:
        raise ValueError("VM not found after resize")
    return vm_out


def _wait_task(task) -> None:
    if task is None:
        return
    while task.info.state not in (vim.TaskInfo.State.success, vim.TaskInfo.State.error):
        pass
    if task.info.state == vim.TaskInfo.State.error:
        raise RuntimeError(task.info.error.msg if task.info.error else "vSphere task failed")


class VsphereBackend(VmProviderBackend):
    name = VmProvider.vsphere.value

    async def list_vms(self) -> list[VirtualMachine]:
        return await asyncio.to_thread(_list_vms_sync)

    async def get_vm(self, external_id: str) -> VirtualMachine | None:
        return await asyncio.to_thread(_get_vm_sync, external_id)

    async def power(self, external_id: str, action: VmPowerAction) -> None:
        await asyncio.to_thread(_power_sync, external_id, action)

    async def resize(self, external_id: str, spec: VmResizeSpec) -> VirtualMachine:
        return await asyncio.to_thread(_resize_sync, external_id, spec)
