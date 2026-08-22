import pytest
from bitnet_runtime.execution import (
    BackendStatus,
    BackendType,
    ExecutionRegistry,
    LoadedModelInstance,
    ModelNotLoadedError,
    execution_registry,
)
from bitnet_runtime.model_garden import ModelGarden, ModelStatus

@pytest.mark.asyncio
async def test_execution_registry_health_and_backends():
    registry = ExecutionRegistry()
    health = await registry.get_all_health()
    assert "llamacpp" in health
    assert "tei" in health
    assert "bitnet_sidecar" in health
    assert "mock" in health
    assert health["mock"].status == BackendStatus.ONLINE

@pytest.mark.asyncio
async def test_model_loading_and_unloading():
    garden = ModelGarden()
    registry = ExecutionRegistry()
    manifest = garden.get("qwen2.5_1.5b_instruct")
    assert manifest is not None

    # 1. Initially not loaded
    assert not registry.is_model_loaded(manifest.model_id)

    # 2. Load model
    instance = await registry.load_model(manifest)
    assert isinstance(instance, LoadedModelInstance)
    assert registry.is_model_loaded(manifest.model_id)
    assert registry.get_total_ram_used_mb() > 0

    # 3. Complete prompt
    resp = await registry.complete(manifest, prompt="What is 2+2?", auto_load=False)
    assert resp is not None
    assert len(resp.text) > 0

    # 4. Unload model
    unloaded = await registry.unload_model(manifest.model_id)
    assert unloaded is True
    assert not registry.is_model_loaded(manifest.model_id)

    # 5. Error when auto_load=False and not loaded
    with pytest.raises(ModelNotLoadedError):
        await registry.complete(manifest, prompt="Hello", auto_load=False)

@pytest.mark.asyncio
async def test_embedding_and_reranking_execution():
    garden = ModelGarden()
    registry = ExecutionRegistry()
    manifest = garden.get("bge_small_en_v1.5")
    assert manifest is not None

    # Embed batch
    responses = await registry.embed(
        manifest,
        texts=["Machine learning algorithms", "Deep neural networks"],
        auto_load=True,
    )
    assert len(responses) == 2
    assert responses[0].dim == 384
    assert len(responses[0].vector) == 384

    # Rerank
    rerank_res = await registry.rerank(
        manifest,
        query="Artificial Intelligence",
        documents=["Machine learning models", "A recipe for chocolate cake"],
        auto_load=True,
    )
    assert len(rerank_res.results) == 2
    assert rerank_res.results[0].score >= rerank_res.results[1].score
