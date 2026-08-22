import pytest
from bitnet_runtime.model_garden import (
    HardwareRequirements,
    ModelFamily,
    ModelGarden,
    ModelManifest,
    ModelModality,
)
from bitnet_runtime.router import (
    ModelCapabilityRegistry,
    ModelTier,
    PrivacyRequirement,
    RoutingPolicyEngine,
    TaskRequirements,
    TaskType,
)

def test_model_garden_modality_separation():
    garden = ModelGarden()
    generative = garden.list_generative_slms()
    embeddings = garden.list_embedding_models()
    rerankers = garden.list_by_modality(ModelModality.RERANKER)

    assert len(generative) >= 4
    assert len(embeddings) >= 3
    assert len(rerankers) >= 1

    # Ensure embedding models are not mixed into generative SLMs
    embedding_ids = {m.model_id for m in embeddings}
    for gen in generative:
        assert gen.model_id not in embedding_ids

def test_granular_task_benchmark_ratings():
    garden = ModelGarden()
    qwen = garden.get("qwen2.5_1.5b_instruct")
    phi = garden.get("phi3.5_mini_3.8b")
    bitnet = garden.get("bitnet_b1_58_2b")

    assert qwen is not None
    assert phi is not None
    assert bitnet is not None

    # Qwen specializes in extraction
    assert qwen.get_task_rating(TaskType.EXTRACTION) > qwen.get_task_rating(TaskType.REASONING)
    # Phi specializes in complex reasoning
    assert phi.get_task_rating(TaskType.REASONING) > phi.get_task_rating(TaskType.EXTRACTION)
    # BitNet is 1-bit ternary CPU optimized
    assert bitnet.hardware.quantization == "1bit_ternary"
    assert bitnet.get_task_rating(TaskType.CLASSIFICATION) >= 4.5

def test_router_selects_specialized_model_per_task():
    garden = ModelGarden()
    registry = ModelCapabilityRegistry(garden=garden)
    policy = RoutingPolicyEngine(registry)

    # 1. Extraction task should pick Qwen 1.5B (4.8 rating)
    req_extract = TaskRequirements(
        task_type=TaskType.EXTRACTION,
        privacy=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY,
    )
    decision_extract = policy.evaluate_route(req_extract)
    assert decision_extract.primary_model.model_id == "qwen2.5_1.5b_instruct"

    # 2. Complex reasoning task should pick Phi-3.5 Mini (4.6 rating)
    req_reason = TaskRequirements(
        task_type=TaskType.REASONING,
        privacy=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY,
    )
    decision_reason = policy.evaluate_route(req_reason)
    assert decision_reason.primary_model.model_id == "phi3.5_mini_3.8b"

    # 3. High-volume classification with 1-bit preferred tier
    req_classify = TaskRequirements(
        task_type=TaskType.CLASSIFICATION,
        preferred_tier=ModelTier.LOCAL_1BIT,
        privacy=PrivacyRequirement.AIRGAPPED_LOCAL_ONLY,
    )
    decision_classify = policy.evaluate_route(req_classify)
    assert decision_classify.primary_model.model_id == "bitnet_b1_58_2b"

def test_dynamic_custom_manifest_registration():
    garden = ModelGarden()
    custom_manifest = ModelManifest(
        model_id="custom_specialist_slm",
        name="Custom Specialist SLM",
        family=ModelFamily.CUSTOM,
        modality=ModelModality.GENERATIVE_TEXT,
        tier=ModelTier.LOCAL_DENSE,
        hardware=HardwareRequirements(min_ram_mb=800),
        task_ratings={TaskType.CODING: 5.0},
    )
    garden.register_manifest(custom_manifest)

    registry = ModelCapabilityRegistry(garden=garden)
    profile = registry.get("custom_specialist_slm")
    assert profile is not None
    assert profile.task_ratings[TaskType.CODING] == 5.0
