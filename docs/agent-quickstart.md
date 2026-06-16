# NeuroCore Agent Quickstart

A one-page bootstrap for an **AI agent** that will build and run **worker agents**
with NeuroCore. Paste this into your agent's system prompt / instructions. For the
full guide (graph routing, ports/conditions, skill catalog, custom skills,
deployment, best practices), see the [Agent Manual](agent-manual.md).

---

NeuroCore is your chassis for **worker agents**. A worker = a YAML **blueprint**
(naming reusable **skills** + a **flow**) that the runtime executes, records, and
can pause/resume. You author the blueprint, feed it inputs, and read its outputs.
You compose *installed skills* — you don't write the executor.

## 1. Install (pull from PyPI)

```bash
pip install neurocore-ai                                   # runtime + CLI
pip install neurocore-skill-tavily neurocore-skill-math    # capabilities you need
# local LLM, no cloud key:  pip install "neurocore-ai[local]"
```

Installed skills are auto-discovered (entry-point group `neurocore.skills`).

## 2. The loop (run every time)

discover → write blueprint → validate → run → inspect → (resume) → iterate

```bash
neurocore skill list                 # what skills exist
neurocore skill info <name>          # a skill's consumes/provides/config
neurocore validate blueprints/x.flow.yaml
neurocore run blueprints/x.flow.yaml --data query="..." --json
neurocore runs list                  # durable run history
neurocore runs inspect <run_id> --full --json
```

## 3. Author a blueprint (a worker)

```yaml
name: research-worker
components:
  - {name: search, type: tavily, config: {max_results: 5}}
  - {name: summarize, type: summarize}   # a requires_llm skill
flow:
  type: sequential                       # or `graph` for branching/loops
  steps: [{component: search}, {component: summarize}]
```

Scaffold a starter instead: `neurocore new research-agent my-agent`
(`neurocore new --list` shows all templates).

## 4. Exchange data with the worker

- **IN:** `--data key=value` (skills read with `context.get("key")`).
- **OUT:** the printed/returned final context (skills' `provides` keys) + the
  persisted run record (`neurocore runs inspect <id> --json`).
- Skill outputs are envelopes `{status, result, ...}` — **always check `status`**
  (`ok`/`refuted`/`tool_unavailable`/`error`/…).
- Wire skills by matching keys (`provides` → `consumes`), or remap with
  `input_key` / `output_key`. Branch with edge `port` / `condition` in graph flows.
- **Human-in-the-loop:** add an `approval:` step → run becomes `suspended` →
  `neurocore runs approve <id>` (or `--reject`) to resume.

## 5. Give it an LLM (in `neurocore.yaml`)

```yaml
llm: {provider: anthropic, model: claude-sonnet-4-6, api_key_env: ANTHROPIC_API_KEY}
# local:  provider: ollama, base_url: http://localhost:11434/v1
```

## In-process instead of CLI

```python
from pathlib import Path
from neurocore.runtime.executor import load_and_run, resume_blueprint
from neurocore.config.loader import load_config
from neurocore.skills.loader import discover_skills
from neurocore.persistence import build_run_store, RunStatus

ctx = load_and_run(Path("blueprints/x.flow.yaml"), initial_data={"query": "..."})
answer = ctx.get("answer")
if ctx.metadata.suspended:                  # paused at an approval gate
    store = build_run_store(load_config())
    run = store.list_runs(status=RunStatus.SUSPENDED)[0]
    resume_blueprint(run.run_id, discover_skills(load_config()), load_config(),
                     resume_data={"approved": True}, run_store=store)
```

---

**Mental model to keep:** a *worker engine* is a **blueprint + skills** — data you
author, not code. Always `validate` before `run`, read the **run record** (not
just the final value) to reason about *how* a worker behaved, and add new
abilities by `pip install neurocore-skill-*` (they appear in `skill list`
automatically). Depth: [Agent Manual](agent-manual.md).
