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
        endpoint_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 60.0,
    ):
        import os
        from ...config import config
        self.endpoint_url = (endpoint_url or config.inference.bitnet_server_url or os.getenv("BITNET_SERVER_URL", "https://ai.alamiaconnect.com/v1")).rstrip("/")
        self.base_url = self.endpoint_url.removesuffix("/v1").rstrip("/")
        self.model_name = model_name or os.getenv("BITNET_MODEL_NAME", "/models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf")
        self.api_key = api_key or config.inference.api_key or os.getenv("BITNET_API_KEY", "51129693340")
        self.timeout = timeout
        self._loaded_models: Dict[str, LoadedModelInstance] = {}

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @property
    def backend_type(self) -> BackendType:
        return BackendType.BITNET_SIDECAR

    async def check_health(self) -> BackendHealth:
        headers = self._get_headers()
        endpoints_to_try = [
            f"{self.base_url}/health",
            f"{self.endpoint_url}/health",
            f"{self.base_url}/models",
            f"{self.endpoint_url}/models",
            "http://127.0.0.1:8080/health",
            "http://127.0.0.1:8080/v1/models",
            "http://bitnet-server:8080/health",
            "http://bitnet-server:8080/v1/models",
            "http://172.17.0.1:8080/health",
            "http://172.17.0.1:8080/v1/models",
            "http://host.docker.internal:8080/health",
        ]
        try:
            async with httpx.AsyncClient(timeout=6.0, headers=headers, verify=False) as client:
                for ep in endpoints_to_try:
                    try:
                        res = await client.get(ep)
                        if res.status_code == 200:
                            return BackendHealth(
                                backend_type=self.backend_type,
                                status=BackendStatus.ONLINE,
                                endpoint_url=self.endpoint_url,
                                active_models=list(self._loaded_models.keys()),
                            )
                    except Exception:
                        continue
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

        target_model = self.model_name if (not model_id.startswith("/") or model_id == "bitnet_b1_58_2b") else model_id

        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stop": stop_sequences or [],
        }

        urls_to_try = [
            f"{self.endpoint_url}/chat/completions",
            f"{self.base_url}/v1/chat/completions",
            f"{self.base_url}/chat/completions",
            "http://127.0.0.1:8080/v1/chat/completions",
            "http://bitnet-server:8080/v1/chat/completions",
            "http://172.17.0.1:8080/v1/chat/completions",
            "http://host.docker.internal:8080/v1/chat/completions",
        ]

        async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers(), verify=False) as client:
            res = None
            last_err = None
            for target_url in urls_to_try:
                try:
                    res = await client.post(target_url, json=payload)
                    if res.status_code == 200:
                        break
                except Exception as ex:
                    last_err = ex
                    continue

            if res is None or res.status_code != 200:
                err_msg = res.text if res is not None else (str(last_err) if last_err else "Endpoint unreachable")
                raise RuntimeError(f"bitnet-server error: {err_msg}")
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
