from __future__ import annotations
from dataclasses import asdict
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from ...execution import execution_registry
from ...model_garden import ModelGarden, ModelLifecycleManager

router = APIRouter(prefix="/api/v1/execution", tags=["Execution Fabric"])

garden = ModelGarden()
lifecycle = ModelLifecycleManager(garden=garden)

@router.get("/backends")
async def get_backend_health() -> Dict[str, Any]:
    """Get real-time operational health of all serving backends (llama.cpp, TEI, bitnet-server)."""
    statuses = await execution_registry.get_all_health()
    return {
        "backends": {k: asdict(v) for k, v in statuses.items()},
        "total_loaded_models": len(execution_registry.get_loaded_models()),
        "total_ram_used_mb": round(execution_registry.get_total_ram_used_mb(), 2),
    }

@router.get("/memory")
async def get_memory_breakdown() -> Dict[str, Any]:
    """Get detailed active RAM allocations per loaded model instance."""
    loaded = execution_registry.get_loaded_models()
    return {
        "total_ram_used_mb": round(execution_registry.get_total_ram_used_mb(), 2),
        "instances": [asdict(inst) for inst in loaded],
    }

@router.post("/models/{model_id}/load")
async def load_model_to_ram(model_id: str) -> Dict[str, Any]:
    """Explicitly loads an installed model into active engine RAM."""
    manifest = garden.get(model_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in catalog.")

    try:
        instance = await execution_registry.load_model(manifest)
        return {
            "status": "loaded",
            "model_id": model_id,
            "backend": instance.backend_type.value,
            "ram_allocated_mb": instance.ram_usage_mb,
            "device": instance.device,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model into memory: {e}")

@router.post("/models/{model_id}/unload")
async def unload_model_from_ram(model_id: str) -> Dict[str, Any]:
    """Unloads a model from RAM to free host memory."""
    unloaded = await execution_registry.unload_model(model_id)
    if not unloaded:
        return {"status": "not_loaded", "model_id": model_id}
    return {"status": "unloaded", "model_id": model_id}
