from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from tracelens.analysis import analyze
from tracelens.models import IncidentReport, IncidentRequest, SignalIn
from tracelens.storage import add_signals, count_signals, initialize

ASSET_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize()
    yield


app = FastAPI(
    title="TraceLens",
    summary="Evidence-first root cause analysis for microservice incidents.",
    description=(
        "Ingest normalized telemetry and rank incident hypotheses with an evidence timeline and concrete next checks."
    ),
    version="1.0.0",
    license_info={"name": "MIT"},
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=ASSET_DIR / "static"), name="static")


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{key: error[key] for key in ("loc", "msg", "type")} for error in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(ASSET_DIR / "static" / "index.html")


@app.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "signals": count_signals()}


@app.post("/v1/signals", status_code=202)
def ingest(signal: SignalIn) -> dict[str, object]:
    return {"accepted": add_signals([signal])}


@app.post("/v1/signals/batch", status_code=202)
def ingest_batch(signals: list[SignalIn]) -> dict[str, object]:
    if not 1 <= len(signals) <= 1000:
        raise HTTPException(422, "Batch size must be between 1 and 1000.")
    return {"accepted": add_signals(signals)}


@app.post("/v1/incidents/analyze", response_model=IncidentReport)
def incident(request: IncidentRequest) -> IncidentReport:
    try:
        return analyze(request)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/v1/demo/load")
def load_demo() -> dict[str, object]:
    now = datetime.now(UTC).replace(second=0, microsecond=0)
    t = now - timedelta(minutes=10)
    signals = [
        SignalIn(
            timestamp=t,
            service="payments-api",
            kind="deployment",
            name="release-v2.4.1",
            severity="warning",
            message="New release deployed",
        ),
        SignalIn(
            timestamp=t + timedelta(minutes=2),
            service="payments-api",
            kind="metric",
            name="http_5xx_rate",
            value=0.18,
            severity="critical",
            message="5xx rate rose after deployment",
        ),
        SignalIn(
            timestamp=t + timedelta(minutes=3),
            service="payments-api",
            kind="log",
            name="DatabaseTimeout",
            severity="critical",
            message="Connection pool exhausted",
            trace_id="demo-001",
        ),
        SignalIn(
            timestamp=t + timedelta(minutes=4),
            service="checkout-api",
            kind="trace",
            name="payment_request_failed",
            severity="critical",
            message="Downstream payments-api returned 503",
            trace_id="demo-001",
        ),
        SignalIn(
            timestamp=t + timedelta(minutes=5),
            service="orders-api",
            kind="alert",
            name="checkout_latency_high",
            severity="warning",
            message="p95 latency above threshold",
        ),
        SignalIn(
            timestamp=t + timedelta(minutes=6),
            service="inventory-api",
            kind="metric",
            name="request_rate",
            value=72,
            severity="info",
            message="Normal request rate",
        ),
    ]
    return {
        "accepted": add_signals(signals),
        "started_at": t.isoformat(),
        "ended_at": (t + timedelta(minutes=8)).isoformat(),
    }
