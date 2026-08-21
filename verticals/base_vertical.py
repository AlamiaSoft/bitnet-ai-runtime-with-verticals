from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from bitnet_runtime.config import AppConfig, config
from bitnet_runtime.inference.base import InferenceEngine
from bitnet_runtime.inference.model_manager import ModelManager
from bitnet_runtime.memory.db import DatabaseManager
from bitnet_runtime.memory.episodic_memory import EpisodicMemory
from bitnet_runtime.memory.semantic_memory import SemanticMemory
from bitnet_runtime.tools.registry import ToolRegistry

from bitnet_runtime.plugins.vertical_registry import VerticalManifest, VerticalPluginContract

class BaseVertical(VerticalPluginContract, ABC):
    """Abstract base class for all business vertical applications."""

    manifest: VerticalManifest = VerticalManifest(name="base", title="Base Vertical")

    def __init__(self, cfg: Optional[AppConfig] = None):
        self.config = cfg or config
        self.db = DatabaseManager(self.config.memory.db_path)
        self.model_mgr = ModelManager(self.config.inference)
        self.inference_engine: InferenceEngine = self.model_mgr.get_inference_engine()
        self.embedding_engine = self.model_mgr.get_embedding_engine(self.config.memory.vector_dim)
        self.episodic_memory = EpisodicMemory(self.db)
        self.semantic_memory = SemanticMemory(self.db, self.embedding_engine)
        self.tool_registry = ToolRegistry()
        self._setup_tools()

    def _setup_tools(self) -> None:
        pass

    @abstractmethod
    async def initialize(self) -> None:
        pass

    def get_cli_handlers(self) -> Dict[str, Any]:
        return {}
