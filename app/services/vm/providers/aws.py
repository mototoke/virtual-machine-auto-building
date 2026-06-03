from __future__ import annotations

import asyncio

import boto3
from botocore.config import Config

from app.config import settings
from app.services.vm.models import VirtualMachine, VmPowerAction, VmPowerState, VmProvider, VmResizeSpec
from app.services.vm.providers.base import VmProviderBackend

_INSTANCE_CPU_MEM: dict[str, tuple[int, int]] = {
    "t3.micro": (2, 1024),
    "t3.small": (2, 2048),
    "t3.medium": (2, 4096),
    "t3.large": (2, 8192),
}


def _client():
    return boto3.client(
        "ec2",
        endpoint_url=settings.aws_endpoint_url,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_default_region,
        config=Config(retries={"max_attempts": 2}),
    )


def _state_map(name: str) -> VmPowerState:
    mapping = {
        "running": VmPowerState.running,
        "stopped": VmPowerState.stopped,
        "stopping": VmPowerState.running,
        "pending": VmPowerState.stopped,
    }
    return mapping.get(name, VmPowerState.unknown)


def _list_sync() -> list[VirtualMachine]:
    ec2 = _client()
    resp = ec2.describe_instances()
    vms: list[VirtualMachine] = []
    for res in resp.get("Reservations", []):
        for inst in res.get("Instances", []):
            iid = inst["InstanceId"]
            itype = inst.get("InstanceType", "t3.micro")
            cpus, mem = _INSTANCE_CPU_MEM.get(itype, (1, 1024))
            name = iid
            for tag in inst.get("Tags") or []:
                if tag.get("Key") == "Name":
                    name = tag["Value"]
                    break
            vms.append(
                VirtualMachine(
                    provider=VmProvider.aws,
                    external_id=iid,
                    name=name,
                    power_state=_state_map(inst.get("State", {}).get("Name", "unknown")),
                    cpus=cpus,
                    memory_mb=mem,
                    disk_gb=8,
                    extra={"instance_type": itype},
                )
            )
    return vms


def _get_sync(external_id: str) -> VirtualMachine | None:
    for vm in _list_sync():
        if vm.external_id == external_id:
            return vm
    return None


def _power_sync(external_id: str, action: VmPowerAction) -> None:
    ec2 = _client()
    if action == VmPowerAction.start:
        ec2.start_instances(InstanceIds=[external_id])
    elif action in (VmPowerAction.stop, VmPowerAction.shutdown):
        ec2.stop_instances(InstanceIds=[external_id])
    elif action == VmPowerAction.reboot:
        ec2.reboot_instances(InstanceIds=[external_id])
    elif action == VmPowerAction.reset:
        ec2.stop_instances(InstanceIds=[external_id])
        waiter = ec2.get_waiter("instance_stopped")
        waiter.wait(InstanceIds=[external_id])
        ec2.start_instances(InstanceIds=[external_id])
    else:
        raise ValueError(action)


def _resize_sync(external_id: str, spec: VmResizeSpec) -> VirtualMachine:
    ec2 = _client()
    if spec.cpus is not None or spec.memory_mb is not None:
        target = _pick_instance_type(spec.cpus, spec.memory_mb)
        ec2.modify_instance_attribute(
            InstanceId=external_id,
            InstanceType={"Value": target},
        )
    if spec.disk_gb is not None:
        vols = ec2.describe_instances(InstanceIds=[external_id])["Reservations"][0]["Instances"][0][
            "BlockDeviceMappings"
        ]
        for bdm in vols:
            if "Ebs" in bdm:
                ec2.modify_volume(VolumeId=bdm["Ebs"]["VolumeId"], Size=spec.disk_gb)
                break
    vm = _get_sync(external_id)
    if not vm:
        raise ValueError("instance not found")
    return vm


def _pick_instance_type(cpus: int | None, memory_mb: int | None) -> str:
    cpus = cpus or 2
    memory_mb = memory_mb or 1024
    best = "t3.micro"
    for itype, (c, m) in _INSTANCE_CPU_MEM.items():
        if c >= cpus and m >= memory_mb:
            best = itype
    return best


class AwsBackend(VmProviderBackend):
    name = VmProvider.aws.value

    async def list_vms(self) -> list[VirtualMachine]:
        return await asyncio.to_thread(_list_sync)

    async def get_vm(self, external_id: str) -> VirtualMachine | None:
        return await asyncio.to_thread(_get_sync, external_id)

    async def power(self, external_id: str, action: VmPowerAction) -> None:
        await asyncio.to_thread(_power_sync, external_id, action)

    async def resize(self, external_id: str, spec: VmResizeSpec) -> VirtualMachine:
        return await asyncio.to_thread(_resize_sync, external_id, spec)
