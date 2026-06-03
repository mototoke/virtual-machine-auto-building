from abc import ABC, abstractmethod

from app.services.vm.models import VirtualMachine, VmPowerAction, VmResizeSpec


class VmProviderBackend(ABC):
    name: str

    @abstractmethod
    async def list_vms(self) -> list[VirtualMachine]:
        raise NotImplementedError

    @abstractmethod
    async def get_vm(self, external_id: str) -> VirtualMachine | None:
        raise NotImplementedError

    @abstractmethod
    async def power(self, external_id: str, action: VmPowerAction) -> None:
        raise NotImplementedError

    @abstractmethod
    async def resize(self, external_id: str, spec: VmResizeSpec) -> VirtualMachine:
        raise NotImplementedError
