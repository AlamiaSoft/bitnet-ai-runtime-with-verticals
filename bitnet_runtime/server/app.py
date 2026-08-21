from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from ..config import config
from ..logging import logger
from .routes.agents import router as agents_router
from .routes.memory import router as memory_router
from .routes.webhooks import router as webhooks_router
from .sse import broadcaster

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting BitNet AI Runtime Local Server...")
    yield
    logger.info("Shutting down BitNet AI Runtime Local Server...")

def create_app() -> FastAPI:
    app = FastAPI(
        title="BitNet AI Runtime API",
        description="Local-First, Zero-Cloud-Cost AI Agent Runtime",
        version="0.1.0",
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

    @app.get("/health", tags=["Health"])
    async def health():
        return {"status": "healthy", "runtime": config.runtime.name, "provider": config.inference.default_provider}

    @app.get("/events", tags=["Events"])
    async def stream_events():
        return EventSourceResponse(broadcaster.subscribe())

    return app
