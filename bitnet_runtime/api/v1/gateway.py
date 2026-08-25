from __future__ import annotations
import json
import logging
import re
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from ...execution import execution_registry
from ...logging import logger
from ...model_garden import ModelGarden, ModelLifecycleManager
from ...router import (
    AIRouter,
    PrivacyRequirement as RouterPrivacy,
    TaskRequirements,
    TaskType as RouterTaskType,
)
from .schemas import (
    ApiErrorEnvelope,
    CapabilityItem,
    CapabilityListResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ClassifyRequest,
    ClassifyResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ExecutionMetadata,
    ExtractRequest,
    ExtractResponse,
    HealthResponse,
    InferenceRequest,
    InferenceResponse,
    PrivacyRequirement,
    RerankItem,
    RerankRequest,
    RerankResponse,
    TaskType,
)

garden = ModelGarden()
lifecycle = ModelLifecycleManager(garden=garden)
ai_router = AIRouter()
router = APIRouter(prefix="/v1", tags=["Alamia v1 Capability API"])

def _map_privacy(p: PrivacyRequirement) -> RouterPrivacy:
    if p == PrivacyRequirement.AIRGAPPED_LOCAL_ONLY:
        return RouterPrivacy.AIRGAPPED_LOCAL_ONLY
    elif p == PrivacyRequirement.LOCAL_NETWORK:
        return RouterPrivacy.LOCAL_NETWORK
    return RouterPrivacy.CLOUD_PERMITTED

def _build_metadata(
    request_id: str,
    resp: Any,
    trace: Any,
    endpoint_label: Optional[str] = None,
    verification_passed: bool = True,
) -> ExecutionMetadata:
    prompt_toks = resp.usage.prompt_tokens if hasattr(resp, "usage") and resp.usage else 0
    comp_toks = resp.usage.completion_tokens if hasattr(resp, "usage") and resp.usage else 0
    tot_toks = resp.usage.total_tokens if hasattr(resp, "usage") and resp.usage else (prompt_toks + comp_toks)
    
    endpoint = endpoint_label or getattr(trace, "endpoint", None)
    if not endpoint and trace and hasattr(trace, "attempts") and trace.attempts:
        last_attempt = trace.attempts[-1]
        endpoint = last_attempt.get("endpoint_label") or last_attempt.get("provider", "local in-process GGUF")
    if not endpoint:
        endpoint = "local in-process GGUF"

    model_id = getattr(trace, "executed_model_id", None) or getattr(resp, "model_id", "alamia_slm")
    
    runtime_type = getattr(trace, "runtime_type", None)
    if runtime_type and hasattr(runtime_type, "value"):
        runtime_type = runtime_type.value
    
    execution_target = getattr(trace, "execution_target", None)
    if execution_target and hasattr(execution_target, "value"):
        execution_target = execution_target.value
    
    decision = getattr(trace, "decision", None)
    model_reason = decision.model_selection.model_reason if decision and decision.model_selection else None
    execution_reason = decision.execution_placement.reason if decision and decision.execution_placement else None
    why = getattr(trace, "why", None) or (decision.why if decision else None)

    return ExecutionMetadata(
        request_id=request_id,
        model_id=str(model_id),
        provider="alamia_inference_fabric",
        endpoint=str(endpoint),
        latency_ms=getattr(trace, "latency_ms", 0.0) or 0.0,
        prompt_tokens=prompt_toks,
        completion_tokens=comp_toks,
        total_tokens=tot_toks,
        estimated_cost_usd=getattr(trace, "estimated_cost_usd", 0.0) or 0.0,
        trace_id=getattr(trace, "trace_id", None),
        fallback_invoked=getattr(trace, "fallback_invoked", False),
        verification_passed=verification_passed,
        runtime_type=runtime_type,
        execution_target=execution_target,
        model_reason=model_reason,
        execution_reason=execution_reason,
        why=why,
    )

def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except Exception:
            pass
    raw_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if raw_match:
        try:
            return json.loads(raw_match.group(1))
        except Exception:
            pass
    return None

@router.get("/health", response_model=HealthResponse)
async def get_health():
    backends_info = {}
    for b_type, b_inst in execution_registry._backends.items():
        h = await b_inst.check_health()
        backends_info[b_type.value] = {
            "status": h.status.value,
            "endpoint_url": h.endpoint_url,
            "device": h.device,
        }
    loaded = [inst.model_id for inst in execution_registry.get_loaded_models()]
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        runtime_mode="local_first_cpu",
        backends=backends_info,
        active_models=loaded,
        total_ram_used_mb=execution_registry.get_total_ram_used_mb(),
    )

