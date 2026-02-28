# NeuroCore v0.1.0 — Implementation Plan

> **Agentic AI Bootstrapping Framework**
> Design document for implementation. All decisions final unless explicitly revisited.

---

## 1. Vision & Scope

NeuroCore is the **chassis** — a pluggable, YAML-driven framework for building and running agentic AI applications with minimal configuration. It wires together:

- **FlowEngine** (v0.4.1) — workflow orchestration (DAG, sequential, conditional, cyclic graphs)
- **Skills** — components with metadata, discoverable via directory scan + entry points
- **NeuroWeave** (v0.1.0) — first skill, knowledge graph memory (optional, pip-installable)

NeuroCore is **not** an LLM abstraction layer. Each skill owns its own LLM client. NeuroCore orchestrates, configures, logs, and provides the CLI — it doesn't opine on providers.

### v0.1.0 Deliverables

| Deliverable | Description |
|---|---|
| `neurocore init` | Scaffold a new project with config, .env, logging, paths |
| `neurocore run <blueprint>` | Execute a YAML blueprint via FlowEngine |
| `neurocore skill list` | List discovered skills (directory + entry points) |
| `neurocore skill info <n>` | Show skill metadata, config schema, health status |
| `neurocore validate <blueprint>` | Validate a blueprint without executing |
| Skill abstraction | `Skill` base class extending `BaseComponent` with `SkillMeta` |
| Dual discovery | `skills/` directory scan + `pyproject.toml` entry points |
| NeuroWeave skill | `neurocore-skill-neuroweave` wrapper package |
| Config system | YAML-based with `.env` overlay, structured logging |
| Test suite | Unit + integration, ≥90% coverage on core |

### Explicit Non-Goals for v0.1.0

- No web UI or dashboard
- No built-in LLM client abstraction (skills bring their own)
- No skill marketplace or remote registry
- No multi-agent coordination (single-flow execution only)
- No async CLI (sync execution, async skills bridge internally)

---

## 2. Architecture

```
┌──────────────────────────────────────────────────┐
│                User's Agent App                  │
├──────────────────────────────────────────────────┤
│  NeuroCore                                       │
│  ┌────────────┬──────────────┬────────────────┐  │
│  │  Config    │  CLI         │  Skill         │  │
│  │  (YAML +  │  (Typer)     │  Registry      │  │
│  │   .env)   │  init, run,  │  (discover,    │  │
│  │           │  skill, val  │   load, meta)  │  │
│  └────────────┴──────────────┴────────────────┘  │
│  ┌────────────────────────────────────────────┐  │
│  │  Runtime                                   │  │
│  │  (Blueprint loader → FlowEngine executor)  │  │
│  └────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────┤
│  FlowEngine (orchestration)                      │
│  BaseComponent, DAG/Sequential/Cyclic, Hooks     │
├──────────────────────────────────────────────────┤
│  Skills (pip-installable or local)               │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │NeuroWeave│ │WebSearch │ │ User's Custom    │ │
│  │  Skill   │ │  Skill   │ │   Skills         │ │
│  └──────────┘ └──────────┘ └──────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Package Boundaries

| Package | PyPI Name | Depends On | Provides |
|---|---|---|---|
| `neurocore` | `neurocore` | `flowengine`, `pyyaml`, `pydantic-settings`, `structlog`, `typer` | Framework, CLI, skill registry |
| `neurocore-skill-neuroweave` | `neurocore-skill-neuroweave` | `neurocore`, `neuroweave-python` | NeuroWeave as a FlowEngine skill |
| `flowengine` | `flowengine` | `pyyaml`, `pydantic` | Workflow execution engine |
| `neuroweave` | `neuroweave-python` | `anthropic`, `networkx`, etc. | Knowledge graph memory |

NeuroCore has **no direct dependency** on NeuroWeave. The skill wrapper package bridges them.

---

## 3. Project Structure

```
neurocore/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
├── .env.example
├── src/
│   └── neurocore/
│       ├── __init__.py              # Public API exports
│       ├── py.typed                 # PEP 561 marker
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── schema.py            # Pydantic models for neurocore.yaml
│       │   ├── loader.py            # YAML + .env loading, path resolution
│       │   └── defaults.py          # Default config values
│       │
│       ├── logging/
│       │   ├── __init__.py
│       │   └── setup.py             # structlog configuration (JSON + console)
│       │
│       ├── skills/
│       │   ├── __init__.py
│       │   ├── base.py              # Skill base class + SkillMeta
│       │   ├── registry.py          # Discovery (directory + entry points)
│       │   └── loader.py            # Instantiation + config injection
│       │
│       ├── runtime/
│       │   ├── __init__.py
│       │   ├── blueprint.py         # Blueprint YAML parser + validator
│       │   └── executor.py          # FlowEngine wiring + execution
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py               # Typer app, top-level commands
│       │   ├── init_cmd.py          # neurocore init
│       │   ├── run_cmd.py           # neurocore run
│       │   ├── skill_cmd.py         # neurocore skill (list, info)
│       │   └── validate_cmd.py      # neurocore validate
│       │
│       ├── scaffold/
│       │   ├── __init__.py
│       │   └── templates/           # Project scaffold templates
│       │       ├── neurocore.yaml
│       │       ├── .env.example
│       │       └── agent.flow.yaml
│       │
│       └── errors.py                # NeuroCore-specific exceptions
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── config/
│   │   ├── skills/
│   │   ├── runtime/
│   │   └── cli/
│   └── integration/
│       ├── test_init_scaffold.py
│       ├── test_run_blueprint.py
│       └── test_skill_discovery.py
│
└── examples/
    ├── echo_agent/                  # Minimal working example
    │   ├── neurocore.yaml
    │   ├── agent.flow.yaml
    │   └── skills/
    │       └── echo.py
    └── research_agent/              # NeuroWeave-powered example
        ├── neurocore.yaml
        └── research.flow.yaml
