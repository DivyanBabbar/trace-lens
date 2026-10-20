from datetime import UTC, datetime, timedelta
from tracelens.analysis import analyze
from tracelens.models import IncidentRequest, SignalIn
from tracelens.storage import add_signals, initialize

def test_ranks_preceding_deployment_and_error_signals(tmp_path, monkeypatch):
    from tracelens import storage
    monkeypatch.setattr(storage.settings,"data_dir",str(tmp_path)); initialize()
    t=datetime.now(UTC)
    add_signals([
        SignalIn(timestamp=t,service="billing",kind="deployment",name="release",severity="warning",message="deployed"),
        SignalIn(timestamp=t+timedelta(minutes=1),service="billing",kind="log",name="DBTimeout",severity="critical",message="timeout"),
        SignalIn(timestamp=t+timedelta(minutes=2),service="checkout",kind="trace",name="failed call",severity="critical",message="upstream error"),
    ])
    report=analyze(IncidentRequest(started_at=t-timedelta(minutes=1),ended_at=t+timedelta(minutes=3)))
    assert report.hypotheses[0].service == "billing"
    assert "not proof" in report.disclaimer

def test_rejects_empty_or_inverted_window(tmp_path, monkeypatch):
    from tracelens import storage
    monkeypatch.setattr(storage.settings,"data_dir",str(tmp_path)); initialize()
    t=datetime.now(UTC)
    try: analyze(IncidentRequest(started_at=t,ended_at=t-timedelta(minutes=1)))
    except ValueError: pass
    else: raise AssertionError("inverted incident range must be rejected")
