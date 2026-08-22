import pytest
from fastapi.testclient import TestClient
from bitnet_runtime.server.app import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_garden_models_endpoint(client):
    res = client.get("/api/v1/garden/models")
    assert res.status_code == 200
    models = res.json()
    assert len(models) >= 5
    model_ids = {m["model_id"] for m in models}
    assert "bitnet_b1_58_2b" in model_ids
    assert "qwen2.5_1.5b_instruct" in model_ids

def test_garden_hardware_and_storage_endpoints(client):
    res_hw = client.get("/api/v1/garden/hardware")
    assert res_hw.status_code == 200
    hw = res_hw.json()
    assert "total_ram_mb" in hw
    assert "logical_cores" in hw

    res_st = client.get("/api/v1/garden/storage")
    assert res_st.status_code == 200
    st = res_st.json()
    assert "total_models_count" in st

def test_router_policies_and_telemetry_endpoints(client):
    res_pol = client.get("/api/v1/router/policies")
    assert res_pol.status_code == 200
    assert "privacy_policy" in res_pol.json()

    res_tel = client.get("/api/v1/router/telemetry")
    assert res_tel.status_code == 200
    assert "total_routed_tasks" in res_tel.json()

def test_dashboard_route(client):
    res = client.get("/dashboard")
    assert res.status_code == 200
    assert "BitNet AI Runtime" in res.text
