"""SQLite-backed RunStore using the stdlib ``sqlite3`` module (no extra deps).

The database holds three tables: ``runs`` (one row per execution), ``steps``
(per-step records, cascade-deleted with the run), and ``checkpoints`` (used by
:mod:`neurocore.persistence.checkpoint_adapter` so flowengine's sync
suspend/resume shares the same file).
"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from neurocore.persistence.base import (
    RunRecord,
    RunStatus,
    RunStore,
    StepRecord,
    StepStatus,
)

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS runs (
    run_id              TEXT PRIMARY KEY,
    blueprint_name      TEXT NOT NULL,
    blueprint_version   TEXT NOT NULL,
    blueprint_path      TEXT,
    blueprint_snapshot  TEXT NOT NULL,
    flow_type           TEXT NOT NULL,
    status              TEXT NOT NULL,
    initial_data        TEXT NOT NULL,
    final_context       TEXT,
    error               TEXT,
    suspended_at_node   TEXT,
    suspension_reason   TEXT,
    checkpoint_id       TEXT,
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL,
    duration_ms         REAL
);
CREATE INDEX IF NOT EXISTS idx_runs_status  ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_bp      ON runs(blueprint_name);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC);

CREATE TABLE IF NOT EXISTS steps (
    run_id            TEXT NOT NULL REFERENCES runs(run_id) ON DELETE CASCADE,
    step_index        INTEGER NOT NULL,
    component         TEXT NOT NULL,
    skill_type        TEXT,
    status            TEXT NOT NULL,
    started_at        TEXT NOT NULL,
    duration_ms       REAL,
    error             TEXT,
    output_keys       TEXT NOT NULL,
    context_snapshot  TEXT,
    PRIMARY KEY (run_id, step_index)
);

CREATE TABLE IF NOT EXISTS checkpoints (
    checkpoint_id  TEXT PRIMARY KEY,
    flow_config    TEXT NOT NULL,
    context        TEXT NOT NULL,
    created_at     TEXT NOT NULL
);
"""


def _dumps(value: Any) -> str:
    return json.dumps(value, default=str)


class SQLiteRunStore(RunStore):
    """RunStore persisting to a single SQLite file.

    Thread-safe: the DAG executor runs sync skills via ``run_in_executor`` so
    concurrent writes are possible. We use ``check_same_thread=False`` plus a
    lock around every write.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # -- runs --------------------------------------------------------------
    def save_run(self, run: RunRecord) -> str:
        row = (
            run.run_id,
            run.blueprint_name,
            run.blueprint_version,
            run.blueprint_path,
            _dumps(run.blueprint_snapshot),
            run.flow_type,
            str(run.status),
            _dumps(run.initial_data),
            _dumps(run.final_context) if run.final_context is not None else None,
            run.error,
            run.suspended_at_node,
            run.suspension_reason,
            run.checkpoint_id,
            run.created_at,
            run.updated_at,
            run.duration_ms,
        )
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO runs (
                    run_id, blueprint_name, blueprint_version, blueprint_path,
                    blueprint_snapshot, flow_type, status, initial_data,
                    final_context, error, suspended_at_node, suspension_reason,
                    checkpoint_id, created_at, updated_at, duration_ms
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status=excluded.status,
                    final_context=excluded.final_context,
                    error=excluded.error,
                    suspended_at_node=excluded.suspended_at_node,
                    suspension_reason=excluded.suspension_reason,
                    checkpoint_id=excluded.checkpoint_id,
                    updated_at=excluded.updated_at,
                    duration_ms=excluded.duration_ms
                """,
                row,
            )
            self._conn.commit()
        return run.run_id

    def load_run(self, run_id: str) -> RunRecord | None:
        with self._lock:
            cur = self._conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,))
            row = cur.fetchone()
        return self._row_to_run(row) if row else None

    def list_runs(
        self,
        *,
        status: RunStatus | None = None,
        blueprint: str | None = None,
        limit: int = 50,
    ) -> list[RunRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if status is not None:
            clauses.append("status=?")
            params.append(str(status))
        if blueprint is not None:
            clauses.append("blueprint_name=?")
            params.append(blueprint)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)
        with self._lock:
            cur = self._conn.execute(
                f"SELECT * FROM runs{where} ORDER BY created_at DESC LIMIT ?",
                params,
            )
            rows = cur.fetchall()
        return [self._row_to_run(r) for r in rows]

    def delete_run(self, run_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM runs WHERE run_id=?", (run_id,))
            self._conn.commit()

    # -- steps -------------------------------------------------------------
    def save_step(self, step: StepRecord) -> None:
        row = (
            step.run_id,
            step.step_index,
            step.component,
            step.skill_type,
            str(step.status),
            step.started_at,
            step.duration_ms,
            step.error,
            _dumps(step.output_keys),
            _dumps(step.context_snapshot)
            if step.context_snapshot is not None
            else None,
        )
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO steps (
                    run_id, step_index, component, skill_type, status,
                    started_at, duration_ms, error, output_keys, context_snapshot
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(run_id, step_index) DO UPDATE SET
                    component=excluded.component,
                    skill_type=excluded.skill_type,
                    status=excluded.status,
                    started_at=excluded.started_at,
                    duration_ms=excluded.duration_ms,
                    error=excluded.error,
                    output_keys=excluded.output_keys,
                    context_snapshot=excluded.context_snapshot
                """,
                row,
            )
            self._conn.commit()

    def load_steps(self, run_id: str) -> list[StepRecord]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT * FROM steps WHERE run_id=? ORDER BY step_index ASC",
                (run_id,),
            )
            rows = cur.fetchall()
        return [self._row_to_step(r) for r in rows]

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # -- row mapping -------------------------------------------------------
    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            run_id=row["run_id"],
            blueprint_name=row["blueprint_name"],
            blueprint_version=row["blueprint_version"],
            blueprint_path=row["blueprint_path"],
            blueprint_snapshot=json.loads(row["blueprint_snapshot"]),
            flow_type=row["flow_type"],
            status=RunStatus(row["status"]),
            initial_data=json.loads(row["initial_data"]),
            final_context=json.loads(row["final_context"])
            if row["final_context"]
            else None,
            error=row["error"],
            suspended_at_node=row["suspended_at_node"],
            suspension_reason=row["suspension_reason"],
            checkpoint_id=row["checkpoint_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            duration_ms=row["duration_ms"],
        )

    @staticmethod
    def _row_to_step(row: sqlite3.Row) -> StepRecord:
        return StepRecord(
            run_id=row["run_id"],
            step_index=row["step_index"],
            component=row["component"],
            skill_type=row["skill_type"],
            status=StepStatus(row["status"]),
            started_at=row["started_at"],
            duration_ms=row["duration_ms"],
            error=row["error"],
            output_keys=json.loads(row["output_keys"]),
            context_snapshot=json.loads(row["context_snapshot"])
            if row["context_snapshot"]
            else None,
        )
