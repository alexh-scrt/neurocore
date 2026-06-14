"""Adapt a NeuroCore RunStore to flowengine's CheckpointStore.

flowengine's sync ``FlowEngine.execute()`` auto-saves a ``Checkpoint`` when a
component suspends, and ``FlowEngine.resume()`` reloads it. We back that with the
same SQLite file the RunStore uses (the ``checkpoints`` table) so a single
``runs.db`` holds both durable history and transient checkpoints.

For the in-memory backend (tests), we fall back to flowengine's own
``InMemoryCheckpointStore``.
"""
from __future__ import annotations

import json

from flowengine import Checkpoint, CheckpointStore, InMemoryCheckpointStore

from neurocore.persistence.base import RunStore
from neurocore.persistence.sqlite_store import SQLiteRunStore, _dumps


class SQLiteCheckpointStore(CheckpointStore):
    """flowengine CheckpointStore backed by a SQLiteRunStore's connection."""

    def __init__(self, store: SQLiteRunStore) -> None:
        self._store = store

    def save(self, checkpoint: Checkpoint) -> str:
        with self._store._lock:  # noqa: SLF001 — same package, shared connection
            self._store._conn.execute(
                """
                INSERT INTO checkpoints (checkpoint_id, flow_config, context, created_at)
                VALUES (?,?,?,?)
                ON CONFLICT(checkpoint_id) DO UPDATE SET
                    flow_config=excluded.flow_config,
                    context=excluded.context,
                    created_at=excluded.created_at
                """,
                (
                    checkpoint.checkpoint_id,
                    _dumps(checkpoint.flow_config),
                    _dumps(checkpoint.context),
                    checkpoint.created_at,
                ),
            )
            self._store._conn.commit()
        return checkpoint.checkpoint_id

    def load(self, checkpoint_id: str) -> Checkpoint | None:
        with self._store._lock:  # noqa: SLF001
            cur = self._store._conn.execute(
                "SELECT * FROM checkpoints WHERE checkpoint_id=?", (checkpoint_id,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        return Checkpoint(
            checkpoint_id=row["checkpoint_id"],
            flow_config=json.loads(row["flow_config"]),
            context=json.loads(row["context"]),
            created_at=row["created_at"],
        )

    def delete(self, checkpoint_id: str) -> None:
        with self._store._lock:  # noqa: SLF001
            self._store._conn.execute(
                "DELETE FROM checkpoints WHERE checkpoint_id=?", (checkpoint_id,)
            )
            self._store._conn.commit()


def checkpoint_store_for(run_store: RunStore | None) -> CheckpointStore | None:
    """Return a flowengine CheckpointStore backed by ``run_store``.

    Returns None when persistence is disabled, a SQLite-backed store for the
    sqlite backend, and a per-run_store in-memory store for the memory backend.
    The in-memory store is memoized on the run_store so checkpoints survive
    across the suspend/resume boundary (which makes two separate calls).
    """
    if run_store is None:
        return None
    if isinstance(run_store, SQLiteRunStore):
        return SQLiteCheckpointStore(run_store)
    cached = getattr(run_store, "_checkpoint_store", None)
    if cached is None:
        cached = InMemoryCheckpointStore()
        run_store._checkpoint_store = cached  # type: ignore[attr-defined]
    return cached
