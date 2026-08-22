from __future__ import annotations
import time
from typing import Any, Dict, List, Optional
import numpy as np
from ..base import (
    BackendHealth,
    BackendStatus,
    BackendType,
    ExecutionBackend,
    LoadedModelInstance,
    RerankItem,
    RerankResponse,
)
from ...inference.base import CompletionResponse, EmbeddingResponse, TokenUsage

class MockExecutionBackend(ExecutionBackend):
    """Deterministic mock backend used exclusively for offline testing and CI suites."""

    def __init__(self):
        self._loaded_models: Dict[str, LoadedModelInstance] = {}

    @property
    def backend_type(self) -> BackendType:
        return BackendType.MOCK

    async def check_health(self) -> BackendHealth:
        return BackendHealth(
            backend_type=self.backend_type,
            status=BackendStatus.ONLINE,
            endpoint_url="mock://in-process",
            active_models=list(self._loaded_models.keys()),
        )

    async def load_model(self, model_id: str, model_path: Optional[str] = None, **kwargs: Any) -> LoadedModelInstance:
        instance = LoadedModelInstance(
            model_id=model_id,
            backend_type=self.backend_type,
            loaded_at=time.time(),
            ram_usage_mb=kwargs.get("ram_mb", 100.0),
            device="mock",
            is_ready=True,
        )
        self._loaded_models[model_id] = instance
        return instance

    async def unload_model(self, model_id: str) -> bool:
        if model_id in self._loaded_models:
            del self._loaded_models[model_id]
            return True
        return False

    async def complete(
        self,
        model_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        **kwargs: Any,
    ) -> CompletionResponse:
        text = f"Mock completion for model '{model_id}' on prompt: '{prompt[:40]}...'"
        return CompletionResponse(
            text=text,
            model=model_id,
            usage=TokenUsage(prompt_tokens=len(prompt.split()), completion_tokens=len(text.split()), total_tokens=len(prompt.split()) + len(text.split())),
        )

    async def embed(self, model_id: str, texts: List[str], **kwargs: Any) -> List[EmbeddingResponse]:
        dim = 384
        responses = []
        for text in texts:
            # Deterministic unit vector
            np.random.seed(abs(hash(text)) % (2**32))
            v = np.random.randn(dim).astype(np.float32)
            v = (v / np.linalg.norm(v)).tolist()
            responses.append(EmbeddingResponse(vector=v, dim=dim, model=model_id))
        return responses

    async def rerank(self, model_id: str, query: str, documents: List[str], **kwargs: Any) -> RerankResponse:
        results = [
            RerankItem(index=i, score=round(1.0 - (i * 0.1), 3), text=doc)
            for i, doc in enumerate(documents)
        ]
        return RerankResponse(results=results, model=model_id, latency_ms=5.0)
