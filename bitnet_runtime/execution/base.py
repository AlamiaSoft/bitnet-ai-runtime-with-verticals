from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from ..inference.base import CompletionResponse, EmbeddingResponse

class BackendType(str, Enum):
    LLAMACPP = "llamacpp"
    TEI = "tei"
    BITNET_SIDECAR = "bitnet_sidecar"
    MOCK = "mock"

class BackendStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    INITIALIZING = "initializing"

@dataclass
class BackendHealth:
    backend_type: BackendType
    status: BackendStatus
    endpoint_url: str
    active_models: List[str] = field(default_factory=list)
    memory_used_mb: float = 0.0
    device: str = "cpu"
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RerankItem:
    index: int
    score: float
    text: str

@dataclass
class RerankResponse:
    results: List[RerankItem]
    model: str
    latency_ms: float = 0.0

@dataclass
class LoadedModelInstance:
    model_id: str
    backend_type: BackendType
    loaded_at: float
    ram_usage_mb: float
    device: str = "cpu"
    is_ready: bool = True

class ExecutionBackend(ABC):
    """Abstract base interface for all concrete OSS inference serving engines."""

    @property
    @abstractmethod
    def backend_type(self) -> BackendType:
        pass

    @abstractmethod
    async def check_health(self) -> BackendHealth:
        """Verify connectivity and health of the serving engine."""
        pass

    @abstractmethod
    async def load_model(self, model_id: str, model_path: Optional[str] = None, **kwargs: Any) -> LoadedModelInstance:
        """Load model weights into engine memory."""
        pass

    @abstractmethod
    async def unload_model(self, model_id: str) -> bool:
        """Release model weights from engine memory."""
        pass

    @abstractmethod
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
        """Generate text completion."""
        pass

    @abstractmethod
    async def embed(
        self,
        model_id: str,
        texts: List[str],
        **kwargs: Any,
    ) -> List[EmbeddingResponse]:
        """Generate dense vector embeddings."""
        pass

    @abstractmethod
    async def rerank(
        self,
        model_id: str,
        query: str,
        documents: List[str],
        **kwargs: Any,
    ) -> RerankResponse:
        """Score and rerank documents given a query."""
        pass
