from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.vm.manager import vm_manager
from app.services.vm.models import VmPowerAction, VmProvider, VmResizeSpec

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("", response_model=list)
async def list_vms_json():
    vms = await vm_manager.list_all()
    return [v.model_dump() for v in vms]


@router.get("/partials/detail/{provider}/{external_id:path}", response_class=HTMLResponse)
async def vm_detail_partial(request: Request, provider: str, external_id: str):
    uid = f"{provider}:{external_id}"
    vm = await vm_manager.get(uid)
    if not vm:
        return HTMLResponse("<p class='muted'>VM が見つかりません。</p>", status_code=404)
    return templates.TemplateResponse(
        request=request,
        name="partials/vm_detail.html",
        context={"vm": vm, "power_actions": _available_power(vm.power_state.value)},
    )


@router.get("/{provider}/{external_id:path}", response_model=dict)
async def get_vm_json(provider: str, external_id: str):
    try:
        p = VmProvider(provider)
    except ValueError as exc:
        raise HTTPException(400, "invalid provider") from exc
    uid = f"{p.value}:{external_id}"
    vm = await vm_manager.get(uid)
    if not vm:
        raise HTTPException(404, "VM not found")
    return vm.model_dump()


@router.post("/{provider}/{external_id:path}/power/{action}")
async def vm_power(
    request: Request,
    provider: str,
    external_id: str,
    action: str,
):
    try:
        p = VmProvider(provider)
        act = VmPowerAction(action)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    uid = f"{p.value}:{external_id}"
    try:
        await vm_manager.power(uid, act)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"power action failed: {exc}") from exc

    if request.headers.get("HX-Request"):
        return await vm_detail_partial(request, provider, external_id)
    return {"ok": True, "uid": uid, "action": act.value}


@router.post("/{provider}/{external_id:path}/resize")
async def vm_resize(
    request: Request,
    provider: str,
    external_id: str,
    cpus: int | None = Form(None),
    memory_mb: int | None = Form(None),
    disk_gb: int | None = Form(None),
):
    try:
        VmProvider(provider)
    except ValueError as exc:
        raise HTTPException(400, "invalid provider") from exc
    if cpus is None and memory_mb is None and disk_gb is None:
        raise HTTPException(400, "at least one of cpus, memory_mb, disk_gb required")
    uid = f"{provider}:{external_id}"
    spec = VmResizeSpec(cpus=cpus, memory_mb=memory_mb, disk_gb=disk_gb)
    try:
        vm = await vm_manager.resize(uid, spec)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"resize failed: {exc}") from exc

    if request.headers.get("HX-Request"):
        return await vm_detail_partial(request, provider, external_id)
    return vm.model_dump()


def _available_power(state: str) -> list[str]:
    if state == "running":
        return ["stop", "shutdown", "reboot", "reset"]
    if state == "stopped":
        return ["start"]
    return ["start", "stop"]
