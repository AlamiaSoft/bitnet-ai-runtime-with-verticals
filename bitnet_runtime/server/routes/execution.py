from __future__ import annotations
from dataclasses import asdict
from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from ...execution import execution_registry
from ...execution.hardware import detect_hardware
from ...execution.native_binary import select_best_binary
from ...execution.runtime_preference import (
    RuntimePreference,
    RuntimePreferenceStore,
    get_preference_store,
    set_preference,
)
from ...execution.runtime_resolver import global_runtime_resolver
from ...model_garden import ModelGarden, ModelLifecycleManager
from pathlib import Path

router = APIRouter(prefix="/api/v1/execution", tags=["Execution Fabric"])

garden = ModelGarden()
lifecycle = ModelLifecycleManager(garden=garden)

_BIN_DIR = Path(__file__).parent.parent.parent.parent / ".sidecar" / "alamia-bitnet-runtime" / "bin"

# ---- Execution Fabric endpoints ----

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

from ..telemetry import telemetry_collector

@router.post("/models/{model_id}/load")
async def load_model_to_ram(model_id: str) -> Dict[str, Any]:
    """Explicitly loads an installed model into active engine RAM."""
    manifest = garden.get(model_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found in catalog.")

    try:
        instance = await execution_registry.load_model(manifest)
        telemetry_collector.record_model_lifecycle(
            action="load",
            model_id=model_id,
            model_name=manifest.name,
            ram_mb=instance.ram_usage_mb,
            status="loaded",
        )
        return {
            "status": "loaded",
            "model_id": model_id,
            "backend": instance.backend_type.value,
            "ram_allocated_mb": instance.ram_usage_mb,
            "device": instance.device,
        }
    except Exception as e:
        telemetry_collector.record_model_lifecycle(
            action="load",
            model_id=model_id,
            model_name=manifest.name,
            status=f"error: {e}",
        )
        raise HTTPException(status_code=500, detail=f"Failed to load model into memory: {e}")

@router.post("/models/{model_id}/unload")
async def unload_model_from_ram(model_id: str) -> Dict[str, Any]:
    """Unloads a model from RAM to free host memory."""
    manifest = garden.get(model_id)
    name = manifest.name if manifest else model_id
    unloaded = await execution_registry.unload_model(model_id)
    status_str = "unloaded" if unloaded else "not_loaded"
    telemetry_collector.record_model_lifecycle(
        action="unload",
        model_id=model_id,
        model_name=name,
        status=status_str,
    )
    if not unloaded:
        return {"status": "not_loaded", "model_id": model_id}
    return {"status": "unloaded", "model_id": model_id}


# ---- Runtime Assessment endpoints ----

@router.get("/runtime/hardware")
async def get_hardware_profile() -> Dict[str, Any]:
    """
    Detect host hardware capabilities: CPU arch, SIMD flags, RAM, GPU, disk.
    Also runs binary tier selection to show what native build is available.
    """
    hw = detect_hardware()
    assessment = select_best_binary(hw, _BIN_DIR)

    # RAM eligibility thresholds for known models
    ram_eligible = []
    if hw.available_ram_mb >= int(1200 * 1.2):
        ram_eligible.append("bitnet_b1_58_2b (1.2 GB)")
    if hw.available_ram_mb >= int(1100 * 1.2):
        ram_eligible.append("qwen2.5_1.5b_instruct (1.1 GB)")
    if hw.available_ram_mb >= int(2000 * 1.2):
        ram_eligible.append("gemma2_2b_it (2 GB)")
    if hw.available_ram_mb >= int(2500 * 1.2):
        ram_eligible.append("llama3.2_3b_instruct (2.5 GB)")
    if hw.available_ram_mb >= int(3800 * 1.2):
        ram_eligible.append("phi3.5_mini_3.8b (3.8 GB)")

    return {
        "cpu_arch": hw.cpu_arch,
        "cpu_cores": hw.cpu_cores,
        "total_ram_mb": hw.total_ram_mb,
        "available_ram_mb": hw.available_ram_mb,
        "simd_flags": hw.simd_flags,
        "has_gpu": hw.has_gpu,
        "gpu_vram_mb": hw.gpu_vram_mb,
        "free_disk_mb": hw.free_disk_mb,
        "native_binary": {
            "tier": assessment.tier.name if assessment.tier else None,
            "binary": assessment.tier.binary_filename if assessment.tier else None,
            "suitability": assessment.suitability,
            "suitability_score": assessment.suitability_score,
            "reason": assessment.reason,
            "warn_performance": assessment.warn_performance,
            "available_tiers_on_disk": assessment.available_tiers,
        },
        "ram_eligible_models": ram_eligible,
    }


@router.get("/runtime/preference")
async def get_runtime_preference() -> Dict[str, Any]:
    """Get the current user runtime preference."""
    store = get_preference_store()
    return {
        "preference": store.preference.value,
        "dismissed_recommendation": store.dismissed_recommendation,
        "last_assessment_ts": store.last_assessment_ts,
    }


@router.post("/runtime/preference")
async def update_runtime_preference(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Set the user runtime preference.
    Accepted values: 'auto', 'native', 'docker'
    """
    raw = payload.get("preference", "").lower()
    try:
        pref = RuntimePreference(raw)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid preference '{raw}'. Valid values: auto, native, docker"
        )
    store = set_preference(pref)
    # Clear cached assessment so next resolution re-evaluates
    global_runtime_resolver.hardware_profile = None
    global_runtime_resolver.binary_assessment = None
    return {
        "status": "updated",
        "preference": store.preference.value,
    }


@router.get("/runtime/recommendation")
async def get_runtime_recommendation() -> Dict[str, Any]:
    """
    Returns the recommended runtime for this machine, with human-readable reasoning.
    Also lists all available runtimes and their suitability.
    """
    hw = detect_hardware()
    assessment = select_best_binary(hw, _BIN_DIR)
    store = get_preference_store()

    available: List[Dict[str, Any]] = []

    # Assess native
    native_suitability = assessment.suitability
    native_entry = {
        "runtime": "native",
        "label": f"Native CPU ({assessment.tier.name if assessment.tier else 'no binary'})",
        "suitability": native_suitability,
        "suitability_score": assessment.suitability_score,
        "reason": assessment.reason,
        "warn_performance": assessment.warn_performance,
    }
    available.append(native_entry)

    # Docker always listed (we don't probe live here to keep this fast)
    available.append({
        "runtime": "docker",
        "label": "Docker Container",
        "suitability": "good",
        "suitability_score": 0.75,
        "reason": "Isolated container runtime. Requires Docker installed.",
        "warn_performance": False,
    })

    # Determine recommendation
    if native_suitability == "excellent":
        recommended = "native"
        rec_reason = (
            f"{assessment.tier.description if assessment.tier else 'Native binary'} + "
            f"{hw.available_ram_mb} MB RAM available. Lowest overhead, no Docker required."
        )
    elif native_suitability == "good":
        recommended = "native"
        rec_reason = f"Compatible native binary available. {assessment.reason}"
    elif native_suitability == "poor":
        recommended = "docker"
        rec_reason = (
            f"Native binary available but performance would be poor (no SIMD). "
            f"Docker provides better isolation and reliability for this hardware."
        )
    else:
        recommended = "docker"
        rec_reason = f"No compatible native binary. {assessment.reason}"

    return {
        "recommended": recommended,
        "reason": rec_reason,
        "current_preference": store.preference.value,
        "available": available,
        "hardware_summary": {
            "cpu_arch": hw.cpu_arch,
            "cpu_cores": hw.cpu_cores,
            "simd_flags": hw.simd_flags,
            "total_ram_mb": hw.total_ram_mb,
            "available_ram_mb": hw.available_ram_mb,
            "has_gpu": hw.has_gpu,
        },
    }
