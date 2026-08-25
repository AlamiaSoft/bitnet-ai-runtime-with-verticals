import pytest
from bitnet_runtime.config import AppConfig
from bitnet_runtime.inference.mock_engine import MockInferenceEngine
from bitnet_runtime.router import (
    AIRouter,
    LatencyRequirement,
    ModelCapabilityProfile,
    ModelCapabilityRegistry,
    ModelTier,
    PrivacyRequirement,
    RoutingPolicyEngine,
    TaskRequirements,
    TaskType,
)

@pytest.fixture
def mock_router(tmp_path):
    cfg = AppConfig()
    cfg.inference.default_provider = "mock"
    cfg.memory.db_path = tmp_path / "router_test.db"

    registry = ModelCapabilityRegistry()
    test_profile = ModelCapabilityProfile(
        model_id="test_runtime_engine",
        name="Test Runtime Engine",
        tier=ModelTier.LOCAL_1BIT,
        provider="mock",
        capabilities=set(TaskType),
        task_ratings={t: 4.2 for t in TaskType},
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        typical_latency_ms=10.0,
        quality_score=4.2,
        is_development_only=False,
    )
    registry.register(test_profile)
    router = AIRouter(registry=registry, cfg=cfg)
    router._engine_cache["mock"] = MockInferenceEngine()
    return router

def test_mock_engine_excluded_from_production_routing():
    registry = ModelCapabilityRegistry()
    policy = RoutingPolicyEngine(registry)

    req = TaskRequirements(
        task_type=TaskType.DIALOGUE,
        privacy=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY,
    )
    decision = policy.evaluate_route(req)
    assert decision.primary_model.model_id != "mock_local_engine"
    assert "mock" not in decision.primary_model.model_id
    for m in decision.fallback_chain:
        assert m.model_id != "mock_local_engine"

def test_privacy_constraint_filtering():
    registry = ModelCapabilityRegistry()
    policy = RoutingPolicyEngine(registry)

    # 1. Strict airgapped local policy
    req_airgap = TaskRequirements(
        task_type=TaskType.REASONING,
        privacy=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY,
    )
    decision = policy.evaluate_route(req_airgap)
    assert decision.primary_model.tier in (ModelTier.LOCAL_1BIT, ModelTier.LOCAL_DENSE)
    # Ensure no cloud models in fallback chain
    for m in decision.fallback_chain:
        assert m.tier != ModelTier.CLOUD_FRONTIER

def test_classification_routes_to_local_1bit():
    registry = ModelCapabilityRegistry()
    policy = RoutingPolicyEngine(registry)

    req_classify = TaskRequirements(
        task_type=TaskType.CLASSIFICATION,
        privacy=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY,
    )
    decision = policy.evaluate_route(req_classify)
    assert decision.primary_model.tier == ModelTier.LOCAL_1BIT
    assert "bitnet" in decision.primary_model.model_id

def test_zero_budget_constraint_filtering():
    registry = ModelCapabilityRegistry()
    policy = RoutingPolicyEngine(registry)

    req_free = TaskRequirements(
        task_type=TaskType.CODING,
        privacy=PrivacyRequirement.CLOUD_ALLOWED,
        max_budget_usd=0.0,
    )
    decision = policy.evaluate_route(req_free)
    # Paid models must not be selected
    assert decision.primary_model.cost_per_1k_input == 0.0

@pytest.mark.asyncio
async def test_router_execution_and_decision_trace(mock_router):
    resp, trace = await mock_router.complete(
        prompt="Classify this lead as urgent: Need office space immediately",
        task_type=TaskType.CLASSIFICATION,
    )
    assert resp.text is not None
    assert trace.trace_id.startswith("trace_")
    assert trace.success is True
    assert trace.latency_ms > 0
    assert len(trace.attempts) >= 1
    assert trace.task_requirements.task_type == TaskType.CLASSIFICATION

@pytest.mark.asyncio
async def test_router_automatic_fallback_on_primary_failure(tmp_path):
    from bitnet_runtime.inference.base import InferenceEngine

    class BrokenInferenceEngine(InferenceEngine):
        async def complete(self, *args, **kwargs):
            raise ConnectionError("Simulated primary model connection error")

        async def stream(self, *args, **kwargs):
            raise ConnectionError("Simulated primary stream error")
            yield ""

    cfg = AppConfig()
    cfg.inference.default_provider = "mock"
    cfg.memory.db_path = tmp_path / "fallback_test.db"

    registry = ModelCapabilityRegistry()
    # Intentionally register a failing primary model
    failing_model = ModelCapabilityProfile(
        model_id="failing_primary",
        name="Failing Primary Engine",
        tier=ModelTier.LOCAL_1BIT,
        provider="broken_driver",
        capabilities={TaskType.EXTRACTION},
        task_ratings={TaskType.EXTRACTION: 10.0},
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        quality_score=10.0,  # High score so it is selected primary
    )
    registry.register(failing_model)

    router = AIRouter(registry=registry, cfg=cfg)
    router._engine_cache["broken_driver"] = BrokenInferenceEngine()

    req = TaskRequirements(
        task_type=TaskType.EXTRACTION,
        privacy=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY,
    )

    resp, trace = await router.complete(
        prompt="Extract phone number: +1-555-0199",
        requirements=req,
    )

    # Should have survived by falling back to healthy mock engine
    assert resp.text is not None
    assert trace.success is True
    assert trace.fallback_invoked is True
    assert len(trace.attempts) >= 2
    assert trace.attempts[0]["success"] is False
    assert trace.attempts[-1]["success"] is True

