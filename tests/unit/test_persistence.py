"""Tests for the persistence layer (A2): RunStore contract + factory + adapter."""
from __future__ import annotations

import threading

import pytest

from neurocore.config.schema import NeuroCoreConfig, PersistenceConfig
from neurocore.errors import ConfigError
from neurocore.persistence import (
    InMemoryRunStore,
    RunRecord,
    RunStatus,
    SQLiteRunStore,
    StepRecord,
    StepStatus,
    build_run_store,
)
from neurocore.persistence.checkpoint_adapter import checkpoint_store_for


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path):
    if request.param == "memory":
        s = InMemoryRunStore()
    else:
        s = SQLiteRunStore(tmp_path / "runs.db")
    yield s
    s.close()


def _run(run_id: str, **kw) -> RunRecord:
    base = dict(
        run_id=run_id,
        blueprint_name="bp",
        blueprint_snapshot={"name": "bp"},
        flow_type="sequential",
    )
    base.update(kw)
    return RunRecord(**base)


# ---- RunStore contract (parametrized over both backends) ------------------

def test_save_and_load_run(store):
    store.save_run(_run("r1"))
    loaded = store.load_run("r1")
    assert loaded is not None
    assert loaded.run_id == "r1"
    assert loaded.status == RunStatus.RUNNING


def test_load_missing_run_returns_none(store):
    assert store.load_run("nope") is None


def test_save_run_upserts(store):
    store.save_run(_run("r1"))
    store.save_run(_run("r1", status=RunStatus.COMPLETED, duration_ms=12.5))
    loaded = store.load_run("r1")
    assert loaded.status == RunStatus.COMPLETED
    assert loaded.duration_ms == 12.5


def test_save_and_load_steps_ordered(store):
    store.save_run(_run("r1"))
    store.save_step(StepRecord(run_id="r1", step_index=1, component="b"))
    store.save_step(StepRecord(run_id="r1", step_index=0, component="a",
                               output_keys=["x"]))
    steps = store.load_steps("r1")
    assert [s.step_index for s in steps] == [0, 1]
    assert steps[0].output_keys == ["x"]


def test_step_status_roundtrip(store):
    store.save_run(_run("r1"))
    store.save_step(StepRecord(run_id="r1", step_index=0, component="a",
                               status=StepStatus.FAILED, error="boom"))
    steps = store.load_steps("r1")
    assert steps[0].status == StepStatus.FAILED
    assert steps[0].error == "boom"


def test_list_runs_filters_and_orders(store):
    store.save_run(_run("r1", created_at="2026-01-01T00:00:00",
                        status=RunStatus.COMPLETED))
    store.save_run(_run("r2", created_at="2026-02-01T00:00:00",
                        status=RunStatus.FAILED))
    store.save_run(_run("r3", created_at="2026-03-01T00:00:00",
                        status=RunStatus.COMPLETED, blueprint_name="other"))
    # newest-first
    ids = [r.run_id for r in store.list_runs()]
    assert ids == ["r3", "r2", "r1"]
    # filter by status
    assert {r.run_id for r in store.list_runs(status=RunStatus.COMPLETED)} == {"r1", "r3"}
    # filter by blueprint
    assert [r.run_id for r in store.list_runs(blueprint="other")] == ["r3"]
    # limit
    assert len(store.list_runs(limit=1)) == 1


def test_delete_run_cascades_steps(store):
    store.save_run(_run("r1"))
    store.save_step(StepRecord(run_id="r1", step_index=0, component="a"))
    store.delete_run("r1")
    assert store.load_run("r1") is None
    assert store.load_steps("r1") == []


def test_final_context_roundtrip(store):
    store.save_run(_run("r1", final_context={"data": {"answer": 42}}))
    loaded = store.load_run("r1")
    assert loaded.final_context == {"data": {"answer": 42}}


# ---- SQLite-specific ------------------------------------------------------

def test_sqlite_creates_db_and_parent_dir(tmp_path):
    db = tmp_path / "nested" / "dir" / "runs.db"
    s = SQLiteRunStore(db)
    s.save_run(_run("r1"))
    s.close()
    assert db.exists()


def test_sqlite_concurrent_writes(tmp_path):
    s = SQLiteRunStore(tmp_path / "runs.db")
    s.save_run(_run("r1"))

    def writer(i: int) -> None:
        s.save_step(StepRecord(run_id="r1", step_index=i, component=f"c{i}"))

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(s.load_steps("r1")) == 20
    s.close()


# ---- factory --------------------------------------------------------------

def test_factory_disabled_returns_none():
    cfg = NeuroCoreConfig(persistence=PersistenceConfig(enabled=False))
    assert build_run_store(cfg) is None


def test_factory_memory_backend():
    cfg = NeuroCoreConfig(persistence=PersistenceConfig(backend="memory"))
    assert isinstance(build_run_store(cfg), InMemoryRunStore)


def test_factory_sqlite_backend(tmp_path):
    cfg = NeuroCoreConfig(project_root=tmp_path,
                          persistence=PersistenceConfig(backend="sqlite"))
    s = build_run_store(cfg)
    assert isinstance(s, SQLiteRunStore)
    assert cfg.runs_db_path == tmp_path / "data" / "runs.db"
    s.close()


def test_factory_unknown_backend_raises():
    cfg = NeuroCoreConfig(persistence=PersistenceConfig(backend="bogus"))
    with pytest.raises(ConfigError, match="Unknown persistence backend"):
        build_run_store(cfg)


# ---- checkpoint adapter (flowengine CheckpointStore contract) -------------

def test_checkpoint_adapter_sqlite_roundtrip(tmp_path):
    from flowengine import Checkpoint

    s = SQLiteRunStore(tmp_path / "runs.db")
    cs = checkpoint_store_for(s)
    cp = Checkpoint(flow_config={"name": "f"}, context={"data": {"k": 1}})
    cid = cs.save(cp)
    loaded = cs.load(cid)
    assert loaded is not None
    assert loaded.context == {"data": {"k": 1}}
    cs.delete(cid)
    assert cs.load(cid) is None
    s.close()


def test_checkpoint_adapter_none_when_no_store():
    assert checkpoint_store_for(None) is None


def test_checkpoint_adapter_memory_backend():
    from flowengine import InMemoryCheckpointStore

    cs = checkpoint_store_for(InMemoryRunStore())
    assert isinstance(cs, InMemoryCheckpointStore)
