from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
from ...config import config
from ...inference.model_manager import ModelManager
from ...memory.db import DatabaseManager
from ...memory.semantic_memory import SemanticMemory

router = APIRouter(prefix="/memory", tags=["Memory"])

class IngestTextRequest(BaseModel):
    text: str
    source_path: str
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SearchMemoryRequest(BaseModel):
    query: str
    top_k: int = 3
    threshold: float = 0.2

def get_semantic_memory():
    db = DatabaseManager(config.memory.db_path)
    model_mgr = ModelManager(config.inference)
    emb_engine = model_mgr.get_embedding_engine(config.memory.vector_dim)
    return SemanticMemory(db, emb_engine)

import time
from ..telemetry import telemetry_collector

@router.post("/ingest")
async def ingest_document(req: IngestTextRequest):
    start_time = time.time()
    mem = get_semantic_memory()
    doc_id = await mem.ingest_text(
        text=req.text,
        source_path=req.source_path,
        title=req.title,
        metadata=req.metadata,
    )
    latency_ms = round((time.time() - start_time) * 1000.0, 1)
    telemetry_collector.record_memory_event(
        action="ingest",
        detail=f"Ingested document '{req.title or req.source_path}' ({len(req.text)} chars)",
        result_count=1,
        latency_ms=latency_ms,
    )
    return {"status": "success", "doc_id": doc_id}

@router.post("/search")
async def search_memory(req: SearchMemoryRequest):
    start_time = time.time()
    mem = get_semantic_memory()
    results = await mem.query(req.query, top_k=req.top_k, threshold=req.threshold)
    latency_ms = round((time.time() - start_time) * 1000.0, 1)
    telemetry_collector.record_memory_event(
        action="search",
        detail=f"Semantic query: '{req.query}'",
        result_count=len(results),
        latency_ms=latency_ms,
    )
    return {
        "query": req.query,
        "results": [
            {
                "id": r.id,
                "doc_id": r.doc_id,
                "text_content": r.text_content,
                "score": r.score,
                "metadata": r.metadata,
            }
            for r in results
        ],
    }
