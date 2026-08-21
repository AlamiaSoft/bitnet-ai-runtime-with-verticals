import pytest
from fastapi.testclient import TestClient
from bitnet_runtime.server.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_server_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"

def test_memory_routes(client):
    ingest_payload = {
        "text": "BitNet CPU inference eliminates cloud API bills for local agents.",
        "source_path": "/test/notes.txt",
        "title": "BitNet Cost Advantages",
    }
    ingest_res = client.post("/api/v1/memory/ingest", json=ingest_payload)
    assert ingest_res.status_code == 200
    doc_id = ingest_res.json()["doc_id"]
    assert doc_id is not None

    search_payload = {"query": "cloud API bills", "top_k": 1}
    search_res = client.post("/api/v1/memory/search", json=search_payload)
    assert search_res.status_code == 200
    assert len(search_res.json()["results"]) > 0

def test_agent_run_route(client):
    run_payload = {"prompt": "Perform system check"}
    res = client.post("/api/v1/agents/run", json=run_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["final_answer"]) > 0

def test_webhook_routes(client):
    wa_payload = {"sender_id": "923000000000", "message": "Hello restaurant"}
    res = client.post("/api/v1/webhooks/whatsapp", json=wa_payload)
    assert res.status_code == 200
    assert res.json()["status"] == "received"
