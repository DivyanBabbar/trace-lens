from datetime import UTC, datetime, timedelta
from fastapi import FastAPI, HTTPException
from tracelens.models import IncidentReport, IncidentRequest, SignalIn
from tracelens.storage import add_signals, count_signals, initialize
from tracelens.analysis import analyze

app = FastAPI(title="TraceLens RCA", version="1.0.0", description="Evidence-first microservice incident analysis.")
@app.on_event("startup")
def startup() -> None: initialize()
@app.get("/health")
def health() -> dict[str, object]: return {"status":"ok","signals":count_signals()}
@app.post("/v1/signals", status_code=202)
def ingest(signal: SignalIn) -> dict[str, object]: return {"accepted":add_signals([signal])}
@app.post("/v1/signals/batch", status_code=202)
def ingest_batch(signals: list[SignalIn]) -> dict[str, object]:
    if not 1 <= len(signals) <= 1000: raise HTTPException(422,"Batch size must be between 1 and 1000.")
    return {"accepted": add_signals(signals)}
@app.post("/v1/incidents/analyze", response_model=IncidentReport)
def incident(request: IncidentRequest) -> IncidentReport:
    try: return analyze(request)
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc
    except ValueError as exc: raise HTTPException(422,str(exc)) from exc
@app.post("/v1/demo/load")
def load_demo() -> dict[str,object]:
    now=datetime.now(UTC).replace(second=0,microsecond=0); t=now-timedelta(minutes=10)
    signals=[
      SignalIn(timestamp=t,service="payments-api",kind="deployment",name="release-v2.4.1",severity="warning",message="New release deployed"),
      SignalIn(timestamp=t+timedelta(minutes=2),service="payments-api",kind="metric",name="http_5xx_rate",value=.18,severity="critical",message="5xx rate rose after deployment"),
      SignalIn(timestamp=t+timedelta(minutes=3),service="payments-api",kind="log",name="DatabaseTimeout",severity="critical",message="Connection pool exhausted",trace_id="demo-001"),
      SignalIn(timestamp=t+timedelta(minutes=4),service="checkout-api",kind="trace",name="payment_request_failed",severity="critical",message="Downstream payments-api returned 503",trace_id="demo-001"),
      SignalIn(timestamp=t+timedelta(minutes=5),service="orders-api",kind="alert",name="checkout_latency_high",severity="warning",message="p95 latency above threshold"),
      SignalIn(timestamp=t+timedelta(minutes=6),service="inventory-api",kind="metric",name="request_rate",value=72,severity="info",message="Normal request rate"),
    ]
    return {"accepted": add_signals(signals), "started_at": t.isoformat(), "ended_at": (t + timedelta(minutes=8)).isoformat()}
@app.get("/",include_in_schema=False)
def home() -> dict[str,str]: return {"service":"TraceLens RCA API","docs":"/docs","demo":"POST /v1/demo/load"}
