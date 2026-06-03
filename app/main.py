from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import htmx, projects, provision_runs, vms
from app.db import init_db

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="VM Provision System",
    description="自働仮想マシン払い出し — htmx + FastAPI",
    lifespan=lifespan,
)

static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(htmx.router, prefix="/api", tags=["htmx"])
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(provision_runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(vms.router, prefix="/api/vms", tags=["vms"])


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"title": "VM 払い出しダッシュボード"},
    )


@app.get("/vms", response_class=HTMLResponse)
async def vms_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="vms/list.html",
        context={"title": "仮想マシン管理"},
    )


@app.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="projects/list.html",
        context={"title": "プロジェクト一覧"},
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
