from __future__ import annotations
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..logging import logger
from .semantic_memory import SemanticMemory

SUPPORTED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".py", ".html"}

class DocumentIndexer:
    """
    Scans directories, parses text files, and registers chunks into SemanticMemory.
    """

    def __init__(self, semantic_memory: SemanticMemory):
        self.semantic_memory = semantic_memory

    async def index_file(self, file_path: str | Path, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        p = Path(file_path)
        if not p.exists() or not p.is_file():
            logger.warning(f"File not found: {file_path}")
            return None

        if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
            logger.debug(f"Skipping unsupported file extension: {p.suffix}")
            return None

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            doc_id = await self.semantic_memory.ingest_text(
                text=content,
                source_path=str(p.resolve()),
                title=p.name,
                metadata={"filename": p.name, "file_extension": p.suffix, **(metadata or {})},
            )
            logger.info(f"Indexed document: {p.name} (ID: {doc_id[:8]})")
            return doc_id
        except Exception as e:
            logger.error(f"Failed to index file {file_path}: {e}")
            return None

    async def index_directory(
        self,
        dir_path: str | Path,
        recursive: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        p = Path(dir_path)
        if not p.exists() or not p.is_dir():
            return []

        doc_ids: List[str] = []
        pattern = "**/*" if recursive else "*"
        for item in p.glob(pattern):
            if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
                res = await self.index_file(item, metadata)
                if res:
                    doc_ids.append(res)

        return doc_ids
