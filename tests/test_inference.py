import pytest
from bitnet_runtime.config import InferenceSettings
from bitnet_runtime.inference.base import CompletionResponse, EmbeddingResponse
from bitnet_runtime.inference.bitnet_engine import BitNetEngine
from bitnet_runtime.inference.embeddings import BitNetEmbeddingEngine
from bitnet_runtime.inference.llamacpp_engine import LlamaCppEngine
from bitnet_runtime.inference.local_endpoint_engine import LocalEndpointEngine
from bitnet_runtime.inference.mock_engine import MockInferenceEngine
from bitnet_runtime.inference.model_manager import ModelManager

@pytest.mark.asyncio
async def test_mock_inference_engine():
    engine = MockInferenceEngine()
    resp = await engine.complete("Summarize this document for me")
    assert isinstance(resp, CompletionResponse)
    assert len(resp.text) > 0
    assert resp.usage.total_tokens > 0

@pytest.mark.asyncio
async def test_mock_pattern_response():
    engine = MockInferenceEngine()
    engine.register_pattern(r"calculate 2\+2", "Result is 4")
    resp = await engine.complete("Please calculate 2+2 now")
    assert resp.text == "Result is 4"

@pytest.mark.asyncio
async def test_bitnet_embedding_engine():
    emb_engine = BitNetEmbeddingEngine(dim=64, quantize_1bit=True)
    res = await emb_engine.embed_text("Local offline AI agent runtime")
    assert isinstance(res, EmbeddingResponse)
    assert res.dim == 64
    assert len(res.vector) == 64

    # Batch test
    batch_res = await emb_engine.embed_batch(["First doc", "Second doc"])
    assert len(batch_res) == 2
    assert len(batch_res[0].vector) == 64

@pytest.mark.asyncio
async def test_bitnet_engine_fallback():
    engine = BitNetEngine()
    resp = await engine.complete("Hello BitNet CPU runner")
    assert resp.model.startswith("bitnet")
    assert len(resp.text) > 0

@pytest.mark.asyncio
async def test_llamacpp_engine_fallback():
    engine = LlamaCppEngine()
    resp = await engine.complete("Test llama prompt")
    assert len(resp.text) > 0

@pytest.mark.asyncio
async def test_local_endpoint_engine_offline():
    engine = LocalEndpointEngine(endpoint_url="http://127.0.0.1:99999/v1", timeout=1.0)
    resp = await engine.complete("Hello Ollama")
    assert "[Local Endpoint Offline]" in resp.text

def test_model_manager_hardware_detection():
    settings = InferenceSettings(default_provider="mock")
    mgr = ModelManager(settings)
    hw = mgr.get_hardware_info()
    assert "cpu_count" in hw
    assert "architecture" in hw
    assert isinstance(mgr.get_inference_engine(), MockInferenceEngine)