```

---

## 4. Detailed Design

### 4.1 Configuration System

**File:** `neurocore.yaml` (project root)

```yaml
# neurocore.yaml — project configuration
project:
  name: "my-research-agent"
  version: "0.1.0"

# Paths (relative to project root, resolved at load time)
paths:
  skills: "skills"           # Local skills directory
  blueprints: "blueprints"   # Flow definition files
  data: "data"               # Persistent data directory
  logs: "logs"               # Log output directory

# Logging
logging:
  level: "INFO"              # DEBUG | INFO | WARNING | ERROR
  format: "console"          # console | json
  file: null                 # Optional: path to log file (in addition to stderr)

# Skill configuration (passed to skills at init)
skills:
  neuroweave:
    llm_provider: "anthropic"
    llm_model: "claude-haiku-4-5-20251001"
    graph_backend: "memory"
  web_search:
    provider: "tavily"
    max_results: 5
```

**Loading priority** (highest wins):
1. Environment variables: `NEUROCORE_LOGGING__LEVEL=DEBUG` (double underscore for nesting)
2. `.env` file (project root)
3. `neurocore.yaml`
4. Built-in defaults

**Path resolution:** All paths in `paths:` are resolved relative to `project_root` (the directory containing `neurocore.yaml`). Absolute paths are used as-is.

### 4.2 Structured Logging

Reuse the same pattern as NeuroWeave: `structlog` with console (colored, dev) and JSON (machine-parseable, production) modes. Every module gets a named logger via `get_logger("module_name")`.

### 4.3 Skill Abstraction

A **Skill** is a FlowEngine `BaseComponent` with declarative metadata. The metadata enables discovery, validation, documentation, and configuration injection.

```python
@dataclass(frozen=True)
class SkillMeta:
    name: str                              # Unique skill identifier
    version: str                           # Semantic version
    description: str = ""                  # Human-readable description
    author: str = ""                       # Author/maintainer
    requires: list[str] = field(...)       # pip package dependencies
    provides: list[str] = field(...)       # Context keys this skill produces
    consumes: list[str] = field(...)       # Context keys this skill reads
    config_schema: dict = field(...)       # JSON Schema for config
    tags: list[str] = field(...)           # Categorization tags


class Skill(BaseComponent):
    skill_meta: SkillMeta  # Must be defined by subclass

    def validate_config(self) -> list[str]: ...
    def health_check(self) -> bool: ...
