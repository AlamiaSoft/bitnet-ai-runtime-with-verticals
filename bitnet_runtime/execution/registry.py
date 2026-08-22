from __future__ import annotations
import logging
import time
from typing import Any, Dict, List, Optional
from .base import (
    BackendHealth,
    BackendStatus,
    BackendType,
    ExecutionBackend,
    LoadedModelInstance,
    RerankResponse,
)
from .backends import BitNetBackend, LlamaCppBackend, MockExecutionBackend, TEIBackend
from ..inference.base import CompletionResponse, EmbeddingResponse
from ..model_garden.models import ModelManifest, ModelModality

logger = logging.getLogger(__name__)

class ModelNotLoadedError(RuntimeError):
    """Raised when attempting inference on a model that is not loaded in memory."""
    pass

class ExecutionRegistry:
    """
    Central Orchestration Registry managing all execution backends,
    active model instances in RAM, and routing requests to the appropriate engine.
    """

    def __init__(self, use_mock_fallback_for_tests: bool = True):
        self.use_mock = use_mock_fallback_for_tests
        self._backends: Dict[BackendType, ExecutionBackend] = {
            BackendType.LLAMACPP: LlamaCppBackend(),
            BackendType.TEI: TEIBackend(),
            BackendType.BITNET_SIDECAR: BitNetBackend(),
            BackendType.MOCK: MockExecutionBackend(),
        }
        self._loaded_instances: Dict[str, LoadedModelInstance] = {}

    def register_backend(self, backend: ExecutionBackend) -> None:
        self._backends[backend.backend_type] = backend

    def get_backend(self, backend_type: BackendType) -> Optional[ExecutionBackend]:
        return self._backends.get(backend_type)

    async def get_all_health(self) -> Dict[str, BackendHealth]:
        statuses = {}
        for b_type, backend in self._backends.items():
            statuses[b_type.value] = await backend.check_health()
        return statuses

    async def resolve_backend_for_model(self, manifest: ModelManifest) -> ExecutionBackend:
        """
        Dynamically resolves the active operational backend based on model modality and server health:
        1. llama.cpp backend  <- PRIMARY (generative SLMs, GGUF embeddings, rerankers)
        2. BitNet backend     <- ONLY where native BitNet 1-bit support
        3. TEI backend        <- Specialized fallback/optimization for embeddings/reranking
        4. Mock backend       <- Offline test suites
        """
        # 1. Native BitNet sidecar (only for BitNet model family)
        if manifest.family == "bitnet":
            bitnet = self._backends[BackendType.BITNET_SIDECAR]
            h_b = await bitnet.check_health()
            if h_b.status == BackendStatus.ONLINE:
                return bitnet

        # 2. llama.cpp (Primary for all generative SLMs, GGUF embeddings, and reranking)
        llama = self._backends[BackendType.LLAMACPP]
        h_llama = await llama.check_health()
        if h_llama.status == BackendStatus.ONLINE:
            return llama

        # 3. TEI (Specialized fallback/optimization for embedding & reranker models)
        if manifest.modality in (ModelModality.EMBEDDING, ModelModality.RERANKER):
            tei = self._backends[BackendType.TEI]
            h_tei = await tei.check_health()
            if h_tei.status == BackendStatus.ONLINE:
                return tei

        # 4. Mock backend (for offline CI test suites)
        return self._backends[BackendType.MOCK]

    async def load_model(self, manifest: ModelManifest, model_path: Optional[str] = None) -> LoadedModelInstance:
        backend = await self.resolve_backend_for_model(manifest)
        instance = await backend.load_model(
            model_id=manifest.model_id,
            model_path=model_path,
            ram_mb=manifest.hardware.min_ram_mb,
        )
        self._loaded_instances[manifest.model_id] = instance
        logger.info(f"Model '{manifest.model_id}' successfully loaded via {backend.backend_type.value}")
        return instance

    async def unload_model(self, model_id: str) -> bool:
        if model_id in self._loaded_instances:
            instance = self._loaded_instances[model_id]
            backend = self._backends.get(instance.backend_type)
            if backend:
                await backend.unload_model(model_id)
            del self._loaded_instances[model_id]
            logger.info(f"Model '{model_id}' unloaded from RAM")
            return True
        return False

    def is_model_loaded(self, model_id: str) -> bool:
        return model_id in self._loaded_instances

    def get_loaded_models(self) -> List[LoadedModelInstance]:
        return list(self._loaded_instances.values())

    def get_total_ram_used_mb(self) -> float:
        return sum(inst.ram_usage_mb for inst in self._loaded_instances.values())

    async def complete(
        self,
        manifest: ModelManifest,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
        stop_sequences: Optional[List[str]] = None,
        auto_load: bool = True,
        **kwargs: Any,
    ) -> CompletionResponse:
        model_id = manifest.model_id
        if not self.is_model_loaded(model_id):
            if auto_load:
                await self.load_model(manifest)
            else:
                raise ModelNotLoadedError(f"Model '{model_id}' is not loaded in memory.")

        instance = self._loaded_instances[model_id]
        backend = self._backends[instance.backend_type]
        return await backend.complete(
            model_id=model_id,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            stop_sequences=stop_sequences,
            **kwargs,
        )

    async def embed(
        self,
        manifest: ModelManifest,
        texts: List[str],
        auto_load: bool = True,
        **kwargs: Any,
    ) -> List[EmbeddingResponse]:
        model_id = manifest.model_id
        if not self.is_model_loaded(model_id):
            if auto_load:
                await self.load_model(manifest)
            else:
                raise ModelNotLoadedError(f"Model '{model_id}' is not loaded in memory.")

        instance = self._loaded_instances[model_id]
        backend = self._backends[instance.backend_type]
        try:
            return await backend.embed(model_id=model_id, texts=texts, **kwargs)
        except NotImplementedError:
            if self.use_mock:
                return await self._backends[BackendType.MOCK].embed(model_id=model_id, texts=texts, **kwargs)
            raise

    async def rerank(
        self,
        manifest: ModelManifest,
        query: str,
        documents: List[str],
        auto_load: bool = True,
        **kwargs: Any,
    ) -> RerankResponse:
        model_id = manifest.model_id
        if not self.is_model_loaded(model_id):
            if auto_load:
                await self.load_model(manifest)
            else:
                raise ModelNotLoadedError(f"Model '{model_id}' is not loaded in memory.")

        instance = self._loaded_instances[model_id]
        backend = self._backends[instance.backend_type]
        try:
            return await backend.rerank(model_id=model_id, query=query, documents=documents, **kwargs)
        except NotImplementedError:
            if self.use_mock:
                return await self._backends[BackendType.MOCK].rerank(model_id=model_id, query=query, documents=documents, **kwargs)
            raise

execution_registry = ExecutionRegistry()
