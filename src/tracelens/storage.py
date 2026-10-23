import json
import sqlite3
from contextlib import closing
from pathlib import Path
from tracelens.config import settings
from tracelens.models import SignalIn


def connect() -> sqlite3.Connection:
    root = Path(settings.data_dir)
    root.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(root / "tracelens.db", timeout=10)
    db.row_factory = sqlite3.Row
    return db


def initialize() -> None:
    with closing(connect()) as db, db:
        db.execute("""CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, service TEXT NOT NULL,
            kind TEXT NOT NULL, name TEXT NOT NULL, value REAL, severity TEXT NOT NULL,
            trace_id TEXT, operation TEXT, message TEXT NOT NULL, attributes TEXT NOT NULL)""")
        db.execute("CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(timestamp)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_signals_service ON signals(service, timestamp)")


def add_signals(signals: list[SignalIn]) -> int:
    with closing(connect()) as db, db:
        cursor = db.executemany(
            """INSERT INTO signals(timestamp,service,kind,name,value,severity,trace_id,operation,message,attributes)
            VALUES(?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    s.timestamp.isoformat(),
                    s.service,
                    s.kind,
                    s.name,
                    s.value,
                    s.severity,
                    s.trace_id,
                    s.operation,
                    s.message,
                    json.dumps(s.attributes),
                )
                for s in signals
            ],
        )
        return cursor.rowcount


def query_signals(start: str, end: str, service: str | None = None) -> list[sqlite3.Row]:
    sql = "SELECT * FROM signals WHERE timestamp >= ? AND timestamp <= ?"
    params: list[object] = [start, end]
    if service:
        sql += " AND service = ?"
        params.append(service)
    sql += " ORDER BY timestamp ASC"
    with closing(connect()) as db, db:
        return db.execute(sql, params).fetchall()


def count_signals() -> int:
    with closing(connect()) as db, db:
        return db.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
