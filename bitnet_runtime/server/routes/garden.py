from __future__ import annotations
import asyncio
import json
from dataclasses import asdict
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from ...model_garden import (
    HardwareDiscoveryEngine,
    ModelGarden,
    ModelLifecycleManager,
    ModelModality,
    ModelStatus,
)

router = APIRouter(prefix="/api/v1/garden", tags=["Model Garden"])

garden = ModelGarden()
hardware_engine = HardwareDiscoveryEngine()
lifecycle_manager = ModelLifecycleManager(garden=garden)

@router.get("/models")
async def list_garden_models(
    modality: Optional[str] = None,
    max_ram_mb: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """List all catalog models with lifecycle status and hardware compatibility."""
    manifests = garden.list_all()
    if modality:
        manifests = [m for m in manifests if m.modality.value == modality]
    if max_ram_mb:
        manifests = [m for m in manifests if m.hardware.min_ram_mb <= max_ram_mb]

    results = []
    for m in manifests:
        status = lifecycle_manager.get_status(m.model_id)
        compat = hardware_engine.evaluate_compatibility(m)
        progress = lifecycle_manager.get_download_progress(m.model_id)

        item = {
            "model_id": m.model_id,
            "name": m.name,
            "family": m.family.value,
            "modality": m.modality.value,
            "tier": m.tier.value,
            "parameter_size": m.parameter_size,
            "context_window": m.context_window,
            "hardware": asdict(m.hardware),
            "provider_backend": m.provider_backend,
            "task_ratings": {k.value: v for k, v in m.task_ratings.items()},
            "typical_latency_ms": m.typical_latency_ms,
            "license": m.license,
            "description": m.description,
            "status": status.value,
            "compatibility": asdict(compat),
            "download_progress": asdict(progress) if progress else None,
        }
        results.append(item)
    return results

@router.get("/hardware")
async def get_hardware_diagnostics() -> Dict[str, Any]:
    """Return host CPU, RAM, and hardware acceleration capabilities."""
    profile = hardware_engine.get_profile()
    return asdict(profile)

@router.get("/storage")
async def get_storage_statistics() -> Dict[str, Any]:
    """Return on-disk models storage usage and free disk space."""
    stats = lifecycle_manager.get_storage_stats()
    return asdict(stats)

@router.post("/models/{model_id}/install")
async def install_model_endpoint(
    model_id: str,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """Trigger async background installation for a model."""
    manifest = garden.get(model_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    status = lifecycle_manager.get_status(model_id)
    if status == ModelStatus.DOWNLOADING:
        return {"status": "already_downloading", "model_id": model_id}

    background_tasks.add_task(lifecycle_manager.install_model, model_id)
    return {"status": "install_initiated", "model_id": model_id}

@router.delete("/models/{model_id}")
async def uninstall_model_endpoint(model_id: str) -> Dict[str, Any]:
    """Uninstall and delete model weights from local disk."""
    manifest = garden.get(model_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    success = lifecycle_manager.uninstall_model(model_id)
    return {"status": "uninstalled" if success else "error", "model_id": model_id}

@router.get("/models/{model_id}/events")
async def stream_model_progress(model_id: str):
    """Server-Sent Events (SSE) live stream for download/verification progress."""
    async def event_generator():
        async for prog in lifecycle_manager.subscribe_progress(model_id):
            data = json.dumps(asdict(prog))
            yield {"event": "progress", "data": data}
            yield {"event": "message", "data": data}
            await asyncio.sleep(0.01)

    return EventSourceResponse(event_generator())
