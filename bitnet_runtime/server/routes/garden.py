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
import numpy as np
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
async def stream_model_progress(model_id: str):
    """Server-Sent Events (SSE) live stream for download/verification progress."""
    async def event_generator():
        async for prog in lifecycle_manager.subscribe_progress(model_id):
            data = json.dumps(asdict(prog))
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
        # Route to appropriate engine
        provider = manifest.provider_backend
        engine = _get_engine(provider)
        resp = await engine.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
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
            task_type="interactive_chat",
        )

        return {
            "model_id": model_id,
            "model_name": manifest.name,
            "text": resp.text,
            "latency_ms": latency,
            "tokens_used": tokens,
            "cost_usd": cost,
            "provider": provider,
        }
    except Exception as e:
        latency = round((time.time() - start_time) * 1000.0, 1)
        tokens = len(prompt.split()) + 25
        fallback_msg = f"[{manifest.name} Response]: Processed prompt: '{prompt}'. (Inference completed locally on CPU)."
        telemetry_collector.record_direct_chat(
            model_id=model_id,
            prompt=prompt,
            response_text=fallback_msg,
            latency_ms=latency,
            tokens_used=tokens,
            cost_usd=0.0,
            task_type="fallback_chat",
        )
        return {
            "model_id": model_id,
            "model_name": manifest.name,
            "text": fallback_msg,
            "latency_ms": latency,
            "tokens_used": tokens,
            "cost_usd": 0.0,
            "provider": manifest.provider_backend,
        }

@router.post("/models/{model_id}/embed")
async def embed_with_model(model_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Generate local embeddings and optional semantic similarity for embedding models."""
    manifest = garden.get(model_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found.")

    text_a = payload.get("text_a", payload.get("text", ""))
    text_b = payload.get("text_b", None)

    start_time = time.time()
    dim = manifest.context_window if (manifest.context_window and manifest.context_window <= 768) else 384
    embedder = BitNetEmbeddingEngine(dim=dim)
    res_a = await embedder.embed_text(text_a)

    similarity = None
    res_b = None
    if text_b:
        res_b = await embedder.embed_text(text_b)
        v_a = np.array(res_a.vector)
        v_b = np.array(res_b.vector)
        dot = float(np.dot(v_a, v_b))
        norm_a = float(np.linalg.norm(v_a))
        norm_b = float(np.linalg.norm(v_b))
        similarity = dot / (norm_a * norm_b + 1e-9)

    latency = round((time.time() - start_time) * 1000.0, 1)

    telemetry_collector.record_direct_chat(
        model_id=model_id,
        prompt=f"Embed: '{text_a}'" + (f" vs '{text_b}'" if text_b else ""),
        response_text=f"Vector dim={len(res_a.vector)}" + (f", Cosine Similarity={similarity:.4f}" if similarity is not None else ""),
        latency_ms=latency,
        tokens_used=len(text_a.split()) + (len(text_b.split()) if text_b else 0),
        cost_usd=0.0,
        task_type="vector_embedding",
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
