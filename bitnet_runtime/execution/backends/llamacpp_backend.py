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
from ...inference.base import CompletionResponse, EmbeddingResponse, TokenUsage

logger = logging.getLogger(__name__)

class LlamaCppBackend(ExecutionBackend):
    """
    Driver for llama.cpp / llama-server.
    Supports OpenAI-compatible chat, completions, embeddings, and reranking.
    """

    def __init__(self, endpoint_url: str = "http://localhost:8080", timeout: float = 60.0):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.timeout = timeout
        self._loaded_models: Dict[str, LoadedModelInstance] = {}

    @property
    def backend_type(self) -> BackendType:
        return BackendType.LLAMACPP

    async def check_health(self) -> BackendHealth:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.endpoint_url}/health")
                if res.status_code == 200:
                    data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
                    return BackendHealth(
                        backend_type=self.backend_type,
                        status=BackendStatus.ONLINE,
                        endpoint_url=self.endpoint_url,
                        active_models=list(self._loaded_models.keys()),
                        details=data,
                    )
        except Exception as e:
            logger.debug(f"llama-server health check offline: {e}")
        return BackendHealth(
            backend_type=self.backend_type,
            status=BackendStatus.OFFLINE,
            endpoint_url=self.endpoint_url,
            active_models=list(self._loaded_models.keys()),
        )

    async def load_model(self, model_id: str, model_path: Optional[str] = None, **kwargs: Any) -> LoadedModelInstance:
        # In llama-server router mode or single-model mode, register loaded instance
        instance = LoadedModelInstance(
            model_id=model_id,
            backend_type=self.backend_type,
            loaded_at=time.time(),
            ram_usage_mb=kwargs.get("ram_mb", 1200.0),
            device=kwargs.get("device", "cpu"),
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
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> CompletionResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop": stop_sequences or [],
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(f"{self.endpoint_url}/v1/chat/completions", json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"llama-server error ({res.status_code}): {res.text}")
            data = res.json()
            choice = data["choices"][0]["message"]
            text = choice.get("content", "")
            usage = data.get("usage", {})
            return CompletionResponse(
                text=text.strip(),
                model=model_id,
                usage=TokenUsage(
                    prompt_tokens=usage.get("prompt_tokens", len(prompt.split())),
                    completion_tokens=usage.get("completion_tokens", len(text.split())),
                    total_tokens=usage.get("total_tokens", len(prompt.split()) + len(text.split())),
                ),
                raw_output=data,
            )

    async def embed(
        self,
        model_id: str,
        texts: List[str],
        **kwargs: Any,
    ) -> List[EmbeddingResponse]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(
                f"{self.endpoint_url}/v1/embeddings",
                json={"model": model_id, "input": texts},
            )
            if res.status_code in (404, 501):
                raise NotImplementedError(f"llama-server at {self.endpoint_url} does not support embeddings: {res.text}")
            elif res.status_code != 200:
                raise RuntimeError(f"llama-server embedding error ({res.status_code}): {res.text}")
            data = res.json()
            items = data.get("data", [])
            responses = []
            for item in items:
                vec = item.get("embedding", [])
                responses.append(EmbeddingResponse(vector=vec, dim=len(vec), model=model_id))
            return responses

    async def rerank(
        self,
        model_id: str,
        query: str,
        documents: List[str],
        **kwargs: Any,
    ) -> RerankResponse:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            res = await client.post(
                f"{self.endpoint_url}/v1/rerank",
                json={"model": model_id, "query": query, "documents": documents},
            )
            if res.status_code in (404, 501):
                raise NotImplementedError(f"llama-server at {self.endpoint_url} does not support reranking: {res.text}")
            elif res.status_code != 200:
                raise RuntimeError(f"llama-server rerank error ({res.status_code}): {res.text}")
            data = res.json()
            results = [
                RerankItem(index=r["index"], score=r["relevance_score"], text=documents[r["index"]])
                for r in data.get("results", [])
            ]
            latency = (time.time() - start_time) * 1000.0
            return RerankResponse(results=results, model=model_id, latency_ms=round(latency, 2))
