from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import ProvisionRun, ProvisionStatus

router = APIRouter()


class RunOut(BaseModel):
    id: str
    project_id: str
    status: ProvisionStatus
    trigger_key: str | None
    log_summary: str | None

    model_config = {"from_attributes": True}


@router.get("", response_model=list[RunOut])
async def list_runs(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ProvisionRun).order_by(ProvisionRun.created_at.desc()).limit(50))
    return result.scalars().all()


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)):
    run = await session.get(ProvisionRun, run_id)
    if not run:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="run not found")
    return run
