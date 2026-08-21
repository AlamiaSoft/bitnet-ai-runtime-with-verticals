from __future__ import annotations
import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from ..inference.base import EmbeddingEngine
from .db import DatabaseManager
from .vector_store import VectorSearchResult, VectorStore

@dataclass
class DocumentChunk:
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    metadata: Dict[str, Any]

class SemanticMemory:
    """
    High-level interface for ingesting documents, querying knowledge,
    and performing local vector similarity recall.
    """

    def __init__(self, db_manager: DatabaseManager, embedding_engine: EmbeddingEngine):
        self.db = db_manager
        self.embedding_engine = embedding_engine
        self.vector_store = VectorStore(db_manager)

    async def ingest_text(
        self,
        text: str,
        source_path: str,
        title: Optional[str] = None,
        chunk_size: int = 400,
        chunk_overlap: int = 40,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        doc_id = str(uuid.uuid4())
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        # Save document record
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO documents (id, source_path, title, content_hash, file_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (doc_id, source_path, title or source_path, content_hash, "text", json.dumps(metadata or {})),
            )
            conn.commit()

        # Chunk text
        chunks: List[str] = []
        words = text.split()
        step = max(1, chunk_size - chunk_overlap)
        for i in range(0, len(words), step):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)

        if not chunks:
            chunks = [text]

        # Generate embeddings & save to vector store
        embeddings = await self.embedding_engine.embed_batch(chunks)
        for idx, (chunk_text, emb) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc_id}_{idx}"
            self.vector_store.add_chunk(
                chunk_id=chunk_id,
                doc_id=doc_id,
                chunk_index=idx,
                text_content=chunk_text,
                vector=emb.vector,
                metadata={"source_path": source_path, "title": title, **(metadata or {})},
            )

        return doc_id

    async def query(self, query_text: str, top_k: int = 3, threshold: float = 0.0) -> List[VectorSearchResult]:
        q_emb = await self.embedding_engine.embed_text(query_text)
        return self.vector_store.search(q_emb.vector, top_k=top_k, threshold=threshold)
