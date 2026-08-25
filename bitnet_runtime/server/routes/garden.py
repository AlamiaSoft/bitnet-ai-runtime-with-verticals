from __future__ import annotations
import asyncio
import json
import time
from dataclasses import asdict
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from sse_starlette.sse import EventSourceResponse
from ...model_garden import (
    HardwareDiscoveryEngine,
    ModelFamily,
    ModelGarden,
    ModelLifecycleManager,
    ModelModality,
    ModelStatus,
)
from ...inference import (
    BitNetEngine,
    BitNetEmbeddingEngine,
    CompletionResponse,
    InferenceEngine,
    LlamaCppEngine,
    LocalEndpointEngine,
    MockInferenceEngine,
)
from ...execution import execution_registry
from ...config import config
from ..telemetry import telemetry_collector

def _get_engine(provider: str) -> InferenceEngine:
    if provider == "bitnet":
        return BitNetEngine()
    elif provider == "llamacpp":
        return LlamaCppEngine()
    elif provider == "local_endpoint":
        return LocalEndpointEngine()
    return MockInferenceEngine()

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
            "download_url": m.download_url,
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
@router.get("/models/{model_id}/acquire-stream")
async def stream_model_progress(model_id: str, background_tasks: BackgroundTasks):
    """Server-Sent Events (SSE) live stream for download/verification progress."""
    manifest = garden.get(model_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    status = lifecycle_manager.get_status(model_id)
    if status == ModelStatus.AVAILABLE:
        background_tasks.add_task(lifecycle_manager.install_model, model_id)

    async def event_generator():
        async for prog in lifecycle_manager.subscribe_progress(model_id):
            data_dict = asdict(prog)
            data_dict["progress_pct"] = data_dict.get("percentage", 0.0)
            data = json.dumps(data_dict)
            yield {"event": "progress", "data": data}
            yield {"event": "message", "data": data}
            await asyncio.sleep(0.01)

    return EventSourceResponse(event_generator())

@router.post("/models/{model_id}/chat")
async def chat_with_model(model_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Direct interactive chat with a downloaded model."""
    manifest = garden.get(model_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    status = lifecycle_manager.get_status(model_id)
    if status not in (ModelStatus.INSTALLED, ModelStatus.LOADED) and manifest.provider_backend != "mock":
        raise HTTPException(
            status_code=400,
            detail=f"Model '{model_id}' is not installed yet (status: {status}). Please install it first.",
        )

    prompt = payload.get("prompt", "")
    system_prompt = payload.get("system_prompt", "You are an efficient local AI assistant.")
    temperature = float(payload.get("temperature", 0.7))
    max_tokens = int(payload.get("max_tokens", 512))

    start_time = time.time()
    try:
        resp = await execution_registry.complete(
            manifest=manifest,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            auto_load=True,
        )
        latency = round((time.time() - start_time) * 1000.0, 1)
        tokens = resp.usage.total_tokens if resp.usage else (len(prompt.split()) + len(resp.text.split()))
        cost = 0.0 if manifest.cost_per_1k_input == 0.0 else round(0.002, 5)

        telemetry_collector.record_direct_chat(
            model_id=model_id,
            prompt=prompt,
            response_text=resp.text,
            latency_ms=latency,
            tokens_used=tokens,
            cost_usd=cost,
            task_type="chat",
            model_name=manifest.name,
        )

        from ...execution.base import BackendType
        if manifest.family == ModelFamily.BITNET:
            bitnet_backend = execution_registry._backends.get(BackendType.BITNET_SIDECAR)
            endpoint_desc = bitnet_backend.get_endpoint_description() if bitnet_backend and hasattr(bitnet_backend, "get_endpoint_description") else "bitnet-sidecar (local container / 8080)"
        elif model_id == "mock_local_engine":
            endpoint_desc = "test-harness mock"
        else:
            endpoint_desc = "local in-process GGUF"

        return {
            "model_id": model_id,
            "model_name": manifest.name,
            "text": resp.text,
            "latency_ms": latency,
            "tokens_used": tokens,
            "cost_usd": cost,
            "provider": manifest.provider_backend,
            "endpoint": endpoint_desc,
        }
    except Exception as e:
        latency = round((time.time() - start_time) * 1000.0, 1)
        raise HTTPException(
            status_code=500,
            detail=f"Inference failed on model '{model_id}': {e}",
        )

@router.post("/models/{model_id}/embed")
async def embed_with_model(model_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate local embeddings and optional semantic similarity for embedding models."""
    manifest = garden.get(model_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    text_a = payload.get("text_a", payload.get("text", ""))
    text_b = payload.get("text_b", None)

    start_time = time.time()
    texts = [text_a]
    if text_b:
        texts.append(text_b)

    responses = await execution_registry.embed(
        manifest=manifest,
        texts=texts,
        auto_load=True,
    )
    res_a = responses[0]

    similarity = None
    if text_b and len(responses) > 1:
        res_b = responses[1]
        v_a = res_a.vector
        v_b = res_b.vector
        dot = sum(a * b for a, b in zip(v_a, v_b))
        norm_a = sum(a * a for a in v_a) ** 0.5
        norm_b = sum(b * b for b in v_b) ** 0.5
        similarity = dot / (norm_a * norm_b + 1e-9)

    latency = round((time.time() - start_time) * 1000.0, 1)

    if similarity is not None and text_b:
        telemetry_collector.record_embedding(
            model_id=model_id,
            text_a=text_a,
            text_b=text_b,
            similarity=float(similarity),
            latency_ms=latency,
        )
    else:
        telemetry_collector.record_direct_chat(
            model_id=model_id,
            prompt=f"Embed: '{text_a}'",
            response_text=f"Vector dim={len(res_a.vector)}",
            latency_ms=latency,
            tokens_used=len(text_a.split()),
            cost_usd=0.0,
            task_type="embedding",
            model_name=manifest.name,
        )

    return {
        "model_id": model_id,
        "model_name": manifest.name,
        "dimensions": len(res_a.vector),
        "vector_a_preview": [round(float(x), 4) for x in res_a.vector[:8]],
        "text_a": text_a,
        "text_b": text_b,
        "cosine_similarity": round(float(similarity), 4) if similarity is not None else None,
        "latency_ms": latency,
    }
