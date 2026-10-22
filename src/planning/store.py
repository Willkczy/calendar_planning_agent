"""Local SQLite repository and process-safe per-plan mutation locks (POSIX)."""

from __future__ import annotations

import fcntl
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from src.domain.models import Plan


class ConflictError(ValueError):
    pass


class PlanStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_dir = self.path.parent / (self.path.name + ".locks")
        self.lock_dir.mkdir(exist_ok=True)
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, payload TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS revisions (
                    plan_id TEXT NOT NULL, revision INTEGER NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(plan_id, revision));
                CREATE TABLE IF NOT EXISTS writes (
                    plan_id TEXT NOT NULL, event_id TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(plan_id, event_id));
                CREATE TABLE IF NOT EXISTS mock_events (
                    calendar_id TEXT NOT NULL, event_id TEXT NOT NULL, payload TEXT NOT NULL,
                    PRIMARY KEY(calendar_id, event_id));
            """)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @contextmanager
    def lock(self, plan_id: str):
        name = hashlib.sha256(plan_id.encode()).hexdigest()
        with (self.lock_dir / name).open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ConflictError(
                    "This plan is being changed. Reload before trying again."
                ) from exc
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def save(self, plan: Plan):
        payload = plan.model_dump_json()
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO plans VALUES (?, ?, ?)",
                (plan.id, payload, plan.updated_at.isoformat()),
            )
            db.execute(
                "INSERT OR REPLACE INTO revisions VALUES (?, ?, ?)",
                (plan.id, plan.revision, payload),
            )

    def get(self, plan_id: str) -> Plan:
        with self.connect() as db:
            row = db.execute(
                "SELECT payload FROM plans WHERE id = ?", (plan_id,)
            ).fetchone()
        if row is None:
            raise KeyError(plan_id)
        return Plan.model_validate_json(row["payload"])

    def list(self) -> list[Plan]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM plans ORDER BY updated DESC LIMIT 50"
            ).fetchall()
        return [Plan.model_validate_json(row["payload"]) for row in rows]

    def write_records(self, plan_id: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM writes WHERE plan_id = ? ORDER BY rowid",
                (plan_id,),
            ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def save_write(self, plan_id: str, event_id: str, payload: dict):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO writes VALUES (?, ?, ?)",
                (plan_id, event_id, json.dumps(payload)),
            )

    def mock_events(self, calendar_id: str) -> list[dict]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT payload FROM mock_events WHERE calendar_id = ?", (calendar_id,)
            ).fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def insert_mock(self, calendar_id: str, event_id: str, payload: dict) -> dict:
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO mock_events VALUES (?, ?, ?)",
                (calendar_id, event_id, json.dumps(payload)),
            )
            row = db.execute(
                "SELECT payload FROM mock_events WHERE calendar_id=? AND event_id=?",
                (calendar_id, event_id),
            ).fetchone()
        return json.loads(row["payload"])
