from __future__ import annotations
from typing import Dict, List, Optional, Set
from ..logging import logger
from .models import ModelCapabilityProfile, ModelTier, TaskType

class ModelCapabilityRegistry:
    """
    Registry of available model capabilities, pricing, context windows,
    latency profiles, and live health status.
    """

    def __init__(self):
        self._profiles: Dict[str, ModelCapabilityProfile] = {}
        self._init_default_profiles()

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

    def _init_default_profiles(self) -> None:
        # 1. Local 1-Bit BitNet b1.58 2B / 2.4B Engine
        self.register(
            ModelCapabilityProfile(
                model_id="bitnet_b1_58_2b",
                name="Microsoft BitNet b1.58 2B-4T",
                tier=ModelTier.LOCAL_1BIT,
                provider="bitnet",
                capabilities={
                    TaskType.CLASSIFICATION,
                    TaskType.EXTRACTION,
                    TaskType.SUMMARIZATION,
                    TaskType.RAG_QA,
                    TaskType.REASONING,
                    TaskType.CREATIVE,
                },
                context_window=4096,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=120.0,
                quality_score=3.5,
                is_healthy=True,
                metadata={"architecture": "ternary_1bit_cpu", "ram_usage_mb": 1200},
            )
        )

        # 2. Local Dense LLaMA.cpp / GGUF Engine
        self.register(
            ModelCapabilityProfile(
                model_id="llamacpp_dense_8b",
                name="Local LLaMA-3.1 8B Quantized GGUF",
                tier=ModelTier.LOCAL_DENSE,
                provider="llamacpp",
                capabilities={
                    TaskType.CLASSIFICATION,
                    TaskType.EXTRACTION,
                    TaskType.SUMMARIZATION,
                    TaskType.RAG_QA,
                    TaskType.REASONING,
                    TaskType.CODING,
                    TaskType.CREATIVE,
                    TaskType.HIGH_RISK_ACTION,
                },
                context_window=8192,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=650.0,
                quality_score=4.2,
                is_healthy=True,
                metadata={"architecture": "gguf_dense_cpu_gpu", "ram_usage_mb": 5800},
            )
        )

        # 3. Local Endpoint (Ollama / LM Studio)
        self.register(
            ModelCapabilityProfile(
                model_id="local_endpoint_ollama",
                name="Local OpenAI-Compatible Server",
                tier=ModelTier.LOCAL_DENSE,
                provider="local_endpoint",
                capabilities={
                    TaskType.CLASSIFICATION,
                    TaskType.EXTRACTION,
                    TaskType.SUMMARIZATION,
                    TaskType.RAG_QA,
                    TaskType.REASONING,
                    TaskType.CODING,
                },
                context_window=4096,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=450.0,
                quality_score=4.0,
                is_healthy=True,
                metadata={"endpoint": "http://127.0.0.1:11434/v1"},
            )
        )

        # 4. Cloud Frontier Tier (OpenAI / Frontier Adapter)
        self.register(
            ModelCapabilityProfile(
                model_id="cloud_frontier_gpt4o",
                name="Frontier Cloud GPT-4o / Claude 3.5",
                tier=ModelTier.CLOUD_FRONTIER,
                provider="cloud",
                capabilities={
                    TaskType.CLASSIFICATION,
                    TaskType.EXTRACTION,
                    TaskType.SUMMARIZATION,
                    TaskType.RAG_QA,
                    TaskType.REASONING,
                    TaskType.CODING,
                    TaskType.CREATIVE,
                    TaskType.HIGH_RISK_ACTION,
                },
                context_window=128000,
                cost_per_1k_input=0.0025,
                cost_per_1k_output=0.010,
                typical_latency_ms=850.0,
                quality_score=4.9,
                is_healthy=True,
                metadata={"privacy_transit": "public_cloud"},
            )
        )

        # 5. Fast Mock Testing Profile
        self.register(
            ModelCapabilityProfile(
                model_id="mock_local_engine",
                name="Mock Development Engine",
                tier=ModelTier.LOCAL_1BIT,
                provider="mock",
                capabilities={
                    TaskType.CLASSIFICATION,
                    TaskType.EXTRACTION,
                    TaskType.SUMMARIZATION,
                    TaskType.RAG_QA,
                    TaskType.REASONING,
                    TaskType.CODING,
                    TaskType.CREATIVE,
                    TaskType.HIGH_RISK_ACTION,
                },
                context_window=4096,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
                typical_latency_ms=10.0,
                quality_score=3.0,
                is_healthy=True,
                metadata={"test_harness": True},
            )
        )