```

### 4.4 Skill Discovery

Two mechanisms, merged into a unified registry:

1. **Directory scan** (`skills/` folder) — walks directory, imports `.py` files, finds `Skill` subclasses
2. **Entry points** (`pyproject.toml`) — scans `neurocore.skills` group

Entry points take precedence (pip-installed version wins over local copy).

### 4.5 Blueprint & Runtime

A blueprint is a standard FlowEngine YAML flow. The runtime resolves skill names to classes, merges config (neurocore.yaml base + blueprint overlay), and executes via FlowEngine.

**Config merging:** `neurocore.yaml → skills.<name>` (base) + blueprint `components[].config` (overlay).

### 4.6 CLI

```
neurocore init [--name NAME] [--dir PATH]
neurocore run <blueprint.flow.yaml> [--data KEY=VALUE]...
neurocore skill list
neurocore skill info <name>
neurocore validate <blueprint.flow.yaml>
neurocore version
```

### 4.7 NeuroWeave Skill Package

Separate package `neurocore-skill-neuroweave` bridges NeuroWeave into NeuroCore's skill system. Registers via entry point. Supports three modes: process (extract), query (retrieve), context (both).

---

## 5. Implementation Tasks

### Phase 1: Foundation (Tasks 1–5) — Parallel

| Task | Description | Tests |
|---|---|---|
| T1 | Project scaffold & packaging | ~5 |
| T2 | Configuration system (YAML + .env + path resolution) | ~20 |
| T3 | Structured logging (structlog, console/JSON) | ~10 |
| T4 | Error types | ~5 |
| T5 | Skill base class + SkillMeta | ~15 |

### Phase 2: Discovery & Registry (Tasks 6–7)

Depends on: T5

| Task | Description | Tests |
|---|---|---|
| T6 | Skill discovery — directory scan | ~15 |
| T7 | Skill discovery — entry points + merge | ~12 |

### Phase 3: Runtime (Tasks 8–10)

Depends on: T2, T6, T7

| Task | Description | Tests |
|---|---|---|
| T8 | Blueprint parser & validator | ~15 |
| T9 | Blueprint executor (FlowEngine wiring) | ~15 |
| T10 | Skill loader (instantiation + config injection) | ~10 |

### Phase 4: CLI (Tasks 11–14)

Depends on: T2, T3, T9

| Task | Description | Tests |
|---|---|---|
| T11 | `neurocore init` (scaffold) | ~10 |
| T12 | `neurocore run` (execute blueprint) | ~10 |
| T13 | `neurocore skill list/info` | ~8 |
| T14 | `neurocore validate` | ~6 |

### Phase 5: NeuroWeave Skill & Integration (Tasks 15–16)

Depends on: All Phase 1–4

| Task | Description | Tests |
|---|---|---|
| T15 | NeuroWeave skill package | ~15 |
| T16 | End-to-end integration tests | ~10 |

### Phase 6: Documentation (Task 17)

| Task | Description |
|---|---|
| T17 | README, examples, CHANGELOG |

---

## 6. Dependency Graph

```
Phase 1 (parallel):
  T1 (scaffold) ──┐
  T2 (config)  ───┤
  T3 (logging) ───┼──→ Phase 2: T6, T7 (discovery) ──→ Phase 3: T8, T9, T10 (runtime)
  T4 (errors)  ───┤                                              │
  T5 (skill)   ───┘                                              ▼
                                                         Phase 4: T11–T14 (CLI)
                                                                  │
                                                                  ▼
                                                         Phase 5: T15, T16 (integration)
                                                                  │
                                                                  ▼
                                                         Phase 6: T17 (docs)
```

**Estimated total: 17 tasks, ~176 tests**

---

## 7. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Config format | YAML everywhere | Consistent with FlowEngine, single mental model |
| Config loading | pydantic-settings | Env var overlay for free, validation, type safety |
| CLI framework | Typer | Type-hinted, built on Click, rich output |
| Logging | structlog | Structured from day one, matches NeuroWeave |
| Skill base | Extends `BaseComponent` | Zero-cost FlowEngine integration |
| Skill discovery | Directory + entry points | Local dev + pip-installable packages |
| Skill precedence | Entry points > directory | Installed version wins over local copy |
| NeuroWeave coupling | Separate skill package | NeuroCore stays LLM/memory agnostic |
| LLM abstraction | None (skills own theirs) | NeuroCore orchestrates, doesn't opine on providers |
| Blueprint format | Standard FlowEngine YAML | No new format to learn, full FlowEngine power |
| Async bridge | `asyncio.run()` in skill | CLI is sync, async skills bridge internally |

---

## 8. Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Entry point discovery slow | CLI startup lag | Cache discovery results, lazy load |
| Async/sync bridge in skills | Event loop conflicts | Document pattern, test with nested loops |
| FlowEngine type validation | False negatives with skill names | `validate_types=False`, add skill-aware validation |
| Config merge complexity | Unexpected overrides | Clear precedence, `--verbose` shows merged config |
| NeuroWeave async in sync FlowEngine | Runtime errors | Test thoroughly, document `asyncio.run()` pattern |

---

## 9. Success Criteria

v0.1.0 is **done** when:

1. `pip install neurocore && neurocore init my-agent && cd my-agent && neurocore run blueprints/agent.flow.yaml` works
2. `pip install neurocore-skill-neuroweave` makes NeuroWeave discoverable via `neurocore skill list`
3. A blueprint referencing the NeuroWeave skill by name executes correctly
4. All 176+ tests pass
5. Both packages published to PyPI
6. README documents quickstart, skill development, and config reference
