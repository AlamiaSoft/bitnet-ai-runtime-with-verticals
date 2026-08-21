from __future__ import annotations
import hashlib
import math
from typing import List
import numpy as np
from .base import EmbeddingEngine, EmbeddingResponse

class BitNetEmbeddingEngine(EmbeddingEngine):
    """
    Lightweight, local embedding engine simulating 1-bit / ternary quantized
    embedding projections with deterministic high-entropy n-gram hashing and
    unit-norm cosine vector output.
    Zero cloud API calls, zero heavy PyTorch dependencies.
    """

    def __init__(self, dim: int = 128, quantize_1bit: bool = False):
        self.dim = dim
        self.quantize_1bit = quantize_1bit

    def _text_to_vector(self, text: str) -> List[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        words = text.lower().strip().split()
        if not words:
            return vec.tolist()

        for word in words:
            # Hash word into multiple pseudo-random dimensions
            h = hashlib.sha256(word.encode("utf-8")).digest()
            for i in range(0, len(h), 4):
                idx = int.from_bytes(h[i:i+2], byteorder="little") % self.dim
                sign = 1.0 if (h[i+2] % 2 == 0) else -1.0
                weight = 1.0 + (h[i+3] / 255.0)
                vec[idx] += sign * weight

        # Substring n-grams for typo robustness and semantic similarity
        for i in range(len(text) - 2):
            trigram = text[i:i+3].lower()
            h_tri = hashlib.md5(trigram.encode("utf-8")).digest()
            idx = int.from_bytes(h_tri[:2], byteorder="little") % self.dim
            vec[idx] += 0.5 if (h_tri[2] % 2 == 0) else -0.5

        if self.quantize_1bit:
            # 1-bit ternary quantization: {-1, 0, +1}
            mean = np.mean(np.abs(vec))
            threshold = 0.5 * mean
            quantized = np.zeros_like(vec)
            quantized[vec > threshold] = 1.0
            quantized[vec < -threshold] = -1.0
            vec = quantized

        norm = np.linalg.norm(vec)
        if norm > 1e-6:
            vec = vec / norm

        return vec.tolist()

    async def embed_text(self, text: str) -> EmbeddingResponse:
        vector = self._text_to_vector(text)
        return EmbeddingResponse(vector=vector, dim=self.dim, model="bitnet-embed-1bit")

    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        return [await self.embed_text(t) for t in texts]

class LocalCompactEmbeddingEngine(BitNetEmbeddingEngine):
    """Alias for local compact embedding engine."""
    pass
