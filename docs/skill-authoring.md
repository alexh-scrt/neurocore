# Authoring skills

A skill is a Python class plus metadata. You can keep skills local to a project
(`skills/*.py`) or publish them as `pip install`-able packages.

## A local skill

Drop a file in your project's `skills/` directory:

```python
# skills/greet.py
from flowengine import FlowContext
from neurocore import Skill, SkillMeta

class GreetSkill(Skill):
    skill_meta = SkillMeta(
        name="greet",
        version="1.0.0",
        description="Greets the user by name.",
        consumes=["user_name"],
        provides=["greeting"],
        config_schema={"properties": {"prefix": {"type": "string"}}},
    )

    def process(self, context: FlowContext) -> FlowContext:
        name = context.get("user_name", "World")
        prefix = self.config.get("prefix", "Hello")
        context.set("greeting", f"{prefix}, {name}!")
        return context
```

Reference it in a blueprint by its `skill_meta.name` (`type: greet`).

## Async, LLM, and retries

- Extend `AsyncSkill` and make `process` a coroutine for non-blocking I/O.
- Set `requires_llm=True` to get an injected `self.llm` (see
  [Providers](providers.md)).
- Add retry policy via `SkillMeta`: `max_retries`, `retry_delay_base`,
  `retry_delay_max`, `retry_on`.

## Publishing a skill package

Skills become installable capabilities. The convention:

```
neurocore-skill-<name>/
├── pyproject.toml
├── README.md
└── src/neurocore_skill_<name>/
    ├── __init__.py        # exports the Skill subclass
    └── skill.py
└── tests/test_skill.py
```

Two rules make discovery automatic:

1. **Naming** — distribution `neurocore-skill-<name>`, import package
   `neurocore_skill_<name>` (kebab → snake).
2. **Entry point** — register under the `neurocore.skills` group:

   ```toml
   [project.entry-points."neurocore.skills"]
   <name> = "neurocore_skill_<name>:<ClassName>Skill"
   ```

   ⚠️ The group is **`neurocore.skills`** — not `neurocore_ai.skills`.

Once installed, `neurocore skill list` shows it and blueprints can use it by
name. See the [neurocore-skills marketplace](https://github.com/alexh-scrt/neurocore-skills)
for ready-made examples (tavily, brave, qdrant, postgres, ollama, telegram, …).

## Testing tip

Isolate the external call (SDK/HTTP) in a small method and monkeypatch it in
tests, so your suite needs neither network nor the SDK installed:

```python
async def test_search(monkeypatch):
    skill = MySkill(); skill.init({"api_key": "x"})
    async def fake(query): return [{"title": "ok"}]
    monkeypatch.setattr(skill, "_search", fake)
    ...
```
