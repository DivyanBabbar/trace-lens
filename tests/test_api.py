from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from tracelens import analysis, storage
from tracelens.api import app
from tracelens.models import IncidentRequest


def test_demo_ingestion_and_incident_analysis(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "data_dir", str(tmp_path))
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert "Find the first" in page.text
        assert client.get("/static/app.js").status_code == 200

        demo = client.post("/v1/demo/load")
        assert demo.status_code == 200
        window = demo.json()
        response = client.post(
            "/v1/incidents/analyze", json={"started_at": window["started_at"], "ended_at": window["ended_at"]}
        )
        assert response.status_code == 200
        assert response.json()["hypotheses"][0]["service"] == "payments-api"


def test_signal_batch_rejects_empty_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "data_dir", str(tmp_path))
    with TestClient(app) as client:
        assert client.post("/v1/signals/batch", json=[]).status_code == 422


def test_signal_batch_rejects_non_finite_values(tmp_path, monkeypatch):
    monkeypatch.setattr(storage.settings, "data_dir", str(tmp_path))
    with TestClient(app) as client:
        response = client.post(
            "/v1/signals/batch",
            content=(
                '[{"timestamp":"2026-10-23T10:00:00Z","service":"payments-api",'
                '"kind":"metric","name":"http_5xx_rate","value":Infinity}]'
            ),
            headers={"content-type": "application/json"},
        )

    assert response.status_code == 422


def test_deployment_without_failures_is_not_described_as_preceding_errors(monkeypatch):
    started_at = datetime(2026, 10, 23, 10, tzinfo=UTC)
    deployment_at = started_at + timedelta(minutes=1)
    monkeypatch.setattr(
        analysis,
        "query_signals",
        lambda *_args: [
            {
                "id": 1,
                "timestamp": deployment_at.isoformat(),
                "service": "payments-api",
                "kind": "deployment",
                "name": "release-v2.4.1",
                "severity": "warning",
                "message": "Release completed",
            }
        ],
    )

    report = analysis.analyze(IncidentRequest(started_at=started_at, ended_at=started_at + timedelta(minutes=10)))

    assert report.hypotheses[0].title == "Recent deployment occurred in the incident window"
