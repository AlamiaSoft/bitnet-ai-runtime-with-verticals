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
    # Ensure mock engine profile is present
    router = AIRouter(registry=registry, cfg=cfg)
    return router

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
    assert trace.attempts[1]["success"] is True

def test_heuristic_task_inference(mock_router):
    req1 = mock_router.infer_task_requirements("Please classify this customer ticket priority")
    assert req1.task_type == TaskType.CLASSIFICATION

    req2 = mock_router.infer_task_requirements("Extract the json fields: name, email, phone")
    assert req2.task_type == TaskType.EXTRACTION

    req3 = mock_router.infer_task_requirements("def calculate_tax(revenue): return revenue * 0.15")
    assert req3.task_type == TaskType.CODING

    req4 = mock_router.infer_task_requirements("Generate a morning executive briefing digest")
    assert req4.task_type == TaskType.SUMMARIZATION
