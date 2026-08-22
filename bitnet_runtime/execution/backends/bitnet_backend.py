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
    RerankResponse,
)
from ...inference.base import CompletionResponse, EmbeddingResponse, TokenUsage

logger = logging.getLogger(__name__)

class BitNetBackend(ExecutionBackend):
    """
    Driver for Microsoft BitNet sidecar container (ghcr.io/microsoft/bitnet-server).
    """

    def __init__(
        self,
        endpoint_url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ):
        self.endpoint_url = endpoint_url.rstrip("/")
        self.base_url = self.endpoint_url.removesuffix("/v1").rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._loaded_models: Dict[str, LoadedModelInstance] = {}

    def _get_headers(self) -> Dict[str, str]:
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @property
    def backend_type(self) -> BackendType:
        return BackendType.BITNET_SIDECAR

    async def check_health(self) -> BackendHealth:
        try:
            async with httpx.AsyncClient(timeout=3.0, headers=self._get_headers()) as client:
                res = await client.get(f"{self.base_url}/health")
                if res.status_code != 200:
                    res = await client.get(f"{self.endpoint_url}/health")
                if res.status_code == 200:
                    return BackendHealth(
                        backend_type=self.backend_type,
                        status=BackendStatus.ONLINE,
                        endpoint_url=self.endpoint_url,
                        active_models=list(self._loaded_models.keys()),
                    )
        except Exception as e:
            logger.debug(f"bitnet-server health check offline: {e}")
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
            ram_usage_mb=kwargs.get("ram_mb", 1200.0),
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

        async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers()) as client:
            # Try chat completions or completion endpoint
            res = await client.post(f"{self.base_url}/v1/chat/completions", json=payload)
            if res.status_code != 200:
                res = await client.post(f"{self.base_url}/chat/completions", json=payload)
            if res.status_code != 200:
                res = await client.post(f"{self.endpoint_url}/chat/completions", json=payload)
            if res.status_code != 200:
                raise RuntimeError(f"bitnet-server error ({res.status_code}): {res.text}")
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

    async def embed(self, model_id: str, texts: List[str], **kwargs: Any) -> List[EmbeddingResponse]:
        raise NotImplementedError("BitNet sidecar is generative text only.")

    async def rerank(self, model_id: str, query: str, documents: List[str], **kwargs: Any) -> RerankResponse:
        raise NotImplementedError("BitNet sidecar does not support sequence reranking.")
