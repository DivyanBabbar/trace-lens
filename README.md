# TraceLens — Evidence-first Microservice Root Cause Analysis

TraceLens correlates deployment events, logs, metrics, traces, and alerts into ranked incident hypotheses. It focuses on a common SRE question: **what changed first, which services were affected next, and what evidence supports the lead?**

![CI](https://github.com/DivyanBabbar/trace-lens/actions/workflows/ci.yml/badge.svg)

## Highlights

- Ingest individual or batched telemetry through a typed FastAPI API
- Normalize heterogeneous events into an indexed SQLite event store
- Analyze an incident window across service boundaries
- Rank deterministic hypotheses using temporal precedence, error density, severity, deployments, and downstream blast radius
- Return an evidence timeline, confidence score, and concrete next checks
- Load an end-to-end synthetic incident instantly
- OpenAPI docs, Docker Compose, CLI, pytest, Ruff, and CodeQL

## Quick start

```bash
git clone https://github.com/DivyanBabbar/trace-lens.git
cd trace-lens
python -m venv .venv
# Activate the environment, then:
pip install -e '.[dev]'
tracelens serve
```

Open <http://127.0.0.1:8000/docs>, call `POST /v1/demo/load`, and use its `started_at` and `ended_at` fields in `POST /v1/incidents/analyze`. The demo inserts events relative to current UTC:

```bash
curl -X POST http://127.0.0.1:8000/v1/demo/load
```

Then submit a window covering the last 10 minutes to `POST /v1/incidents/analyze`. Or run `docker compose up --build` and use the same API at port 8000.

## Example API

```json
POST /v1/signals/batch
[
  {
    "timestamp": "2026-10-20T12:00:00Z",
    "service": "payments-api",
    "kind": "deployment",
    "name": "release-v2.4.1",
    "severity": "warning",
    "message": "New release deployed"
  },
  {
    "timestamp": "2026-10-20T12:02:00Z",
    "service": "payments-api",
    "kind": "log",
    "name": "DatabaseTimeout",
    "severity": "critical",
    "message": "Connection pool exhausted",
    "trace_id": "trace-123"
  }
]
```

```json
POST /v1/incidents/analyze
{
  "started_at": "2026-10-20T11:55:00Z",
  "ended_at": "2026-10-20T12:15:00Z"
}
```

Routes: `POST /v1/signals`, `POST /v1/signals/batch`, `POST /v1/demo/load`, `POST /v1/incidents/analyze`, `GET /health`.

## How ranking works

The RCA core is deterministic and auditable. It scores services using signals observed before the first failure, failure-like events, deployment proximity, critical severity, and other services failing afterward. Each returned hypothesis contains the events used as evidence. A score is a prioritization aid, not a calibrated probability or proof of causality.

The MVP intentionally avoids asking a language model to decide what broke. A future narrative layer can explain the ranked evidence while preserving links to source signals and clearly marking uncertainty.

## Data model and integrations

`kind` accepts `metric`, `log`, `trace`, `deployment`, and `alert`. Send normalized events from an OpenTelemetry Collector or a lightweight adapter. The service currently accepts JSON over HTTP and stores records in SQLite; production deployments should use an authenticated ingestion gateway, durable queue, retention policy, and a managed database.

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `TRACELENS_DATA_DIR` | `data` | SQLite database directory |
| `TRACELENS_INCIDENT_WINDOW_MINUTES` | `15` | Default window for future integrations |

## Development

```bash
pip install -e '.[dev]'
ruff check .
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [CHANGELOG.md](CHANGELOG.md). MIT licensed.
