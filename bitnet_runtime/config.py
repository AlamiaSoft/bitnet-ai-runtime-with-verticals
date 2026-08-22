from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Automatically load .env file from working directory or project root
load_dotenv()

class RuntimeSettings(BaseModel):
    name: str = Field(default_factory=lambda: os.getenv("ALAMIA_RUNTIME_NAME", os.getenv("BITNET_RUNTIME_NAME", "Alamia Local AI Runtime")))
    environment: str = Field(default_factory=lambda: os.getenv("BITNET_ENV", os.getenv("ENVIRONMENT", "development")))
    data_dir: Path = Field(default_factory=lambda: Path(os.getenv("BITNET_DATA_DIR", "./data")))
    log_level: str = Field(default_factory=lambda: os.getenv("BITNET_LOG_LEVEL", "INFO"))

class ServerSettings(BaseModel):
    host: str = Field(default_factory=lambda: os.getenv("BITNET_HOST", os.getenv("HOST", "127.0.0.1")))
    port: int = Field(default_factory=lambda: int(os.getenv("BITNET_PORT", os.getenv("PORT", "8000"))))
    enable_docs: bool = Field(default_factory=lambda: os.getenv("BITNET_ENABLE_DOCS", "true").lower() in ("true", "1"))

class InferenceSettings(BaseModel):
    default_provider: str = Field(
        default_factory=lambda: os.getenv("BITNET_DEFAULT_PROVIDER", os.getenv("DEFAULT_PROVIDER", "bitnet"))
    )  # "bitnet", "llamacpp", "local_endpoint", "mock"
    bitnet_server_url: str = Field(
        default_factory=lambda: os.getenv("BITNET_SERVER_URL", "http://127.0.0.1:8080/v1")
    )
    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("BITNET_API_KEY", None)
    )
    model_name: str = Field(
        default_factory=lambda: os.getenv("BITNET_MODEL_NAME", "/models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf")
    )
    model_path: Optional[str] = Field(
        default_factory=lambda: os.getenv("BITNET_MODEL_PATH", "./models/bitnet_b1_58-3B.gguf")
    )
    temperature: float = Field(
        default_factory=lambda: float(os.getenv("BITNET_TEMPERATURE", "0.2"))
    )
    max_tokens: int = Field(
        default_factory=lambda: int(os.getenv("BITNET_MAX_TOKENS", "1024"))
    )
    context_window: int = Field(
        default_factory=lambda: int(os.getenv("BITNET_CONTEXT_WINDOW", "4096"))
    )
    threads: int = Field(
        default_factory=lambda: int(os.getenv("BITNET_THREADS", "4"))
    )
    local_endpoint_url: str = Field(
        default_factory=lambda: os.getenv("BITNET_LOCAL_ENDPOINT_URL", "http://127.0.0.1:11434/v1")
    )
    api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("BITNET_API_KEY")
    )

class MemorySettings(BaseModel):
    db_path: Path = Field(
        default_factory=lambda: Path(os.getenv("BITNET_DB_PATH", "./data/memory.db"))
    )
    vector_dim: int = Field(
        default_factory=lambda: int(os.getenv("BITNET_VECTOR_DIM", "128"))
    )
    chunk_size: int = Field(
        default_factory=lambda: int(os.getenv("BITNET_CHUNK_SIZE", "500"))
    )
    chunk_overlap: int = Field(
        default_factory=lambda: int(os.getenv("BITNET_CHUNK_OVERLAP", "50"))
    )
    similarity_threshold: float = Field(
        default_factory=lambda: float(os.getenv("BITNET_SIMILARITY_THRESHOLD", "0.0"))
    )

class AgentSettings(BaseModel):
    max_iterations: int = Field(
        default_factory=lambda: int(os.getenv("BITNET_MAX_ITERATIONS", "10"))
    )
    timeout_seconds: int = Field(
        default_factory=lambda: int(os.getenv("BITNET_TIMEOUT_SECONDS", "120"))
    )
    enable_shell: bool = Field(
        default_factory=lambda: os.getenv("BITNET_ENABLE_SHELL", "true").lower() in ("true", "1")
    )
    enable_browser: bool = Field(
        default_factory=lambda: os.getenv("BITNET_ENABLE_BROWSER", "true").lower() in ("true", "1")
    )
    enable_cron: bool = Field(
        default_factory=lambda: os.getenv("BITNET_ENABLE_CRON", "true").lower() in ("true", "1")
    )
    working_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("BITNET_WORKING_DIR", "./workspace"))
    )

class DynamicConfigNode:
    def __init__(self, data: Optional[Dict[str, Any]] = None):
        object.__setattr__(self, "_data", data if data is not None else {})

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            return super().__getattribute__(name)
        val = self._data.get(name)
        if isinstance(val, dict):
            return DynamicConfigNode(val)
        return val

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            self._data[name] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

class VerticalsConfig(BaseModel):
    """Extensible configuration container for dynamically registered vertical plugins."""
    model_config = {"extra": "allow"}

    def __init__(self, **data):
        super().__init__(**data)
        object.__setattr__(self, "_nodes", {})

    def __getattr__(self, item: str) -> Any:
        if item.startswith("_"):
            return super().__getattribute__(item)
        try:
            nodes = object.__getattribute__(self, "_nodes")
        except AttributeError:
            nodes = {}
            object.__setattr__(self, "_nodes", nodes)

        if item not in nodes:
            extra = self.__pydantic_extra__ or {}
            val = extra.get(item)
            d = val if isinstance(val, dict) else {}
            nodes[item] = DynamicConfigNode(d)
            if self.__pydantic_extra__ is not None:
                self.__pydantic_extra__[item] = d
        return nodes[item]

    def get(self, key: str, default: Any = None) -> Any:
        extra = self.__pydantic_extra__ or {}
        return extra.get(key, default)

class AppConfig(BaseSettings):
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    inference: InferenceSettings = Field(default_factory=InferenceSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)
    verticals: VerticalsConfig = Field(default_factory=VerticalsConfig)

    @classmethod
    def load_from_yaml(cls, path: str | Path = "config.example.yaml") -> AppConfig:
        file_path = Path(path)
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            return cls(**data)
        return cls()

config = AppConfig()
