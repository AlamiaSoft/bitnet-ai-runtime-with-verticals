import os
import pytest
from bitnet_runtime.config import AppConfig

def test_environment_variable_override(monkeypatch):
    monkeypatch.setenv("BITNET_DEFAULT_PROVIDER", "mock")
    monkeypatch.setenv("BITNET_SERVER_URL", "http://test-server:9999/v1")
    monkeypatch.setenv("BITNET_MODEL_NAME", "custom-test-model")
    monkeypatch.setenv("BITNET_PORT", "9000")
    monkeypatch.setenv("BITNET_VECTOR_DIM", "64")

    cfg = AppConfig()
    assert cfg.inference.default_provider == "mock"
    assert cfg.inference.bitnet_server_url == "http://test-server:9999/v1"
    assert cfg.inference.model_name == "custom-test-model"
    assert cfg.server.port == 9000
    assert cfg.memory.vector_dim == 64

def test_config_env_defaults():
    cfg = AppConfig()
    assert cfg.inference.default_provider in ("bitnet", "mock", "llamacpp", "local_endpoint")
    assert cfg.server.port > 0
    assert cfg.memory.vector_dim > 0
