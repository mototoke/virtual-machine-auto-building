from app.services.vm.manager import VmManager
from app.services.vm.models import VmResizeSpec


def test_parse_uid():
    p, ext = VmManager.parse_uid("proxmox:pve-node1/100")
    assert p.value == "proxmox"
    assert ext == "pve-node1/100"


def test_resize_spec_requires_fields():
    spec = VmResizeSpec(cpus=2, memory_mb=2048)
    assert spec.cpus == 2
    assert spec.disk_gb is None
