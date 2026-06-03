from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Project, ProvisionRun
from app.services.vm.manager import vm_manager

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/partials/projects", response_class=HTMLResponse)
async def partial_projects(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    return templates.TemplateResponse(
        request=request,
        name="partials/projects.html",
        context={"projects": projects},
    )


@router.get("/partials/vms", response_class=HTMLResponse)
async def partial_vms(request: Request):
    vms = await vm_manager.list_all()
    return templates.TemplateResponse(
        request=request,
        name="partials/vms.html",
        context={"vms": vms},
    )


@router.get("/partials/runs", response_class=HTMLResponse)
async def partial_runs(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ProvisionRun).order_by(ProvisionRun.created_at.desc()).limit(20))
    runs = result.scalars().all()
    return templates.TemplateResponse(
        request=request,
        name="partials/runs.html",
        context={"runs": runs},
    )
