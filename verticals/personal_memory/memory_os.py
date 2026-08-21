from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, List, Optional
from bitnet_runtime.logging import logger
from bitnet_runtime.memory.indexer import DocumentIndexer
from bitnet_runtime.plugins.vertical_registry import VerticalManifest
from ..base_vertical import BaseVertical
from .query_engine import PersonalMemoryQueryEngine
from .watcher import DirectoryWatcher

class PersonalMemoryOS(BaseVertical):
    manifest = VerticalManifest(
        name="memory",
        title="Personal Memory OS",
        description="Local Document & Activity Vector Recall",
    )
    """
    Personal Memory OS:
    - Continuous local document and memory indexing
    - Instant recall across notes, proposals, transcripts, and records
    - 1-Bit vector similarity search with citations
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.indexer = DocumentIndexer(self.semantic_memory)
        self.query_engine = PersonalMemoryQueryEngine(self.semantic_memory, self.inference_engine)
        watch_dirs = getattr(self.config.verticals.personal_memory, "watch_directories", None) or ["./documents"]
        self.watcher = DirectoryWatcher(
            directories=watch_dirs,
            on_new_file=self._handle_new_document,
        )

    async def initialize(self) -> None:
        logger.info("Personal Memory OS initialized.")
        await self.sync_watched_directories()

    async def _handle_new_document(self, path: Path) -> None:
        await self.indexer.index_file(path)

    async def sync_watched_directories(self) -> int:
        return await self.watcher.scan_once()

    async def ask(self, question: str) -> Dict[str, Any]:
        return await self.query_engine.answer_question(question)
