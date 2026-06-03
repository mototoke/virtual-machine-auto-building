"""
パイプライン worker: RustFS イベント → Terraform apply → Ansible playbook
"""
from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI
from pydantic import BaseModel

from worker.pipeline import run_pipeline

app = FastAPI(title="VM Provision Worker", docs_url="/docs")


class TriggerPayload(BaseModel):
    bucket: str
    key: str
    etag: str | None = None
    project_id: str
    stage: str  # terraform | ansible


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/internal/pipeline/trigger")
async def trigger(payload: TriggerPayload, background_tasks: BackgroundTasks):
    run_id = uuid.uuid4().hex[:16]
    work_dir = Path(os.environ.get("PIPELINE_WORK_DIR", "/tmp/pipeline-runs")) / run_id
    background_tasks.add_task(_run_safe, payload, work_dir, run_id)
    return {"accepted": True, "run_id": run_id, "project_id": payload.project_id}


async def _run_safe(payload: TriggerPayload, work_dir: Path, run_id: str) -> None:
    try:
        await asyncio.to_thread(run_pipeline, payload.model_dump(), work_dir, run_id)
    except Exception as exc:  # noqa: BLE001
        print(f"pipeline {run_id} failed: {exc}")
