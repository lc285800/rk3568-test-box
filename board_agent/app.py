from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .config import Settings, load_settings
from .events import EventBus
from .models import HealthResponse, Resources, SystemInfo, TaskRecord, TaskRequest, TaskResponse
from .probes import get_resources, get_system_info
from .tasks import TaskManager


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    events = EventBus()
    tasks = TaskManager(events=events, mock_mode=settings.mock_mode)

    app = FastAPI(title="RK3568 Test Box Board Agent", version=__version__)
    app.state.settings = settings
    app.state.events = events
    app.state.tasks = tasks

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service="rk3568-test-box-board-agent",
            version=__version__,
            mode=settings.mode,
        )

    @app.get("/api/system", response_model=SystemInfo)
    async def system_info() -> SystemInfo:
        return get_system_info(mock=settings.mock_mode)

    @app.get("/api/resources", response_model=Resources)
    async def resources() -> Resources:
        return get_resources(mock=settings.mock_mode)

    @app.post("/api/tasks", response_model=TaskResponse)
    async def create_task(request: TaskRequest) -> TaskResponse:
        return tasks.create(request)

    @app.get("/api/tasks/{task_id}", response_model=TaskRecord)
    async def get_task(task_id: str) -> TaskRecord:
        record = tasks.get(task_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return record

    @app.websocket("/ws/events")
    async def websocket_events(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            async for event in events.subscribe():
                await websocket.send_json(event)
        except WebSocketDisconnect:
            return

    static_dir = settings.static_dir
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get("/", include_in_schema=False)
        async def index() -> FileResponse:
            return FileResponse(static_dir / "index.html")

    else:
        @app.get("/", include_in_schema=False)
        async def missing_index() -> dict[str, str]:
            return {"message": f"Static directory not found: {static_dir}"}

    return app


def main() -> None:
    settings = load_settings()
    static_dir = Path(settings.static_dir)
    uvicorn.run(
        "board_agent.app:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        reload=False,
        app_dir=str(Path.cwd()),
    )
