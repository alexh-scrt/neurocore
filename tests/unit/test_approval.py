"""Tests for A4 — human-approval gate (ApprovalSkill + sugar + builtins)."""
from __future__ import annotations

import pytest
import yaml
from flowengine import FlowContext

from neurocore import Skill, SkillMeta
from neurocore.config.schema import NeuroCoreConfig, PersistenceConfig
from neurocore.errors import ExecutionError
from neurocore.persistence import InMemoryRunStore, RunStatus
from neurocore.runtime.blueprint import _normalize_blueprint, load_blueprint
from neurocore.runtime.executor import execute_blueprint_tracked, resume_blueprint
from neurocore.skills.builtin import ApprovalSkill
from neurocore.skills.loader import _register_builtins
from neurocore.skills.registry import SkillRegistry


# ---- ApprovalSkill unit behavior -----------------------------------------

async def test_approval_suspends_on_first_pass():
    skill = ApprovalSkill()
    skill.init({"message": "review please"})
    ctx = await skill.process(FlowContext())
    assert ctx.metadata.suspended
    assert ctx.metadata.suspended_at_node == "approval"
    assert ctx.metadata.suspension_reason == "review please"


async def test_approval_continues_when_approved():
    skill = ApprovalSkill()
    skill.init({})
    ctx = FlowContext()
    ctx.set("resume_data", {"approved": True, "by": "alexh@scrtlabs.com"})
    result = await skill.process(ctx)
    assert not result.metadata.suspended
    assert result.get("approval") == {"approved": True, "by": "alexh@scrtlabs.com"}
    assert not result.has("resume_data")


async def test_approval_rejection_raises_when_required():
    skill = ApprovalSkill()
    skill.init({"require": True})
    ctx = FlowContext()
    ctx.set("resume_data", {"approved": False, "note": "nope"})
    with pytest.raises(ExecutionError, match="rejected at approval gate"):
        await skill.process(ctx)


async def test_approval_rejection_continues_when_not_required():
    skill = ApprovalSkill()
    skill.init({"require": False})
    ctx = FlowContext()
    ctx.set("resume_data", {"approved": False})
    result = await skill.process(ctx)
    assert result.get("approval") == {"approved": False}


# ---- builtin registration -------------------------------------------------

def test_approval_is_registered_as_builtin():
    reg = SkillRegistry()
    _register_builtins(reg)
    assert "approval" in reg
    assert reg.get("approval") is ApprovalSkill


# ---- blueprint sugar ------------------------------------------------------

def test_normalize_desugars_approval_step():
    data = {
        "name": "bp",
        "components": [{"name": "draft", "type": "echo"}],
        "flow": {
            "type": "sequential",
            "steps": [
                {"component": "draft"},
                {"approval": {"name": "human_review", "require": True}},
            ],
        },
    }
    out = _normalize_blueprint(data)
    comp_names = {c["name"]: c for c in out["components"]}
    assert "human_review" in comp_names
    assert comp_names["human_review"]["type"] == "approval"
    assert comp_names["human_review"]["config"]["require"] is True
    assert out["flow"]["steps"][1] == {"component": "human_review"}


def test_load_blueprint_with_approval_sugar(tmp_path):
    bp_yaml = {
        "name": "approve-flow",
        "components": [{"name": "draft", "type": "echo"}],
        "flow": {
            "type": "sequential",
            "steps": [
                {"component": "draft"},
                {"approval": {"name": "review", "message": "ok?"}},
            ],
        },
    }
    path = tmp_path / "bp.yaml"
    path.write_text(yaml.safe_dump(bp_yaml))
    bp = load_blueprint(path)
    assert any(c.type == "approval" and c.name == "review" for c in bp.components)
    assert bp.flow.steps[1].component == "review"


# ---- end-to-end suspend → approve → complete -----------------------------

class Draft(Skill):
    skill_meta = SkillMeta(name="draft", version="0.1.0", provides=["draft"])

    def process(self, context: FlowContext) -> FlowContext:
        context.set("draft", "hello")
        return context


class Send(Skill):
    skill_meta = SkillMeta(name="send", version="0.1.0", provides=["sent"])

    def process(self, context: FlowContext) -> FlowContext:
        context.set("sent", True)
        return context


def _registry():
    reg = SkillRegistry()
    _register_builtins(reg)
    reg.register(Draft)
    reg.register(Send)
    return reg


def _config():
    return NeuroCoreConfig(persistence=PersistenceConfig(backend="memory"))


def test_approval_gate_end_to_end_approve():
    store = InMemoryRunStore()
    data = {
        "name": "bp",
        "components": [{"name": "draft", "type": "draft"},
                       {"name": "send", "type": "send"}],
        "flow": {"type": "sequential", "steps": [
            {"component": "draft"},
            {"approval": {"name": "gate"}},
            {"component": "send"},
        ]},
    }
    from neurocore.runtime.blueprint import Blueprint
    bp = Blueprint(**_normalize_blueprint(data))

    ctx = execute_blueprint_tracked(bp, _registry(), _config(), run_store=store)
    assert ctx.metadata.suspended
    run = store.list_runs()[0]
    assert run.status == RunStatus.SUSPENDED
    assert run.suspended_at_node == "gate"

    resumed = resume_blueprint(
        run.run_id, _registry(), _config(),
        resume_data={"approved": True, "by": "alexh@scrtlabs.com"}, run_store=store,
    )
    assert resumed.get("sent") is True
    assert store.load_run(run.run_id).status == RunStatus.COMPLETED


def test_approval_gate_end_to_end_reject():
    store = InMemoryRunStore()
    data = {
        "name": "bp",
        "components": [{"name": "draft", "type": "draft"},
                       {"name": "send", "type": "send"}],
        "flow": {"type": "sequential", "steps": [
            {"component": "draft"},
            {"approval": {"name": "gate", "require": True}},
            {"component": "send"},
        ]},
    }
    from neurocore.runtime.blueprint import Blueprint
    bp = Blueprint(**_normalize_blueprint(data))

    execute_blueprint_tracked(bp, _registry(), _config(), run_store=store)
    run = store.list_runs()[0]
    with pytest.raises(ExecutionError, match="rejected"):
        resume_blueprint(
            run.run_id, _registry(), _config(),
            resume_data={"approved": False, "note": "no"}, run_store=store,
        )
    assert store.load_run(run.run_id).status == RunStatus.FAILED
