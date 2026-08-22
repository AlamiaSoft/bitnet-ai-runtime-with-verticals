from __future__ import annotations
import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

class TaskType(str, enum.Enum):
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    SUMMARIZATION = "summarization"
    RAG_QA = "rag_qa"
    REASONING = "reasoning"
    CODING = "coding"
    CREATIVE = "creative"
    HIGH_RISK_ACTION = "high_risk_action"

class ModelTier(str, enum.Enum):
    LOCAL_1BIT = "local_1bit"          # Ultra-fast, zero-cost, CPU-optimized 1-bit models
    LOCAL_DENSE = "local_dense"        # Local CPU/GPU quantized dense models (8B/14B)
    CLOUD_FRONTIER = "cloud_frontier"  # External frontier models (OpenAI, Claude, DeepSeek)

class ModelModality(str, enum.Enum):
    GENERATIVE_TEXT = "generative_text"
    EMBEDDING = "embedding"
    RERANKER = "reranker"
    VISION = "vision"
    SPEECH = "speech"

class ModelFamily(str, enum.Enum):
    BITNET = "bitnet"
    PHI = "phi"
    QWEN = "qwen"
    GEMMA = "gemma"
    LLAMA = "llama"
    BGE = "bge"
    MINILM = "minilm"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    CUSTOM = "custom"

@dataclass
class HardwareRequirements:
    min_ram_mb: int = 1000
    recommended_threads: int = 4
    quantization: str = "q4_k_m"  # "1bit_ternary", "q4_k_m", "q8_0", "fp16"
    requires_gpu: bool = False
    cpu_archs: List[str] = field(default_factory=lambda: ["x86_64", "arm64"])

@dataclass
class ModelManifest:
    model_id: str
    name: str
    family: ModelFamily
    modality: ModelModality
    tier: ModelTier
    parameter_size: str = "2B"
    context_window: int = 4096
    hardware: HardwareRequirements = field(default_factory=HardwareRequirements)
    provider_backend: str = "bitnet"  # "bitnet", "llamacpp", "local_endpoint", "cloud", "mock"
    task_ratings: Dict[TaskType, float] = field(default_factory=dict)
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    typical_latency_ms: float = 200.0
    license: str = "MIT / Apache-2.0"
    description: str = ""
    is_healthy: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_task_rating(self, task_type: TaskType) -> float:
        """Returns the benchmarked capability rating for a specific task (1.0 to 5.0)."""
        return self.task_ratings.get(task_type, 2.5)
