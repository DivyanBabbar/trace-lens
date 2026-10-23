from collections import defaultdict
from datetime import datetime
from uuid import uuid4
from tracelens.models import Evidence, Hypothesis, IncidentReport, IncidentRequest
from tracelens.storage import query_signals

SEVERITY_WEIGHT = {"info": 0.15, "warning": 0.55, "critical": 1.0}


# RCA is deterministic: temporal precedence, severity, error signals, and downstream breadth.
def analyze(request: IncidentRequest) -> IncidentReport:
    if request.ended_at <= request.started_at:
        raise ValueError("ended_at must be later than started_at")
    rows = query_signals(request.started_at.isoformat(), request.ended_at.isoformat(), request.service)
    if not rows:
        raise LookupError("No telemetry was found in the requested incident window.")
    events = [
        Evidence(
            signal_id=r["id"],
            timestamp=datetime.fromisoformat(r["timestamp"]),
            service=r["service"],
            kind=r["kind"],
            name=r["name"],
            severity=r["severity"],
            message=r["message"],
            relevance=0.0,
        )
        for r in rows
    ]
    first_failure = min((e.timestamp for e in events if _is_failure(e)), default=request.started_at)
    services: dict[str, list[Evidence]] = defaultdict(list)
    for e in events:
        services[e.service].append(e)
    ranked = []
    all_services = set(services)
    for service, signals in services.items():
        before = [s for s in signals if s.timestamp <= first_failure]
        errors = sum(_is_failure(s) for s in signals)
        deploys = sum(s.kind == "deployment" for s in signals)
        critical = sum(s.severity == "critical" for s in signals)
        # Downstream blast radius: services observed after this service's first anomaly.
        first_anomaly = min(
            (s.timestamp for s in signals if _is_failure(s) or s.kind == "deployment"), default=request.ended_at
        )
        breadth = sum(
            1
            for other, group in services.items()
            if other != service and any(s.timestamp >= first_anomaly and _is_failure(s) for s in group)
        )
        score = min(
            1.0,
            0.20
            + min(0.25, len(before) * 0.03)
            + min(0.30, errors * 0.08)
            + min(0.15, deploys * 0.12)
            + min(0.10, critical * 0.05)
            + min(0.15, breadth * 0.05),
        )
        evidence = sorted(
            signals, key=lambda s: (s.timestamp > first_failure, -SEVERITY_WEIGHT[s.severity], s.timestamp)
        )[:8]
        evidence = [
            e.model_copy(update={"relevance": round(max(0.1, score - (0.15 if e.timestamp > first_failure else 0)), 2)})
            for e in evidence
        ]
        if errors or deploys or critical:
            title = (
                "Recent deployment preceded service errors"
                if deploys and errors
                else "Recent deployment occurred in the incident window"
                if deploys
                else "Service errors coincide with incident onset"
            )
            checks = [
                "Compare this service's error rate with its pre-incident baseline",
                "Inspect recent deploy and configuration changes",
                "Follow trace IDs across upstream and downstream calls",
            ]
            ranked.append(
                Hypothesis(
                    rank=0,
                    service=service,
                    title=title,
                    confidence=round(score, 2),
                    score=round(score, 3),
                    evidence=evidence,
                    suggested_checks=checks,
                )
            )
    ranked.sort(key=lambda h: (-h.score, h.service))
    ranked = [h.model_copy(update={"rank": i + 1}) for i, h in enumerate(ranked[:5])]
    impact = f"Analyzed {len(events)} signals across {len(all_services)} services; {sum(_is_failure(e) for e in events)} failure-like signals occurred in the requested window."
    timeline = sorted(events, key=lambda e: (e.timestamp, e.service))
    return IncidentReport(
        incident_id=str(uuid4()),
        started_at=request.started_at,
        ended_at=request.ended_at,
        impact_summary=impact,
        hypotheses=ranked,
        timeline=timeline,
        disclaimer="Ranked hypotheses are evidence-based leads, not proof of causality. Verify with service owners and production telemetry.",
    )


def _is_failure(signal: Evidence) -> bool:
    text = f"{signal.name} {signal.message}".lower()
    return signal.severity == "critical" or any(
        term in text for term in ("error", "failed", "timeout", "exception", "5xx", "unavailable", "latency")
    )
