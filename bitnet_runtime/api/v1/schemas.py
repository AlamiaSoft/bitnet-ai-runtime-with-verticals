from __future__ import annotations
import enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

class TaskType(str, enum.Enum):
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    RAG_QA = "rag_qa"
    REASONING = "reasoning"
    CODING = "coding"
    CREATIVE = "creative"
    DIALOGUE = "dialogue"
    HIGH_RISK_ACTION = "high_risk_action"

class PrivacyRequirement(str, enum.Enum):
    AIRGAPPED_LOCAL_ONLY = "airgapped_local_only"
    LOCAL_NETWORK = "local_network"
    CLOUD_PERMITTED = "cloud_permitted"

class LatencyPreference(str, enum.Enum):
    ULTRA_LOW = "ultra_low"
    LOW = "low"
    BALANCED = "balanced"
    THOROUGH = "thorough"

class RequirementsSpec(BaseModel):
    privacy: PrivacyRequirement = Field(
        default=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY,
        description="Privacy boundary constraint. Default is strict airgap local execution."
    )
    latency: LatencyPreference = Field(
        default=LatencyPreference.BALANCED,
        description="Latency vs throughput optimization preference."
    )
    min_quality: float = Field(
        default=3.0,
        ge=1.0,
        le=5.0,
        description="Minimum capability score required for the candidate model."
    )
    max_budget_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Maximum cost allowance. 0.0 enforces free local execution."
    )
    preferred_model_id: Optional[str] = Field(
        default=None,
        description="Optional direct model override if permitted by policy."
    )

class ExecutionMetadata(BaseModel):
    request_id: str = Field(description="Globally unique identifier for tracing this request.")
    model_id: str = Field(description="Identifier of the model that executed the task.")
    provider: str = Field(description="Execution provider.")
    endpoint: str = Field(description="Serving endpoint location.")
    latency_ms: float = Field(description="Total execution latency in milliseconds.")
    prompt_tokens: int = Field(default=0, description="Number of input prompt tokens.")
    completion_tokens: int = Field(default=0, description="Number of generated output tokens.")
    total_tokens: int = Field(default=0, description="Total tokens processed.")
    estimated_cost_usd: float = Field(default=0.0, description="Estimated cost in USD.")
    trace_id: Optional[str] = Field(default=None, description="Trace ID in observability ledger.")
    fallback_invoked: bool = Field(default=False, description="Whether failover fallback was invoked.")
    verification_passed: bool = Field(default=True, description="Whether output verification passed.")
    runtime_type: Optional[str] = Field(default=None, description="Execution runtime provider (native_cpu, native_gpu, container, remote_fallback).")
    execution_target: Optional[str] = Field(default=None, description="Physical execution target (e.g. local_cpu_native, local_cpu_inprocess, local_cpu_container, remote_vps_fallback).")
    model_reason: Optional[str] = Field(default=None, description="Stage 1 Model Selection rationale.")
    execution_reason: Optional[str] = Field(default=None, description="Stage 2 Execution Placement rationale.")
    why: Optional[str] = Field(default=None, description="Unified end-to-end explainability audit string.")

class InferenceRequest(BaseModel):
    prompt: str = Field(description="The raw prompt, query, or task input.")
    task: TaskType = Field(default=TaskType.REASONING, description="Primary capability required.")
    system_prompt: Optional[str] = Field(default=None, description="Optional system prompt.")
    schema_definition: Optional[Dict[str, Any]] = Field(default=None, description="Optional JSON Schema.")
    requirements: RequirementsSpec = Field(default_factory=RequirementsSpec)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=8192)

class InferenceResponse(BaseModel):
    text: str = Field(description="Generated text output.")
    parsed_json: Optional[Dict[str, Any]] = Field(default=None, description="Parsed JSON object.")
    metadata: ExecutionMetadata = Field(description="Execution telemetry metadata.")

class ChatMessage(BaseModel):
    role: str = Field(description="Message role: system, user, assistant, tool")
    content: str = Field(description="Message text content")
    name: Optional[str] = Field(default=None)

class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(description="Conversation history ordered chronologically.")
    task: TaskType = Field(default=TaskType.DIALOGUE)
    requirements: RequirementsSpec = Field(default_factory=RequirementsSpec)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=8192)
    stream: bool = Field(default=False)

class ChatResponse(BaseModel):
    message: ChatMessage = Field(description="Generated assistant message.")
    metadata: ExecutionMetadata = Field(description="Execution telemetry metadata.")

class ExtractRequest(BaseModel):
    text: str = Field(description="Source text to extract fields from.")
    target_schema: Dict[str, Any] = Field(description="JSON Schema defining expected structure.")
    instructions: Optional[str] = Field(default=None)
    requirements: RequirementsSpec = Field(default_factory=RequirementsSpec)

class ExtractResponse(BaseModel):
    data: Dict[str, Any] = Field(description="Extracted data matching target schema.")
    raw_text: str = Field(description="Raw model output string.")
    is_valid_schema: bool = Field(default=True)
    metadata: ExecutionMetadata

class ClassifyRequest(BaseModel):
    text: str = Field(description="Text content to classify.")
    categories: List[str] = Field(description="Candidate category labels.")
    multi_label: bool = Field(default=False)
    requirements: RequirementsSpec = Field(default_factory=RequirementsSpec)

class ClassifyResponse(BaseModel):
    top_category: str = Field(description="Highest confidence category.")
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    metadata: ExecutionMetadata

class EmbeddingRequest(BaseModel):
    input: Union[str, List[str]] = Field(description="Text string or list of text strings.")
    model_id: Optional[str] = Field(default=None)

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]] = Field(description="Generated vector embeddings.")
    dimension: int = Field(description="Vector dimension size.")
    metadata: ExecutionMetadata

class RerankRequest(BaseModel):
    query: str = Field(description="Search query or reference prompt.")
    documents: List[str] = Field(description="Candidate document passages to score and rank.")
    top_k: int = Field(default=5, ge=1)

class RerankItem(BaseModel):
    index: int
    document: str
    score: float

class RerankResponse(BaseModel):
    ranked_documents: List[RerankItem]
    metadata: ExecutionMetadata

class HealthResponse(BaseModel):
    status: str = Field(default="healthy")
    version: str = Field(default="0.1.0")
    runtime_mode: str = Field(default="local_first_cpu")
    backends: Dict[str, Any] = Field(default_factory=dict)
    active_models: List[str] = Field(default_factory=list)
    total_ram_used_mb: float = Field(default=0.0)

class CapabilityItem(BaseModel):
    task_type: str
    description: str
    primary_model: str
    serving_endpoint: str
    privacy_level: str

class CapabilityListResponse(BaseModel):
    capabilities: List[CapabilityItem]

class ApiErrorEnvelope(BaseModel):
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: Optional[str] = None
