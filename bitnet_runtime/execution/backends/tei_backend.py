from __future__ import annotations
import logging
import time
from typing import Any, Dict, List, Optional
import httpx
from ..base import (
    BackendHealth,
    BackendStatus,
    BackendType,
    ExecutionBackend,
    LoadedModelInstance,
    RerankItem,
    RerankResponse,
)
from ...inference.base import CompletionResponse, EmbeddingResponse

logger = logging.getLogger(__name__)

class TEIBackend(ExecutionBackend):
    """
    Driver for Hugging Face Text Embeddings Inference (TEI).
    Specialized high-throughput engine for embeddings and cross-encoder rerankers.
    """

    def __init__(self, endpoint_url: str = "http://localhost:8081", timeout: float = 30.0):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.timeout = timeout
        self._loaded_models: Dict[str, LoadedModelInstance] = {}

    @property
    def backend_type(self) -> BackendType:
        return BackendType.TEI

    async def check_health(self) -> BackendHealth:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.endpoint_url}/health")
                if res.status_code == 200:
                    return BackendHealth(
                        backend_type=self.backend_type,
                        status=BackendStatus.ONLINE,
                        endpoint_url=self.endpoint_url,
                        active_models=list(self._loaded_models.keys()),
                    )
        except Exception as e:
            logger.debug(f"TEI health check offline: {e}")
        return BackendHealth(
            backend_type=self.backend_type,
            status=BackendStatus.OFFLINE,
            endpoint_url=self.endpoint_url,
            active_models=list(self._loaded_models.keys()),
        )

    async def load_model(self, model_id: str, model_path: Optional[str] = None, **kwargs: Any) -> LoadedModelInstance:
        instance = LoadedModelInstance(
            model_id=model_id,
            backend_type=self.backend_type,
            loaded_at=time.time(),
            ram_usage_mb=kwargs.get("ram_mb", 350.0),
            device="cpu",
            is_ready=True,
        )
        self._loaded_models[model_id] = instance
        return instance

    async def unload_model(self, model_id: str) -> bool:
        if model_id in self._loaded_models:
            del self._loaded_models[model_id]
            return True
        return False

    async def complete(self, model_id: str, prompt: str, **kwargs: Any) -> CompletionResponse:
        raise NotImplementedError("TEI is specialized for embeddings and rerankers, not generative completion.")

    async def embed(self, model_id: str, texts: List[str], **kwargs: Any) -> List[EmbeddingResponse]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(f"{self.endpoint_url}/embed", json={"inputs": texts})
            if res.status_code != 200:
                raise RuntimeError(f"TEI embed error ({res.status_code}): {res.text}")
            vectors = res.json()
            return [
                EmbeddingResponse(vector=vec, dim=len(vec), model=model_id)
                for vec in vectors
            ]

    async def rerank(self, model_id: str, query: str, documents: List[str], **kwargs: Any) -> RerankResponse:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(
                f"{self.endpoint_url}/rerank",
                json={"query": query, "texts": documents},
            )
            if res.status_code != 200:
                raise RuntimeError(f"TEI rerank error ({res.status_code}): {res.text}")
            data = res.json()
            results = [
                RerankItem(index=r["index"], score=r["score"], text=documents[r["index"]])
                for r in data
            ]
            latency = (time.time() - start_time) * 1000.0
            return RerankResponse(results=results, model=model_id, latency_ms=round(latency, 2))