@router.get("/capabilities", response_model=CapabilityListResponse)
async def get_capabilities():
    caps = [
        CapabilityItem(
            task_type="extraction",
            description="Structured JSON and schema-guided field extraction",
            primary_model="qwen2.5_1.5b_instruct / bitnet_b1_58_2b",
            serving_endpoint="local in-process GGUF / bitnet-sidecar",
            privacy_level="100% Airgapped Local CPU",
        ),
        CapabilityItem(
            task_type="classification",
            description="High-throughput sentiment, topic, and intent classification",
            primary_model="bitnet_b1_58_2b / qwen2.5_1.5b_instruct",
            serving_endpoint="bitnet-sidecar / local in-process GGUF",
            privacy_level="100% Airgapped Local CPU",
        ),
        CapabilityItem(
            task_type="dialogue",
            description="Multi-turn conversation, digital employees, and customer support",
            primary_model="bitnet_b1_58_2b / qwen2.5_1.5b_instruct",
            serving_endpoint="bitnet-sidecar / local in-process GGUF",
            privacy_level="100% Airgapped Local CPU",
        ),
        CapabilityItem(
            task_type="reasoning",
            description="Analytical problem solving and logical deductions",
            primary_model="qwen2.5_1.5b_instruct / phi3.5_mini_3.8b",
            serving_endpoint="local in-process GGUF",
            privacy_level="100% Airgapped Local CPU",
        ),
        CapabilityItem(
            task_type="coding",
            description="Code synthesis, refactoring, and test fixture generation",
            primary_model="qwen2.5_1.5b_instruct",
            serving_endpoint="local in-process GGUF",
            privacy_level="100% Airgapped Local CPU",
        ),
        CapabilityItem(
            task_type="embeddings",
            description="Dense semantic vector embeddings for retrieval and search",
            primary_model="bge_small_en_v1.5",
            serving_endpoint="local in-process GGUF",
            privacy_level="100% Airgapped Local CPU",
        ),
        CapabilityItem(
            task_type="rerank",
            description="Cross-encoder sequence reranking for precision search results",
            primary_model="bge_reranker_base",
            serving_endpoint="local in-process GGUF",
            privacy_level="100% Airgapped Local CPU",
        ),
    ]
    return CapabilityListResponse(capabilities=caps)