def test_heuristic_task_inference(mock_router):
    req1 = mock_router.infer_task_requirements("Please classify this customer ticket priority")
    assert req1.task_type == TaskType.CLASSIFICATION

    req2 = mock_router.infer_task_requirements("Extract the json fields: name, email, phone")
    assert req2.task_type == TaskType.EXTRACTION

    req3 = mock_router.infer_task_requirements("def calculate_tax(revenue): return revenue * 0.15")
    assert req3.task_type == TaskType.CODING

    req4 = mock_router.infer_task_requirements("Generate a morning executive briefing digest")
    assert req4.task_type == TaskType.SUMMARIZATION

    # Ambiguous / casual inputs MUST NOT default to reasoning
    req5 = mock_router.infer_task_requirements("123")
    assert req5.task_type == TaskType.DIALOGUE

    req6 = mock_router.infer_task_requirements("Recommend 3 romantic Indian songs")
    assert req6.task_type == TaskType.DIALOGUE

    # Explicit deep analytical tasks trigger reasoning
    req7 = mock_router.infer_task_requirements("Please prove by mathematical induction that n^2 >= 0")
    assert req7.task_type == TaskType.REASONING

@pytest.mark.asyncio
async def test_two_stage_routing_decision_structure(mock_router):
    resp, trace = await mock_router.complete(
        prompt="Hi, what is your name?",
        task_type=TaskType.DIALOGUE,
    )
    assert trace.decision is not None
    assert trace.decision.model_selection is not None
    assert trace.decision.model_selection.model_reason != ""
    assert trace.decision.execution_placement is not None
    assert trace.decision.execution_placement.runtime_type is not None
    assert trace.decision.execution_placement.target is not None
    assert trace.why != ""
    assert "->" in trace.why

@pytest.mark.asyncio
async def test_runtime_resolver_native_first_resolution():
    from bitnet_runtime.execution.runtime_resolver import ExecutionRuntimeResolver
    from bitnet_runtime.model_garden.catalog import ModelGarden
    from bitnet_runtime.router.models import RuntimeType

    garden = ModelGarden()
    bitnet_manifest = garden.get("bitnet_b1_58_2b")
    assert bitnet_manifest is not None

    resolver = ExecutionRuntimeResolver()
    placement = await resolver.resolve_execution(bitnet_manifest, privacy=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY)
    assert placement.runtime_type in (RuntimeType.NATIVE_CPU, RuntimeType.CONTAINER)
    assert placement.target is not None
    assert placement.endpoint_url != ""
    assert placement.why != ""

    # Test in-process GGUF resolution
    qwen_manifest = garden.get("qwen2.5_1.5b_instruct")
    if qwen_manifest:
        placement_qwen = await resolver.resolve_execution(qwen_manifest, privacy=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY)
        assert placement_qwen.runtime_type == RuntimeType.NATIVE_CPU
        assert "In-Process GGUF" in placement_qwen.endpoint_label

@pytest.mark.asyncio
async def test_runtime_resolver_avx2_missing_fallback(monkeypatch):
    from bitnet_runtime.execution import runtime_resolver
    from bitnet_runtime.execution.runtime_resolver import ExecutionRuntimeResolver
    from bitnet_runtime.model_garden.catalog import ModelGarden
    from bitnet_runtime.router.models import RuntimeType, ExecutionTarget

    monkeypatch.setattr(runtime_resolver, "has_avx2", lambda: False)

    garden = ModelGarden()
    bitnet_manifest = garden.get("bitnet_b1_58_2b")
    assert bitnet_manifest is not None

    resolver = ExecutionRuntimeResolver()
    placement = await resolver.resolve_execution(bitnet_manifest, privacy=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY)
    assert placement.target != ExecutionTarget.LOCAL_CPU_NATIVE
    if placement.target == ExecutionTarget.LOCAL_CPU_CONTAINER:
        assert placement.runtime_type == RuntimeType.CONTAINER
    else:
        assert ("AVX2" in placement.why or "unsupported" in placement.reason or "offline" in placement.why)
