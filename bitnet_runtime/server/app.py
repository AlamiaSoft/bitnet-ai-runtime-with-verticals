from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from ..config import config
from ..logging import logger
from pathlib import Path
from fastapi.responses import FileResponse, RedirectResponse
from .routes.agents import router as agents_router
from .routes.execution import router as execution_router
from .routes.garden import router as garden_router
from .routes.memory import router as memory_router
from .routes.router import router as router_routes
from .routes.webhooks import router as webhooks_router
from .sse import broadcaster

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Alamia Local AI Runtime Server...")
    yield
    logger.info("Shutting down Alamia Local AI Runtime Server...")

def create_app() -> FastAPI:
    app = FastAPI(
        title="Alamia Local AI Runtime API",
        description="A local-first AI runtime for running capable AI models on everyday hardware — without requiring a GPU or cloud AI APIs.",
        version="0.2.0",
        docs_url="/docs" if config.server.enable_docs else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(agents_router, prefix="/api/v1")
    app.include_router(memory_router, prefix="/api/v1")
    app.include_router(webhooks_router, prefix="/api/v1")
    app.include_router(garden_router)
    app.include_router(router_routes)
    app.include_router(execution_router)

    dashboard_file = Path(__file__).parent / "static" / "dashboard.html"

    @app.get("/", tags=["Dashboard"])
    async def root():
        if dashboard_file.exists():
            return FileResponse(dashboard_file)
        return {"status": "Alamia Local AI Runtime is running."}

    @app.get("/dashboard", tags=["Dashboard"])
    async def dashboard():
        if dashboard_file.exists():
            return FileResponse(dashboard_file)
        return {"error": "Dashboard static file not found."}

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "healthy", "runtime": config.runtime.name, "provider": config.inference.default_provider}

    @app.get("/events", tags=["Events"])
    async def stream_events():
        return EventSourceResponse(broadcaster.subscribe())

    return app
