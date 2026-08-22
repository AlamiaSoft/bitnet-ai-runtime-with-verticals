from __future__ import annotations
import os
import platform
from pathlib import Path
from typing import Any, Dict, Optional
from ..config import InferenceSettings
from ..logging import logger
from .base import EmbeddingEngine, InferenceEngine
from .bitnet_engine import BitNetEngine
from .embeddings import BitNetEmbeddingEngine
from .llamacpp_engine import LlamaCppEngine
from .local_endpoint_engine import LocalEndpointEngine
from .mock_engine import MockInferenceEngine

class ModelManager:
    def __init__(self, settings: InferenceSettings):
        self.settings = settings
        self._inference_engine: Optional[InferenceEngine] = None
        self._embedding_engine: Optional[EmbeddingEngine] = None

    def get_hardware_info(self) -> Dict[str, Any]:
        return {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "cpu_count": os.cpu_count() or 1,
            "architecture": platform.architecture()[0],
        }

    def get_inference_engine(self, provider: Optional[str] = None) -> InferenceEngine:
        target_provider = (provider or self.settings.default_provider).lower()

        if provider is None and self._inference_engine is not None:
            return self._inference_engine

        logger.info(f"Initializing inference provider: '{target_provider}'")

        if target_provider == "bitnet":
            engine = BitNetEngine(
                server_url=self.settings.bitnet_server_url,
                model_name=self.settings.model_name,
                model_path=self.settings.model_path,
                threads=self.settings.threads,
            )
        elif target_provider == "llamacpp":
            engine = LlamaCppEngine(
                model_path=self.settings.model_path,
                threads=self.settings.threads,
                context_window=self.settings.context_window,
            )
        elif target_provider in ("local_endpoint", "cloud"):
            engine = LocalEndpointEngine(
                endpoint_url=self.settings.local_endpoint_url,
                model_name=self.settings.model_name,
                api_key=self.settings.api_key,
            )
        elif target_provider == "mock":
            engine = MockInferenceEngine()
        else:
            logger.warning(f"Unknown provider '{target_provider}', falling back to MockInferenceEngine.")
            engine = MockInferenceEngine()

        if provider is None:
            self._inference_engine = engine

        return engine

    def get_embedding_engine(self, dim: int = 128) -> EmbeddingEngine:
        if self._embedding_engine is None:
            self._embedding_engine = BitNetEmbeddingEngine(dim=dim)
        return self._embedding_engine
