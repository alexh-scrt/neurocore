"""Tests for hybrid graph routing: GraphExecutor for ports/conditions/cycles."""
from __future__ import annotations

from flowengine import FlowContext

from neurocore import AsyncSkill, SkillMeta
from neurocore.config.schema import NeuroCoreConfig, PersistenceConfig
from neurocore.persistence import InMemoryRunStore, RunStatus
from neurocore.runtime.blueprint import (
    Blueprint,
    BlueprintComponent,
    FlowDefinition,
    FlowEdge,
    FlowGraph,
)
from neurocore.runtime.executor import (
    _graph_needs_executor,
    execute_blueprint,
    execute_blueprint_tracked,
)
from neurocore.skills.registry import SkillRegistry


class Router(AsyncSkill):
    skill_meta = SkillMeta(name="router", version="0.1.0", provides=["score"])

    async def process(self, context: FlowContext) -> FlowContext:
        context.set("score", int(self.config.get("score", 10)))
        self.set_output_port(context, self.config.get("port", "yes"))
        return context


class Mark(AsyncSkill):
    skill_meta = SkillMeta(name="mark", version="0.1.0", provides=["marks"])

    async def process(self, context: FlowContext) -> FlowContext:
        marks = context.get("marks", [])
        marks.append(self.name)
        context.set("marks", marks)
        return context


class Counter(AsyncSkill):
    skill_meta = SkillMeta(name="counter", version="0.1.0", provides=["n"])

    async def process(self, context: FlowContext) -> FlowContext:
        context.set("n", context.get("n", 0) + 1)
        self.set_output_port(context, "again")
        return context


def _registry(*skills):
    reg = SkillRegistry()
    for s in skills:
        reg.register(s)
    return reg


def _cfg():
    return NeuroCoreConfig(persistence=PersistenceConfig(enabled=False))


# -- predicate ---------------------------------------------------------------

def test_predicate_plain_dag_false():
    bp = Blueprint(
        name="bp", components=[BlueprintComponent(name="a", type="mark"),
                               BlueprintComponent(name="b", type="mark")],
        flow=FlowDefinition(type="graph",
                            nodes=[FlowGraph(id="a", component="a"),
                                   FlowGraph(id="b", component="b")],
                            edges=[FlowEdge(source="a", target="b")]),
    )
    assert _graph_needs_executor(bp) is False


def test_predicate_ports_true():
    bp = Blueprint(
        name="bp", components=[BlueprintComponent(name="a", type="mark"),
                               BlueprintComponent(name="b", type="mark")],
        flow=FlowDefinition(type="graph",
                            nodes=[FlowGraph(id="a", component="a"),
                                   FlowGraph(id="b", component="b")],
                            edges=[FlowEdge(source="a", target="b", port="yes")]),
    )
    assert _graph_needs_executor(bp) is True


# -- port routing ------------------------------------------------------------

def test_port_routing_only_matching_branch():
    bp = Blueprint(
        name="route",
        components=[
            BlueprintComponent(name="router", type="router", config={"port": "yes"}),
            BlueprintComponent(name="b", type="mark"),
            BlueprintComponent(name="c", type="mark"),
        ],
        flow=FlowDefinition(
            type="graph",
            nodes=[FlowGraph(id="router", component="router"),
                   FlowGraph(id="b", component="b"),
                   FlowGraph(id="c", component="c")],
            edges=[FlowEdge(source="router", target="b", port="yes"),
                   FlowEdge(source="router", target="c", port="no")],
        ),
    )
    ctx = execute_blueprint(bp, _registry(Router, Mark), _cfg())
    assert ctx.get("marks") == ["b"]  # only the matching-port branch ran


# -- edge conditions ---------------------------------------------------------

def test_edge_condition_routing():
    bp = Blueprint(
        name="cond",
        components=[
            BlueprintComponent(name="router", type="router", config={"score": 10}),
            BlueprintComponent(name="b", type="mark"),
            BlueprintComponent(name="c", type="mark"),
        ],
        flow=FlowDefinition(
            type="graph",
            nodes=[FlowGraph(id="router", component="router"),
                   FlowGraph(id="b", component="b"),
                   FlowGraph(id="c", component="c")],
            edges=[FlowEdge(source="router", target="b",
                            condition="context.data.score > 5"),
                   FlowEdge(source="router", target="c",
                            condition="context.data.score > 50")],
        ),
    )
    ctx = execute_blueprint(bp, _registry(Router, Mark), _cfg())
    assert ctx.get("marks") == ["b"]


# -- cyclic + max_iterations -------------------------------------------------

def test_cyclic_max_iterations():
    bp = Blueprint(
        name="loop",
        components=[BlueprintComponent(name="counter", type="counter")],
        flow=FlowDefinition(
            type="graph",
            settings={"max_iterations": 3, "on_max_iterations": "exit"},
            nodes=[FlowGraph(id="counter", component="counter")],
            edges=[FlowEdge(source="counter", target="counter", port="again")],
        ),
    )
    ctx = execute_blueprint(bp, _registry(Counter), _cfg())
    assert ctx.get("n") >= 1
    assert ctx.metadata.iteration_count <= 4  # bounded by max_iterations


# -- tracked run via the engine path -----------------------------------------

def test_port_routing_tracked():
    store = InMemoryRunStore()
    bp = Blueprint(
        name="route",
        components=[
            BlueprintComponent(name="router", type="router", config={"port": "yes"}),
            BlueprintComponent(name="b", type="mark"),
            BlueprintComponent(name="c", type="mark"),
        ],
        flow=FlowDefinition(
            type="graph",
            nodes=[FlowGraph(id="router", component="router"),
                   FlowGraph(id="b", component="b"),
                   FlowGraph(id="c", component="c")],
            edges=[FlowEdge(source="router", target="b", port="yes"),
                   FlowEdge(source="router", target="c", port="no")],
        ),
    )
    cfg = NeuroCoreConfig(persistence=PersistenceConfig(backend="memory"))
    ctx = execute_blueprint_tracked(bp, _registry(Router, Mark), cfg, run_store=store)
    assert ctx.get("marks") == ["b"]
    run = store.list_runs()[0]
    assert run.status == RunStatus.COMPLETED
    components_run = {s.component for s in store.load_steps(run.run_id)}
    assert "router" in components_run and "b" in components_run
    assert "c" not in components_run  # skipped by port routing
