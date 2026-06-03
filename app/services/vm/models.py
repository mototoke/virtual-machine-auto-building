from enum import Enum

from pydantic import BaseModel, Field


class VmProvider(str, Enum):
    proxmox = "proxmox"
    vsphere = "vsphere"
    aws = "aws"


class VmPowerState(str, Enum):
    running = "running"
    stopped = "stopped"
    paused = "paused"
    unknown = "unknown"


class VirtualMachine(BaseModel):
    """プロバイダ横断の VM 表現。external_id はプロバイダ固有（例: pve-node1/101）。"""

    provider: VmProvider
    external_id: str
    name: str
    power_state: VmPowerState = VmPowerState.unknown
    cpus: int | None = None
    memory_mb: int | None = None
    disk_gb: int | None = None
    extra: dict = Field(default_factory=dict)

    @property
    def uid(self) -> str:
        return f"{self.provider.value}:{self.external_id}"


class VmResizeSpec(BaseModel):
    cpus: int | None = Field(None, ge=1, le=512)
    memory_mb: int | None = Field(None, ge=128, le=4_194_304)
    disk_gb: int | None = Field(None, ge=1, le=64_000)


class VmPowerAction(str, Enum):
    start = "start"
    stop = "stop"
    shutdown = "shutdown"
    reboot = "reboot"
    reset = "reset"