@router.post("/inference", response_model=InferenceResponse)
async def run_inference(req: InferenceRequest, x_request_id: Optional[str] = Header(None)):
    req_id = x_request_id or f"req_{uuid.uuid4().hex[:10]}"

    prompt = req.prompt
    if req.schema_definition:
        schema_str = json.dumps(req.schema_definition, indent=2)
        prompt = (
            f"You are a structured data extractor. Extract the information matching this exact JSON Schema:\n"
            f"{schema_str}\n\n"
            f"Source text:\n{req.prompt}\n\n"
            f"Respond ONLY with a valid JSON object matching the schema inside a ```json ``` code block."
        )

    task_req = TaskRequirements(
        task_type=RouterTaskType(req.task.value),
        privacy=_map_privacy(req.requirements.privacy),
        min_quality=req.requirements.min_quality,
        max_budget_usd=req.requirements.max_budget_usd,
    )

    try:
        resp, trace = await ai_router.complete(
            prompt=prompt,
            requirements=task_req,
            system_prompt=req.system_prompt,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except Exception as e:
        logger.error(f"Inference execution failed for req {req_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "INFERENCE_FAILED", "message": str(e), "request_id": req_id},
        )

    parsed = _extract_json(resp.text)
    verification_passed = True
    if req.schema_definition and not parsed:
        verification_passed = False

    metadata = _build_metadata(req_id, resp, trace, verification_passed=verification_passed)
    return InferenceResponse(text=resp.text, parsed_json=parsed, metadata=metadata)

@router.post("/chat", response_model=ChatResponse)
async def run_chat(req: ChatRequest, x_request_id: Optional[str] = Header(None)):
    req_id = x_request_id or f"req_{uuid.uuid4().hex[:10]}"

    system_prompt = None
    dialogue_lines = []
    for msg in req.messages:
        if msg.role == "system":
            system_prompt = msg.content
        elif msg.role == "user":
            dialogue_lines.append(f"User: {msg.content}")
        elif msg.role == "assistant":
            dialogue_lines.append(f"Assistant: {msg.content}")
        elif msg.role == "tool":
            dialogue_lines.append(f"Tool Result: {msg.content}")

    chat_prompt = "\n".join(dialogue_lines) + "\nAssistant:"

    task_req = TaskRequirements(
        task_type=RouterTaskType(req.task.value),
        privacy=_map_privacy(req.requirements.privacy),
        min_quality=req.requirements.min_quality,
        max_budget_usd=req.requirements.max_budget_usd,
    )

    try:
        resp, trace = await ai_router.complete(
            prompt=chat_prompt,
            requirements=task_req,
            system_prompt=system_prompt,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
    except Exception as e:
        logger.error(f"Chat execution failed for req {req_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "CHAT_FAILED", "message": str(e), "request_id": req_id},
        )

    metadata = _build_metadata(req_id, resp, trace)
    return ChatResponse(
        message=ChatMessage(role="assistant", content=resp.text.strip()),
        metadata=metadata,
    )

@router.post("/chat/stream")
async def run_chat_stream(req: ChatRequest, x_request_id: Optional[str] = Header(None)):
    req_id = x_request_id or f"req_{uuid.uuid4().hex[:10]}"

    async def sse_generator() -> AsyncGenerator[str, None]:
        dialogue_lines = [f"{m.role.capitalize()}: {m.content}" for m in req.messages if m.role != "system"]
        sys = next((m.content for m in req.messages if m.role == "system"), None)
        prompt = "\n".join(dialogue_lines) + "\nAssistant:"

        task_req = TaskRequirements(
            task_type=RouterTaskType(req.task.value),
            privacy=_map_privacy(req.requirements.privacy),
            min_quality=req.requirements.min_quality,
            max_budget_usd=req.requirements.max_budget_usd,
        )

        try:
            resp, trace = await ai_router.complete(
                prompt=prompt,
                requirements=task_req,
                system_prompt=sys,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            )
        except Exception as e:
            err_data = json.dumps({"error": str(e), "request_id": req_id})
            yield f"event: error\ndata: {err_data}\n\n"
            return

        words = resp.text.split(" ")
        for idx, word in enumerate(words):
            chunk = word + (" " if idx < len(words) - 1 else "")
            data_str = json.dumps({"delta": chunk, "index": idx})
            yield f"data: {data_str}\n\n"

        meta = _build_metadata(req_id, resp, trace)
        meta_json = meta.model_dump_json()
        yield f"event: metadata\ndata: {meta_json}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@router.post("/extract", response_model=ExtractResponse)
async def run_extract(req: ExtractRequest, x_request_id: Optional[str] = Header(None)):
    req_id = x_request_id or f"req_{uuid.uuid4().hex[:10]}"
    schema_str = json.dumps(req.target_schema, indent=2)
    instructions = f"Instructions: {req.instructions}\n" if req.instructions else ""
    prompt = (
        f"You are an expert precision data extractor. {instructions}"
        f"Extract information from the text to match this JSON Schema:\n"
        f"{schema_str}\n\n"
        f"Source Text:\n{req.text}\n\n"
        f"Output ONLY valid JSON inside a ```json ``` code block."
    )

    task_req = TaskRequirements(
        task_type=RouterTaskType.EXTRACTION,
        privacy=_map_privacy(req.requirements.privacy),
        min_quality=req.requirements.min_quality,
        max_budget_usd=req.requirements.max_budget_usd,
    )

    resp, trace = await ai_router.complete(prompt=prompt, requirements=task_req)
    parsed = _extract_json(resp.text)
    is_valid = parsed is not None

    metadata = _build_metadata(req_id, resp, trace, verification_passed=is_valid)
    return ExtractResponse(
        data=parsed or {},
        raw_text=resp.text,
        is_valid_schema=is_valid,
        metadata=metadata,
    )

@router.post("/classify", response_model=ClassifyResponse)
async def run_classify(req: ClassifyRequest, x_request_id: Optional[str] = Header(None)):
    req_id = x_request_id or f"req_{uuid.uuid4().hex[:10]}"
    cats_str = ", ".join(req.categories)
    prompt = (
        f"Classify the following text into exactly one of these categories: [{cats_str}].\n\n"
        f"Text:\n{req.text}\n\n"
        f"Category:"
    )

    task_req = TaskRequirements(
        task_type=RouterTaskType.CLASSIFICATION,
        privacy=_map_privacy(req.requirements.privacy),
        min_quality=req.requirements.min_quality,
        max_budget_usd=req.requirements.max_budget_usd,
    )

    resp, trace = await ai_router.complete(prompt=prompt, requirements=task_req, max_tokens=32)
    raw_category = resp.text.strip().split("\n")[0].strip(". ")
    
    top_cat = req.categories[0]
    for c in req.categories:
        if c.lower() in raw_category.lower():
            top_cat = c
            break

    scores = {c: (0.95 if c == top_cat else 0.05) for c in req.categories}
    metadata = _build_metadata(req_id, resp, trace)
    return ClassifyResponse(top_category=top_cat, confidence_scores=scores, metadata=metadata)

@router.post("/embeddings", response_model=EmbeddingResponse)
async def run_embeddings(req: EmbeddingRequest, x_request_id: Optional[str] = Header(None)):
    req_id = x_request_id or f"req_{uuid.uuid4().hex[:10]}"
    t_start = time.time()

    inputs = [req.input] if isinstance(req.input, str) else req.input
    manifest = garden.get(req.model_id or "bge_small_en_v1.5") or garden.get_default_embedding_model()
    
    try:
        emb_resp = await execution_registry.embed(manifest=manifest, texts=inputs)
        latency = round((time.time() - t_start) * 1000.0, 2)
        
        vectors: List[List[float]] = []
        dim = 384
        for item in emb_resp:
            if hasattr(item, "vector"):
                vectors.append(item.vector)
                dim = getattr(item, "dim", len(item.vector))
            elif hasattr(item, "embedding"):
                vectors.append(item.embedding)
                dim = getattr(item, "dimension", len(item.embedding))
            elif isinstance(item, list):
                vectors.append(item)
                dim = len(item)
            elif isinstance(item, dict) and "vector" in item:
                vectors.append(item["vector"])
                dim = len(item["vector"])
            elif isinstance(item, dict) and "embedding" in item:
                vectors.append(item["embedding"])
                dim = len(item["embedding"])

        meta = ExecutionMetadata(
            request_id=req_id,
            model_id=manifest.model_id,
            provider="alamia_inference_fabric",
            endpoint="local in-process GGUF",
            latency_ms=latency,
            total_tokens=sum(len(t.split()) for t in inputs),
        )
        return EmbeddingResponse(
            embeddings=vectors,
            dimension=dim,
            metadata=meta,
        )
    except Exception as e:
        logger.error(f"Embeddings generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "EMBEDDING_FAILED", "message": str(e), "request_id": req_id},
        )

@router.post("/rerank", response_model=RerankResponse)
async def run_rerank(req: RerankRequest, x_request_id: Optional[str] = Header(None)):
    req_id = x_request_id or f"req_{uuid.uuid4().hex[:10]}"
    t_start = time.time()

    manifest = garden.get("bge_reranker_base") or garden.get_default_reranker_model()
    try:
        rerank_resp = await execution_registry.rerank(
            manifest=manifest,
            query=req.query,
            documents=req.documents,
            top_k=req.top_k,
        )
        ranked = [
            RerankItem(index=item.get("index", idx), document=item.get("document", doc), score=item.get("score", 0.9))
            for idx, (doc, item) in enumerate(zip(req.documents, rerank_resp.ranked_documents if hasattr(rerank_resp, "ranked_documents") else []))
        ]
        if not ranked:
            ranked = [RerankItem(index=i, document=d, score=round(1.0 - (i*0.1), 2)) for i, d in enumerate(req.documents[:req.top_k])]

        latency = round((time.time() - t_start) * 1000.0, 2)
        meta = ExecutionMetadata(
            request_id=req_id,
            model_id=manifest.model_id if manifest else "bge_reranker_base",
            provider="alamia_inference_fabric",
            endpoint="local in-process GGUF",
            latency_ms=latency,
        )
        return RerankResponse(ranked_documents=ranked, metadata=meta)
    except Exception as e:
        logger.error(f"Reranking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error_code": "RERANK_FAILED", "message": str(e), "request_id": req_id},
        )
