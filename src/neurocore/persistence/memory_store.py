"""In-memory RunStore for tests and ephemeral runs."""
from __future__ import annotations

from neurocore.persistence.base import (
    RunRecord,
    RunStatus,
    RunStore,
    StepRecord,
)


class InMemoryRunStore(RunStore):
    """Non-persistent RunStore backed by dicts. Useful for tests."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._steps: dict[str, dict[int, StepRecord]] = {}
        # Lazily populated by checkpoint_store_for() so flowengine checkpoints
        # survive across a suspend/resume cycle. Typed loosely to avoid a hard
        # import of flowengine's CheckpointStore here.
        self._checkpoint_store: object | None = None

    def save_run(self, run: RunRecord) -> str:
        self._runs[run.run_id] = run.model_copy(deep=True)
        self._steps.setdefault(run.run_id, {})
        return run.run_id

    def save_step(self, step: StepRecord) -> None:
        self._steps.setdefault(step.run_id, {})[step.step_index] = step.model_copy(
            deep=True
        )

    def load_run(self, run_id: str) -> RunRecord | None:
        run = self._runs.get(run_id)
        return run.model_copy(deep=True) if run else None

    def load_steps(self, run_id: str) -> list[StepRecord]:
        steps = self._steps.get(run_id, {})
        return [steps[i].model_copy(deep=True) for i in sorted(steps)]

    def list_runs(
        self,
        *,
        status: RunStatus | None = None,
        blueprint: str | None = None,
        limit: int = 50,
    ) -> list[RunRecord]:
        runs = list(self._runs.values())
        if status is not None:
            runs = [r for r in runs if r.status == status]
        if blueprint is not None:
            runs = [r for r in runs if r.blueprint_name == blueprint]
        runs.sort(key=lambda r: r.created_at, reverse=True)
        return [r.model_copy(deep=True) for r in runs[:limit]]

    def delete_run(self, run_id: str) -> None:
        self._runs.pop(run_id, None)
        self._steps.pop(run_id, None)
