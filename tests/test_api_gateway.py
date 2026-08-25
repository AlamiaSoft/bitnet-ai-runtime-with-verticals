import pytest
from fastapi.testclient import TestClient
from bitnet_runtime.server.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_v1_health(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "runtime_mode" in data
    assert "backends" in data
    assert "active_models" in data
    assert response.headers.get("X-Request-ID") is not None
    assert response.headers.get("X-Response-Time-Ms") is not None

def test_v1_capabilities(client):
    response = client.get("/v1/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "capabilities" in data
    assert len(data["capabilities"]) >= 5
    task_types = [c["task_type"] for c in data["capabilities"]]
    assert "extraction" in task_types
    assert "classification" in task_types
    assert "dialogue" in task_types
    assert "reasoning" in task_types

def test_v1_inference_capability(client):
    payload = {
        "prompt": "What is the capital of France?",
        "task": "reasoning",
        "requirements": {
            "privacy": "airgapped_local_only",
            "latency": "balanced",
            "min_quality": 2.0
        }
    }
    response = client.post("/v1/inference", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "text" in data
    assert len(data["text"]) > 0
    assert "metadata" in data
    assert "request_id" in data["metadata"]
    assert "latency_ms" in data["metadata"]
    assert "endpoint" in data["metadata"]

def test_v1_chat(client):
    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "task": "dialogue"
    }
    response = client.post("/v1/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"]["role"] == "assistant"
    assert len(data["message"]["content"]) > 0
    assert "metadata" in data

def test_v1_chat_stream(client):
    payload = {
        "messages": [
            {"role": "user", "content": "Explain local AI in one sentence."}
        ]
    }
    response = client.post("/v1/chat/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
    content = response.text
    assert "data:" in content

def test_v1_extract(client):
    payload = {
        "text": "Invoice #98231 from Acme Corp for $4,500.00 due on 2026-09-01.",
        "target_schema": {
            "type": "object",
            "properties": {
                "invoice_number": {"type": "string"},
                "vendor": {"type": "string"},
                "amount": {"type": "number"},
                "due_date": {"type": "string"}
            }
        },
        "instructions": "Extract invoice fields."
    }
    response = client.post("/v1/extract", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "metadata" in data

def test_v1_classify(client):
    payload = {
        "text": "The database cluster experienced an outage and transactions are failing.",
        "categories": ["Technical Issue", "Billing", "General Inquiry", "Feature Request"]
    }
    response = client.post("/v1/classify", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "top_category" in data
    assert "confidence_scores" in data
    assert "metadata" in data

def test_v1_embeddings(client):
    payload = {
        "input": ["Local first AI execution", "Vector search semantic index"]
    }
    response = client.post("/v1/embeddings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "embeddings" in data
    assert len(data["embeddings"]) == 2
    assert "dimension" in data
    assert "metadata" in data

def test_v1_rerank(client):
    payload = {
        "query": "How does local inference work?",
        "documents": [
            "Local inference executes models directly on host CPU using quantized weights.",
            "Cloud APIs send data over the public internet to third party servers.",
            "Weather in Seattle is rainy during winter months."
        ],
        "top_k": 2
    }
    response = client.post("/v1/rerank", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "ranked_documents" in data
    assert len(data["ranked_documents"]) == 2
    assert "metadata" in data
