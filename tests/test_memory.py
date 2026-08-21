import pytest
from pathlib import Path
from bitnet_runtime.inference.embeddings import BitNetEmbeddingEngine
from bitnet_runtime.memory.db import DatabaseManager
from bitnet_runtime.memory.episodic_memory import EpisodicMemory
from bitnet_runtime.memory.indexer import DocumentIndexer
from bitnet_runtime.memory.semantic_memory import SemanticMemory
from bitnet_runtime.memory.vector_store import VectorStore

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_memory.db"
    return DatabaseManager(db_file)

def test_database_manager(temp_db):
    temp_db.execute("INSERT INTO kv_store (key, value) VALUES (?, ?)", ("test_key", '{"status": "ok"}'))
    row = temp_db.fetchone("SELECT * FROM kv_store WHERE key = ?", ("test_key",))
    assert row is not None
    assert row["key"] == "test_key"

def test_vector_store(temp_db):
    vstore = VectorStore(temp_db)
    vstore.add_chunk(
        chunk_id="chunk_1",
        doc_id="doc_1",
        chunk_index=0,
        text_content="BitNet 1.58-bit large language model execution",
        vector=[1.0, 0.0, 0.0, 0.0],
        metadata={"title": "BitNet Overview"},
    )
    vstore.add_chunk(
        chunk_id="chunk_2",
        doc_id="doc_2",
        chunk_index=0,
        text_content="Cooking recipe for Italian pasta",
        vector=[0.0, 1.0, 0.0, 0.0],
        metadata={"title": "Cooking Guide"},
    )

    results = vstore.search(query_vector=[0.9, 0.1, 0.0, 0.0], top_k=1)
    assert len(results) == 1
    assert results[0].id == "chunk_1"
    assert results[0].score > 0.8

def test_episodic_memory(temp_db):
    episodic = EpisodicMemory(temp_db)
    session_id = episodic.create_session(title="Unit Test Session")
    assert len(session_id) > 0

    episodic.log_event(session_id, 1, "thought", "Need to execute tool")
    episodic.log_event(session_id, 2, "tool_call", "run_shell('ls')")
    episodic.log_event(session_id, 3, "final_answer", "Files listed")

    history = episodic.get_session_history(session_id)
    assert len(history) == 3
    assert history[0].event_type == "thought"
    assert history[2].content == "Files listed"

@pytest.mark.asyncio
async def test_semantic_memory_and_indexer(temp_db, tmp_path):
    emb_engine = BitNetEmbeddingEngine(dim=32)
    semantic_mem = SemanticMemory(temp_db, emb_engine)
    indexer = DocumentIndexer(semantic_mem)

    sample_file = tmp_path / "sample_proposal.txt"
    sample_file.write_text("Acme Corp agrees to deliver edge runtime software within 4 weeks.", encoding="utf-8")

    doc_id = await indexer.index_file(sample_file)
    assert doc_id is not None

    search_res = await semantic_mem.query("edge runtime software delivery", top_k=1)
    assert len(search_res) == 1
    assert "Acme Corp" in search_res[0].text_content
