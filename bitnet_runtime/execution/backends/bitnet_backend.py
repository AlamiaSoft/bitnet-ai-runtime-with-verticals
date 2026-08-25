from __future__ import annotations
import asyncio
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
        self._active_endpoint: Optional[str] = None

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @property
    def backend_type(self) -> BackendType:
        return BackendType.BITNET_SIDECAR

    def get_endpoint_description(self) -> str:
        active = self._active_endpoint or self.endpoint_url or ""
        if any(loc in active for loc in ["bitnet-runtime", "bitnet-server", "127.0.0.1", "localhost", "172.", "host.docker.internal"]):
            return "bitnet-sidecar (local container / 8080)"
        domain = active.replace("https://", "").replace("http://", "").split("/")[0]
        return f"bitnet-sidecar ({domain})" if domain else "bitnet-sidecar (local)"

    async def check_health(self) -> BackendHealth:
        headers = self._get_headers()
        local_endpoints = [
            "http://bitnet-runtime:11434/health",
            "http://bitnet-runtime:11434/v1/models",
            "http://bitnet-server:11434/health",
            "http://bitnet-server:11434/v1/models",
            "http://127.0.0.1:8080/health",
            "http://127.0.0.1:8080/v1/models",
            "http://bitnet-server:8080/health",
            "http://bitnet-server:8080/v1/models",
            "http://172.17.0.1:8080/health",
            "http://172.17.0.1:8080/v1/models",
            "http://172.18.0.1:8080/health",
            "http://172.30.0.1:8080/health",
            "http://host.docker.internal:8080/health",
            "http://host.docker.internal:8080/v1/models",
        ]
        remote_endpoints = [
            f"{self.base_url}/health",
            f"{self.endpoint_url}/health",
            f"{self.base_url}/models",
            f"{self.endpoint_url}/models",
        ]
        endpoints_to_try = local_endpoints + remote_endpoints

        last_probe_err = None
        try:
            async with httpx.AsyncClient(timeout=3.0, headers=headers, verify=False) as client:
                async def _probe(ep: str) -> Optional[str]:
                    nonlocal last_probe_err
                    try:
                        res = await client.get(ep)
                        if res.status_code == 200:
                            return ep
                        else:
                            last_probe_err = f"HTTP {res.status_code} on {ep}"
                    except Exception as ex:
                        last_probe_err = f"{ex} on {ep}"
                    return None

                results = await asyncio.gather(*[_probe(ep) for ep in endpoints_to_try], return_exceptions=True)
                for working_ep in results:
                    if isinstance(working_ep, str) and working_ep:
                        if "/health" in working_ep:
                            self._active_endpoint = working_ep.replace("/health", "")
                        elif "/models" in working_ep:
                            self._active_endpoint = working_ep.replace("/models", "").removesuffix("/v1")
                        return BackendHealth(
                            backend_type=self.backend_type,
                            status=BackendStatus.ONLINE,
                            endpoint_url=self._active_endpoint or self.endpoint_url,
                            active_models=list(self._loaded_models.keys()),
                        )
        except Exception as e:
            last_probe_err = str(e)

        logger.info(f"BitNet sidecar health probe reported OFFLINE. Last probe detail: {last_probe_err}")
        return BackendHealth(
            backend_type=self.backend_type,
            status=BackendStatus.OFFLINE,
            endpoint_url=self.endpoint_url,
            active_models=list(self._loaded_models.keys()),
            details={"error": last_probe_err},
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

        # If a specific endpoint_url is passed by the ExecutionPlacement, prioritize it directly
        explicit_ep = kwargs.get("endpoint_url")
        if explicit_ep:
            clean_base = explicit_ep.replace("/chat/completions", "").replace("/v1", "").rstrip("/")
            urls_to_try = [
                f"{clean_base}/v1/chat/completions",
                f"{clean_base}/chat/completions",
            ]
        else:
            urls_to_try = []
            if self._active_endpoint:
                urls_to_try.extend([
                    f"{self._active_endpoint}/v1/chat/completions",
                    f"{self._active_endpoint}/chat/completions",
                ])

            local_urls = [
                "http://bitnet-runtime:11434/v1/chat/completions",
                "http://bitnet-server:11434/v1/chat/completions",
                "http://127.0.0.1:8080/v1/chat/completions",
                "http://bitnet-server:8080/v1/chat/completions",
                "http://172.17.0.1:8080/v1/chat/completions",
                "http://172.30.0.1:8080/v1/chat/completions",
                "http://host.docker.internal:8080/v1/chat/completions",
            ]
            remote_urls = [
                f"{self.endpoint_url}/chat/completions",
                f"{self.base_url}/v1/chat/completions",
                f"{self.base_url}/chat/completions",
            ]
            urls_to_try.extend(local_urls + remote_urls)

        # Remove duplicates preserving order
        seen = set()
        unique_urls = [u for u in urls_to_try if not (u in seen or seen.add(u))]

        async with httpx.AsyncClient(timeout=self.timeout, headers=self._get_headers(), verify=False) as client:
            res = None
            last_err = None
            for target_url in unique_urls:
                try:
                    res = await client.post(target_url, json=payload)
                    if res.status_code == 200:
                        # Record working active endpoint
                        base_working = target_url.replace("/v1/chat/completions", "").replace("/chat/completions", "")
                        self._active_endpoint = base_working
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
