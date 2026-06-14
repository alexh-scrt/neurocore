# NeuroCore vs LangGraph

**LangGraph is excellent for explicit graph/state-machine orchestration.**
**NeuroCore is a higher-level application chassis.** They solve different
problems and compose well.

## Category difference

| | LangGraph | NeuroCore |
|---|-----------|-----------|
| Primary unit | A graph of nodes/edges in Python | A YAML blueprint of skills |
| You write | Graph wiring + node functions | Declarative YAML + reusable skills |
| Distribution | Library code | `pip install neurocore-skill-*` plugins |
| Config | In code | `neurocore.yaml` + `.env` + env overrides |
| Providers | Bring your own | Injected (`anthropic`/`openai`/`ollama`/…) |
| Operations | Build it yourself | Built-in run history, replay, resume, approval |
| Scaffolding | — | `neurocore new <template>` + CLI |

LangGraph optimizes *designing* control flow. NeuroCore optimizes *shipping and
operating* an application around skills — packaging, configuring, running,
streaming, recording, and resuming.

## Use them together

NeuroCore doesn't replace your agent stack — it's the outer chassis. When you
need LangGraph-specific control flow, wrap a compiled LangGraph graph as a
NeuroCore skill:

```python
from neurocore import AsyncSkill, SkillMeta

class LangGraphSkill(AsyncSkill):
    skill_meta = SkillMeta(name="my-graph", version="0.1.0",
                           consumes=["input"], provides=["output"])

    def init(self, config):
        super().init(config)
        from my_graphs import build_graph
        self._graph = build_graph()       # a compiled LangGraph app

    async def process(self, context):
        result = await self._graph.ainvoke({"input": context.get("input")})
        context.set("output", result["output"])
        return context
```

Now that graph is a discoverable, configurable, recordable NeuroCore
component — usable from any blueprint, with run history and approval gates for
free. The same adapter pattern works for LlamaIndex query engines, CrewAI crews,
and the OpenAI Agents SDK.

## The one-liner

> LangGraph helps you design agent graphs. NeuroCore helps you ship agent
> applications.
