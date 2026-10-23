from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class SignalIn(BaseModel):
    timestamp: datetime
    service: str = Field(min_length=1, max_length=120)
    kind: Literal["metric", "log", "trace", "deployment", "alert"]
    name: str = Field(min_length=1, max_length=180)
    value: float | None = Field(default=None, allow_inf_nan=False)
    severity: Literal["info", "warning", "critical"] = "info"
    trace_id: str | None = Field(default=None, max_length=128)
    operation: str | None = Field(default=None, max_length=200)
    message: str = Field(default="", max_length=3000)
    attributes: dict[str, str] = Field(default_factory=dict)


class IncidentRequest(BaseModel):
    started_at: datetime
    ended_at: datetime
    service: str | None = None


class Evidence(BaseModel):
    signal_id: int
    timestamp: datetime
    service: str
    kind: str
    name: str
    severity: str
    message: str
    relevance: float


class Hypothesis(BaseModel):
    rank: int
    service: str
    title: str
    confidence: float
    score: float
    evidence: list[Evidence]
    suggested_checks: list[str]


class IncidentReport(BaseModel):
    incident_id: str
    started_at: datetime
    ended_at: datetime
    impact_summary: str
    hypotheses: list[Hypothesis]
    timeline: list[Evidence]
    disclaimer: str
