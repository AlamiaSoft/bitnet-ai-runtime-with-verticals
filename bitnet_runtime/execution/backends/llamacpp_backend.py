from __future__ import annotations
import asyncio
import gc
import logging
import os
import time
from pathlib import Path
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
    Dual-Mode Driver for llama.cpp:
    1. In-Process Execution: Directly loads .gguf models on host CPU via `llama_cpp.Llama`.
    2. Server Mode: Connects to local or remote `llama-server` instances.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        storage_dir: Optional[Path] = None,
        threads: Optional[int] = None,
        context_window: int = 4096,
        timeout: float = 60.0,
    ):
        self.endpoint_url = (endpoint_url or os.getenv("LLAMACPP_SERVER_URL", "http://localhost:8080")).rstrip("/")
        self.storage_dir = Path(storage_dir or os.getenv("BITNET_MODELS_DIR", "./models")).resolve()
        self.threads = threads or int(os.getenv("BITNET_THREADS", "4"))
        self.context_window = context_window
        self.timeout = timeout
        self._loaded_models: Dict[str, LoadedModelInstance] = {}
        self._in_process_llms: Dict[str, Any] = {}

    @property
    def backend_type(self) -> BackendType:
        return BackendType.LLAMACPP

    def _resolve_local_model_path(self, model_id: str) -> Optional[Path]:
        candidates = [
            self.storage_dir / f"{model_id}.gguf",
            self.storage_dir / f"{model_id.replace('.', '_')}.gguf",
            self.storage_dir / f"{model_id.replace('_', '.')}.gguf",
        ]
        for p in candidates:
            if p.exists() and p.stat().st_size > 0:
                return p
        return None

    def is_in_process_supported(self) -> bool:
        try:
            import llama_cpp
            return True
        except ImportError:
            return False

    async def check_health(self) -> BackendHealth:
        # 1. Check HTTP server
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                res = await client.get(f"{self.endpoint_url}/health")
                if res.status_code == 200:
                    data = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
                    return BackendHealth(
                        backend_type=self.backend_type,
                        status=BackendStatus.ONLINE,
                        endpoint_url=self.endpoint_url,
                        active_models=list(self._loaded_models.keys()),
                        details={"mode": "server", **data},
                    )
        except Exception:
            pass

        # 2. Check in-process availability
        if self.is_in_process_supported():
            return BackendHealth(
                backend_type=self.backend_type,
                status=BackendStatus.ONLINE,
                endpoint_url="in-process://llama_cpp",
                active_models=list(self._loaded_models.keys()),
                details={"mode": "in_process", "threads": self.threads},
            )

        return BackendHealth(
            backend_type=self.backend_type,
            status=BackendStatus.OFFLINE,
            endpoint_url=self.endpoint_url,
            active_models=list(self._loaded_models.keys()),
            details={"mode": "unavailable", "reason": "llama-server offline and llama-cpp-python not installed"},
        )

    async def load_model(self, model_id: str, model_path: Optional[str] = None, **kwargs: Any) -> LoadedModelInstance:
        target_path = Path(model_path) if model_path else self._resolve_local_model_path(model_id)
        if target_path and target_path.exists() and self.is_in_process_supported():
            if model_id not in self._in_process_llms:
                try:
                    from llama_cpp import Llama
                    loop = asyncio.get_running_loop()
                    llm = await loop.run_in_executor(
                        None,
                        lambda: Llama(
                            model_path=str(target_path),
                            n_threads=self.threads,
                            n_ctx=self.context_window,
                            verbose=False,
                        ),
                    )
                    self._in_process_llms[model_id] = llm
                    logger.info(f"Loaded in-process llama.cpp model '{model_id}' from {target_path}")
                except Exception as e:
                    logger.warning(f"Failed to load in-process model '{model_id}': {e}")

        ram_mb = kwargs.get("ram_mb", 1200.0)
        instance = LoadedModelInstance(
            model_id=model_id,
            backend_type=self.backend_type,
            loaded_at=time.time(),
            ram_usage_mb=ram_mb,
            device=kwargs.get("device", "cpu"),
            is_ready=True,
        )
        self._loaded_models[model_id] = instance
        return instance

    def is_model_loaded(self, model_id: str) -> bool:
        return model_id in self._loaded_models

    async def unload_model(self, model_id: str) -> bool:
        unloaded = False
        if model_id in self._in_process_llms:
            del self._in_process_llms[model_id]
            gc.collect()
            unloaded = True
        if model_id in self._loaded_models:
            del self._loaded_models[model_id]
            unloaded = True
        return unloaded

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
        # Mode A: In-Process execution
        if model_id in self._in_process_llms:
            llm = self._in_process_llms[model_id]
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            loop = asyncio.get_running_loop()
            output = await loop.run_in_executor(
                None,
                lambda: llm.create_chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stop=stop_sequences or [],
                ),
            )
            choice = output["choices"][0]["message"]
            text = choice.get("content", "")
            usage = output.get("usage", {})
            return CompletionResponse(
                text=text.strip(),
                model=model_id,
                usage=TokenUsage(
                    prompt_tokens=usage.get("prompt_tokens", len(prompt.split())),
                    completion_tokens=usage.get("completion_tokens", len(text.split())),
                    total_tokens=usage.get("total_tokens", len(prompt.split()) + len(text.split())),
                ),
                raw_output=output,
            )

        # Mode B: Server HTTP execution
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
        # Mode A: In-Process embedding
        if model_id in self._in_process_llms:
            llm = self._in_process_llms[model_id]
            loop = asyncio.get_running_loop()
            output = await loop.run_in_executor(
                None,
                lambda: llm.create_embedding(input=texts),
            )
            items = output.get("data", [])
            responses = []
            for item in items:
                vec = item.get("embedding", [])
                responses.append(EmbeddingResponse(vector=vec, dim=len(vec), model=model_id))
            return responses

        # Mode B: Server HTTP embedding
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
