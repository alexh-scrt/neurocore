"""Persistence models and the RunStore interface.

NeuroCore persists every blueprint execution as a durable *run* with an
ordered list of *step* records. This makes runs inspectable, resumable, and
replayable — the difference between a "nice framework" and a "production agent
runtime".

The ``RunStore`` interface is intentionally separate from flowengine's
``CheckpointStore``: a checkpoint is transient (deleted on resume), while a run
record is durable history. A ``RunStore`` can still *back* a ``CheckpointStore``
for flowengine's sync suspend/resume path — see
:mod:`neurocore.persistence.checkpoint_adapter`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat()


class RunStatus(StrEnum):
    """Lifecycle status of a run."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SUSPENDED = "suspended"  # awaiting human approval / external input
    CANCELLED = "cancelled"


class StepStatus(StrEnum):
    """Outcome of a single step within a run."""

    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class RunRecord(BaseModel):
    """A durable record of one blueprint execution."""

    run_id: str
    blueprint_name: str
    blueprint_version: str = "1.0"
    blueprint_path: str | None = None
    # Full Blueprint.model_dump() so a run can be replayed/resumed even if the
    # source file has moved or changed.
    blueprint_snapshot: dict[str, Any] = Field(default_factory=dict)
    flow_type: str = "sequential"
    status: RunStatus = RunStatus.RUNNING
    initial_data: dict[str, Any] = Field(default_factory=dict)
    final_context: dict[str, Any] | None = None  # FlowContext.to_dict()
    error: str | None = None
    suspended_at_node: str | None = None
    suspension_reason: str | None = None
    checkpoint_id: str | None = None  # flowengine checkpoint id (sync path only)
    created_at: str = Field(default_factory=utcnow_iso)
    updated_at: str = Field(default_factory=utcnow_iso)
    duration_ms: float | None = None


class StepRecord(BaseModel):
    """A record of one step (component invocation) within a run."""

    run_id: str
    step_index: int
    component: str
    skill_type: str | None = None
    status: StepStatus = StepStatus.COMPLETED
    started_at: str = Field(default_factory=utcnow_iso)
    duration_ms: float | None = None
    error: str | None = None
    output_keys: list[str] = Field(default_factory=list)
    context_snapshot: dict[str, Any] | None = None  # gated by persist_step_snapshots


class RunStore(ABC):
    """Abstract durable store for run history.

    Implementations: :class:`~neurocore.persistence.sqlite_store.SQLiteRunStore`
    (default) and :class:`~neurocore.persistence.memory_store.InMemoryRunStore`
    (tests).
    """

    @abstractmethod
    def save_run(self, run: RunRecord) -> str:
        """Insert or update a run by ``run_id``. Returns the run_id."""
        ...

    @abstractmethod
    def save_step(self, step: StepRecord) -> None:
        """Insert or update a step by ``(run_id, step_index)``."""
        ...

    @abstractmethod
    def load_run(self, run_id: str) -> RunRecord | None:
        """Load a run by id, or None if not found."""
        ...

    @abstractmethod
    def load_steps(self, run_id: str) -> list[StepRecord]:
        """Load a run's steps, ordered by step_index."""
        ...

    @abstractmethod
    def list_runs(
        self,
        *,
        status: RunStatus | None = None,
        blueprint: str | None = None,
        limit: int = 50,
    ) -> list[RunRecord]:
        """List runs newest-first, optionally filtered by status/blueprint."""
        ...

    @abstractmethod
    def delete_run(self, run_id: str) -> None:
        """Delete a run and its steps."""
        ...

    def close(self) -> None:  # noqa: B027 — optional override, default no-op
        """Release any underlying resources (no-op by default)."""
