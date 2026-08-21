from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional

@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

@dataclass
class CompletionResponse:
    text: str
    model: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    finish_reason: str = "stop"
    raw_output: Optional[Dict[str, Any]] = None

@dataclass
class EmbeddingResponse:
    vector: List[float]
    dim: int
    model: str

class InferenceEngine(ABC):
    """Abstract base class for all local and edge inference engines."""

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> CompletionResponse:
        """Generate a full completion for the given prompt."""
        pass

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
        stop_sequences: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """Stream completion tokens asynchronously."""
        yield ""

class EmbeddingEngine(ABC):
    """Abstract base class for local embedding generators."""

    @abstractmethod
    async def embed_text(self, text: str) -> EmbeddingResponse:
        """Generate an embedding vector for a single text chunk."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        """Generate embedding vectors for multiple text chunks."""
        pass
