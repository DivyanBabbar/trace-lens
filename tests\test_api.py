from fastapi.testclient import TestClient
from tracelens import storage
from tracelens.api import app

def test_demo_ingestion_and_incident_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "data_dir", str(tmp_path))
    with TestClient(app) as client:
        demo = client.post("/v1/demo/load")
        assert demo.status_code == 200
        window = demo.json()
        response = client.post("/v1/incidents/analyze", json={"started_at":window["started_at"],"ended_at":window["ended_at"]})
        assert response.status_code == 200
        assert response.json()["hypotheses"][0]["service"] == "payments-api"
