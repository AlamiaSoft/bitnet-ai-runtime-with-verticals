from __future__ import annotations
from typing import Dict, List, Optional, Set
from ..logging import logger
from ..model_garden.catalog import ModelGarden
from ..model_garden.manager import ModelLifecycleManager, ModelStatus
from .models import ModelCapabilityProfile, ModelTier, TaskType

class ModelCapabilityRegistry:
    """
    Registry of available model capabilities, pricing, context windows,
    latency profiles, hardware requirements, and live health status.
    Directly consumes and synchronizes from the Model Garden and Lifecycle Manager.
    """

    def __init__(self, garden: Optional[ModelGarden] = None, lifecycle_manager: Optional[ModelLifecycleManager] = None):
        self.garden = garden or ModelGarden()
        self.lifecycle_manager = lifecycle_manager or ModelLifecycleManager(garden=self.garden)
        self._profiles: Dict[str, ModelCapabilityProfile] = {}
        self._sync_from_garden()

    def _sync_from_garden(self) -> None:
        """Dynamically populates capability profiles from Model Garden manifests."""
        for manifest in self.garden.list_all():
            capabilities = set(manifest.task_ratings.keys())
            if not capabilities:
                capabilities = {TaskType.REASONING}

            avg_quality = (
                sum(manifest.task_ratings.values()) / len(manifest.task_ratings)
                if manifest.task_ratings
                else 3.0
            )

            status = self.lifecycle_manager.get_status(manifest.model_id)
            is_installed = (status in (ModelStatus.INSTALLED, ModelStatus.LOADED)) or (manifest.provider_backend in ("bitnet", "mock"))
            is_loaded = (status == ModelStatus.LOADED)

            profile = ModelCapabilityProfile(
                model_id=manifest.model_id,
                name=manifest.name,
                tier=manifest.tier,
                provider=manifest.provider_backend,
                capabilities=capabilities,
                task_ratings=dict(manifest.task_ratings),
                context_window=manifest.context_window,
                cost_per_1k_input=manifest.cost_per_1k_input,
                cost_per_1k_output=manifest.cost_per_1k_output,
                typical_latency_ms=manifest.typical_latency_ms,
                quality_score=round(avg_quality, 2),
                is_healthy=manifest.is_healthy,
                is_installed=is_installed,
                is_loaded=is_loaded,
                metadata={
                    "family": str(manifest.family),
                    "modality": str(manifest.modality),
                    "min_ram_mb": manifest.hardware.min_ram_mb,
                    "quantization": manifest.hardware.quantization,
                    "license": manifest.license,
                    "status": status.value if hasattr(status, "value") else str(status),
                },
            )
            self._profiles[profile.model_id] = profile

    def register(self, profile: ModelCapabilityProfile) -> None:
        self._profiles[profile.model_id] = profile
        logger.debug(f"Registered model capability profile: '{profile.model_id}' ({profile.tier})")

    def unregister(self, model_id: str) -> None:
        self._profiles.pop(model_id, None)

    def get(self, model_id: str) -> Optional[ModelCapabilityProfile]:
        return self._profiles.get(model_id)

    def list_all(self) -> List[ModelCapabilityProfile]:
        return list(self._profiles.values())

    def update_health(self, model_id: str, is_healthy: bool) -> None:
        if model_id in self._profiles:
            self._profiles[model_id].is_healthy = is_healthy
