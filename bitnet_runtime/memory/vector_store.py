from __future__ import annotations
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np
from ..logging import logger
from .db import DatabaseManager

@dataclass
class VectorSearchResult:
    id: str
    doc_id: str
    text_content: str
    score: float
    metadata: Dict[str, Any]

class VectorStore:
    """
    Pure-local high performance vector search store using SQLite persistence
    and vectorized cosine similarity.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def add_chunk(
        self,
        chunk_id: str,
        doc_id: str,
        chunk_index: int,
        text_content: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO vector_chunks (id, doc_id, chunk_index, text_content, vector_json, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    chunk_id,
                    doc_id,
                    chunk_index,
                    text_content,
                    json.dumps(vector),
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        threshold: float = 0.0,
        filter_doc_id: Optional[str] = None,
    ) -> List[VectorSearchResult]:
        q_vec = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm < 1e-6:
            return []

        rows = self.db.fetchall("SELECT id, doc_id, text_content, vector_json, metadata FROM vector_chunks")
        if not rows:
            return []

        results: List[VectorSearchResult] = []
        for r in rows:
            if filter_doc_id and r["doc_id"] != filter_doc_id:
                continue

            v = np.array(json.loads(r["vector_json"]), dtype=np.float32)
            v_norm = np.linalg.norm(v)
            if v_norm < 1e-6:
                score = 0.0
            else:
                score = float(np.dot(q_vec, v) / (q_norm * v_norm))

            if score >= threshold:
                results.append(
                    VectorSearchResult(
                        id=r["id"],
                        doc_id=r["doc_id"],
                        text_content=r["text_content"],
                        score=round(score, 4),
                        metadata=json.loads(r["metadata"]) if r["metadata"] else {},
                    )
                )

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def delete_by_doc_id(self, doc_id: str) -> None:
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM vector_chunks WHERE doc_id = ?", (doc_id,))
            conn.commit()
