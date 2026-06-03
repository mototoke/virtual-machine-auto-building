import uuid

from fastapi import APIRouter, Depends, Form
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import Project

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str | None
    rustfs_terraform_prefix: str
    rustfs_ansible_prefix: str

    model_config = {"from_attributes": True}


@router.get("", response_model=list[ProjectOut])
async def list_projects(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=ProjectOut)
async def create_project(body: ProjectCreate, session: AsyncSession = Depends(get_session)):
    project_id = uuid.uuid4().hex[:12]
    project = Project(
        id=project_id,
        name=body.name,
        description=body.description,
        rustfs_terraform_prefix=f"projects/terraform/{project_id}/",
        rustfs_ansible_prefix=f"projects/ansible/{project_id}/",
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project


@router.post("/form", response_class=None)
async def create_project_form(
    name: str = Form(...),
    description: str | None = Form(None),
    session: AsyncSession = Depends(get_session),
):
    """htmx フォーム POST 用（JSON 不要）。"""
    body = ProjectCreate(name=name, description=description or None)
    return await create_project(body, session)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, session: AsyncSession = Depends(get_session)):
    project = await session.get(Project, project_id)
    if not project:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.get("/{project_id}/upload-hints")
async def upload_hints(project_id: str):
    bucket = settings.rustfs_bucket_projects
    return {
        "bucket": bucket,
        "terraform_prefix": f"projects/terraform/{project_id}/",
        "ansible_prefix": f"projects/ansible/{project_id}/",
        "note": "RustFS に main.tf / playbook.yml を配置すると worker が自動実行します",
    }
