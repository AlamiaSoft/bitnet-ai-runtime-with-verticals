from __future__ import annotations
import enum
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from ..inference.base import CompletionResponse, TokenUsage
from ..model_garden.models import ModelTier, TaskType

class PrivacyRequirement(str, enum.Enum):
    AIRGAPPED_LOCAL_ONLY = "airgapped_local_only"  # 100% on-device CPU/RAM, no outbound net
    LOCAL_NETWORK = "local_network"                # Local LAN/Docker endpoint allowed
    CLOUD_ALLOWED = "cloud_allowed"                # Can send data to external cloud APIs

class LatencyRequirement(str, enum.Enum):
    REALTIME = "realtime"          # < 500ms (streaming, typing, UI triggers)
    INTERACTIVE = "interactive"    # < 3000ms (standard user dialogue)
    BATCH = "batch"                # Asynchronous background queues

class RuntimeType(str, enum.Enum):
    NATIVE_CPU = "native_cpu"           # In-process llama.cpp or native portable C++ binary
    NATIVE_GPU = "native_gpu"           # Local hardware acceleration
    CONTAINER = "container"             # Docker sidecar container (optional)
    REMOTE_FALLBACK = "remote_fallback" # Remote VPS / Cloud Tunnel
    CLOUD_FRONTIER = "cloud_frontier"   # External frontier model APIs (OpenAI, Anthropic)
    MOCK = "mock"

class ExecutionTarget(str, enum.Enum):
    LOCAL_CPU_INPROCESS = "local_cpu_inprocess"
    LOCAL_CPU_NATIVE = "local_cpu_native"
    LOCAL_CPU_CONTAINER = "local_cpu_container"
    LOCAL_GPU = "local_gpu"
    REMOTE_VPS_FALLBACK = "remote_vps_fallback"
    CLOUD_FRONTIER = "cloud_frontier"
    MOCK = "mock"

@dataclass
class ModelCapabilityProfile:
    model_id: str
    name: str
    tier: ModelTier
    provider: str                  # "bitnet", "llamacpp", "local_endpoint", "mock", "cloud"
    capabilities: Set[TaskType]
    task_ratings: Dict[TaskType, float] = field(default_factory=dict)
    context_window: int = 4096
    cost_per_1k_input: float = 0.0 # USD per 1k input tokens (0.0 for local)
    cost_per_1k_output: float = 0.0# USD per 1k output tokens (0.0 for local)
    typical_latency_ms: float = 200.0
    quality_score: float = 3.0     # Baseline general quality rating (1.0 to 5.0)
    is_healthy: bool = True
    is_installed: bool = False
    is_loaded: bool = False
    is_development_only: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TaskRequirements:
    task_type: TaskType = TaskType.REASONING
    min_quality: float = 2.0
    max_latency_ms: Optional[float] = None
    privacy: PrivacyRequirement = PrivacyRequirement.AIRGAPPED_LOCAL_ONLY
    latency: LatencyRequirement = LatencyRequirement.INTERACTIVE
    estimated_context_tokens: int = 500
    max_budget_usd: Optional[float] = 0.0
    preferred_tier: Optional[ModelTier] = None

@dataclass
class ModelSelectionResult:
    model_id: str
    model_name: str
    model_reason: str
    quality_score: float = 3.0
    candidate_scores: Dict[str, float] = field(default_factory=dict)
    fallback_chain: List[str] = field(default_factory=list)

@dataclass
class ExecutionPlacement:
    runtime_type: RuntimeType
    target: ExecutionTarget
    reason: str
    endpoint_url: str
    endpoint_label: str
    fallback_chain: List[str] = field(default_factory=list)
    why: str = ""

@dataclass
class RoutingDecision:
    primary_model: ModelCapabilityProfile
    fallback_chain: List[ModelCapabilityProfile]
    rationale: str
    candidate_scores: Dict[str, float] = field(default_factory=dict)
    model_selection: Optional[ModelSelectionResult] = None
    execution_placement: Optional[ExecutionPlacement] = None
    why: str = ""

@dataclass
class RoutingTrace:
    trace_id: str = field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:8]}")
    timestamp: float = field(default_factory=time.time)
    task_requirements: Optional[TaskRequirements] = None
    decision: Optional[RoutingDecision] = None
    executed_model_id: Optional[str] = None
    runtime_type: Optional[RuntimeType] = None
    execution_target: Optional[ExecutionTarget] = None
    endpoint: Optional[str] = None
    why: str = ""
    fallback_invoked: bool = False
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    token_usage: Optional[TokenUsage] = None
    estimated_cost_usd: float = 0.0
    success: bool = True
    error: Optional[str] = None
