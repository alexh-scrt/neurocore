# NeuroCore

**Pluggable, YAML-driven framework for building agentic AI applications.**

**NeuroCore** is the _chassis_ for agentic AI. It wires together workflow orchestration, discoverable skills, structured configuration, and a developer-friendly CLI — so you can focus on building intelligent agents, not plumbing.

## Architecture

```
┌──────────────────────────────────────────────────┐
│                User's Agent App                  │
├──────────────────────────────────────────────────┤
│  NeuroCore                                       │
│  ┌────────────┬──────────────┬────────────────┐  │
│  │  Config    │  CLI         │  Skill         │  │
│  │  (YAML +   │  (Typer)     │  Registry      │  │
│  │   .env)    │  init, run,  │  (discover,    │  │
│  │            │  skill, val  │   load, meta)  │  │
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
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │NeuroWeave│ │WebSearch │ │ User's Custom    │  │
│  │  Skill   │ │  Skill   │ │   Skills         │  │
│  └──────────┘ └──────────┘ └──────────────────┘  │
└──────────────────────────────────────────────────┘
```

## Key Features

- **YAML-driven configuration** — `neurocore.yaml` with `.env` overlay and env var overrides
- **Skill system** — extend `Skill` (a FlowEngine `BaseComponent` with metadata), discoverable via directory scan or `pyproject.toml` entry points
- **Blueprint execution** — standard FlowEngine YAML flows with skill-aware resolution
- **Structured logging** — `structlog` with console (dev) and JSON (production) modes
- **CLI** — `neurocore init`, `run`, `skill list/info`, `validate`, `version`

---

## Quickstart

### 1. Install

```bash
pip install neurocore
```

Or for local development with [FlowEngine](https://github.com/alexh-scrt/flowengine):

```bash
# Clone both repos
git clone <neurocore-repo-url> neurocore
git clone <flowengine-repo-url> flowengine

# Install FlowEngine, then NeuroCore
pip install -e ./flowengine
pip install -e "./neurocore[dev]"
```

### 2. Scaffold a project

```bash
neurocore init my-agent
cd my-agent
```

This creates:

```
my-agent/
├── neurocore.yaml          # Project configuration
├── .env.example            # Environment variable template
├── blueprints/
│   └── agent.flow.yaml     # Example blueprint
├── skills/                 # Your custom skills go here
├── data/                   # Persistent data
└── logs/                   # Log files
```

### 3. Create a skill

Create `skills/greet.py`:

```python
from flowengine import FlowContext
from neurocore import Skill, SkillMeta

class GreetSkill(Skill):
    skill_meta = SkillMeta(
        name="greet",
        version="1.0.0",
        description="Greets the user by name",
        provides=["greeting"],
        consumes=["user_name"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        name = context.get("user_name", "World")
        context.set("greeting", f"Hello, {name}!")
        return context
```

### 4. Write a blueprint

Create `blueprints/greet.flow.yaml`:

```yaml
name: greet-flow
components:
  - name: greeter
    type: greet

flow:
  type: sequential
  steps:
    - component: greeter
```

### 5. Run it

```bash
neurocore run blueprints/greet.flow.yaml --data user_name=Alice
```

Output:

```
╭─ Flow Result ─────────────────────────────────╮
│  greeting: Hello, Alice!                      │
╰───────────────────────────────────────────────╯
```

---

## Skill Development Guide

### Skill anatomy

Every skill is a Python class that extends `Skill` and defines a `skill_meta` class attribute:

```python
from flowengine import FlowContext
from neurocore import Skill, SkillMeta

class MySkill(Skill):
    # Required: declarative metadata
    skill_meta = SkillMeta(
        name="my-skill",             # Unique identifier
        version="0.1.0",             # Semantic version
        description="What it does",  # Human-readable
        author="You",                # Optional
        provides=["output_key"],     # Context keys produced
        consumes=["input_key"],      # Context keys consumed
        requires=["some-lib>=1.0"],  # pip dependencies
        tags=["category"],           # Discovery tags
        config_schema={              # JSON Schema for config
            "properties": {
                "api_key": {"type": "string"},
            },
            "required": ["api_key"],
        },
    )

    def process(self, context: FlowContext) -> FlowContext:
        """Main logic — called for each execution."""
        value = context.get("input_key", "")
        api_key = self.config.get("api_key")
        # ... do work ...
        context.set("output_key", result)
        return context
```

### Lifecycle hooks

Skills follow FlowEngine's component lifecycle. Override any of these:

| Method | When | Use case |
|--------|------|----------|
| `init(config)` | Once, at setup | Connect to services, load models |
| `setup(context)` | Before each run | Per-run initialization |
| `process(context)` | Each run | **Main logic** (required) |
| `teardown(context)` | After each run | Cleanup, close connections |
| `validate_config()` | After init | Return `list[str]` of errors |
| `health_check()` | On demand | Return `bool` |

Always call `super().init(config)` if you override `init()`.

### Config injection

Skills receive merged configuration from two sources:

1. **`neurocore.yaml`** — base config under `skills.<name>`
2. **Blueprint** — overlay config under `components[].config`

Blueprint values override YAML values (shallow merge).

```yaml
# neurocore.yaml
skills:
  my-skill:
    api_key: "default-key"
    timeout: 30
```

```yaml
# blueprint.flow.yaml
components:
  - name: s1
    type: my-skill
    config:
      timeout: 60    # Overrides 30 → 60
      # api_key still "default-key" from neurocore.yaml
```

### Skill discovery

NeuroCore finds skills through two mechanisms:

**1. Directory scan** — place `.py` files in your project's `skills/` directory. Any class that extends `Skill` is automatically discovered.

**2. Entry points** — for pip-installable skill packages, declare an entry point in `pyproject.toml`:

```toml
[project.entry-points."neurocore.skills"]
my-skill = "my_package:MySkill"
```

Entry points take precedence over directory-discovered skills with the same name.

### Example: pip-installable skill package

```
my-neurocore-skill/
├── pyproject.toml
├── src/my_neurocore_skill/
│   ├── __init__.py          # exports MySkill
│   └── skill.py             # MySkill class
└── tests/
    └── test_skill.py
```

```toml
# pyproject.toml
[project]
name = "my-neurocore-skill"
dependencies = ["neurocore>=0.1.0"]

[project.entry-points."neurocore.skills"]
my-skill = "my_neurocore_skill:MySkill"
```

After `pip install my-neurocore-skill`, the skill appears in `neurocore skill list` across all projects.

### Async skills

For skills wrapping async APIs, bridge to sync with `asyncio.run()`:

```python
import asyncio
from neurocore import Skill, SkillMeta

class AsyncBridgeSkill(Skill):
    skill_meta = SkillMeta(name="async-bridge", version="0.1.0")

    def init(self, config):
        super().init(config)
        from some_async_lib import AsyncClient
        self._client = AsyncClient()

    def process(self, context):
        result = asyncio.run(self._client.call(context.get("input")))
        context.set("output", result)
        return context

    def teardown(self, context):
        asyncio.run(self._client.close())
```

---

## CLI Reference

### `neurocore init <name>`

Scaffold a new project.

```bash
neurocore init my-agent              # Create in current directory
neurocore init my-agent --dir /tmp   # Create in specific parent
```

### `neurocore run <blueprint>`

Execute a blueprint.

```bash
neurocore run flow.yaml                         # Basic run
neurocore run flow.yaml --data key=value        # Pass initial data
neurocore run flow.yaml --data a=1 --data b=2   # Multiple data args
neurocore run flow.yaml --json                  # JSON output
neurocore run flow.yaml --verbose               # Show execution details
neurocore run flow.yaml --project-root /path    # Explicit project root
```

### `neurocore skill list`

List all discovered skills.

```bash
neurocore skill list                            # Table of all skills
neurocore skill list --project-root /path       # Specific project
```

### `neurocore skill info <name>`

Show detailed skill metadata.

```bash
neurocore skill info greet                      # Metadata, config schema, health
neurocore skill info neuroweave                 # Works for entry point skills too
```

### `neurocore validate <blueprint>`

Validate a blueprint without running it. Three-stage check:

1. **YAML parsing** — is the file valid YAML?
2. **Blueprint structure** — does it have `name`, `components`, `flow`?
3. **Skill references** — do all `type:` values resolve to known skills?

```bash
neurocore validate flow.yaml
neurocore validate flow.yaml --project-root /path
```

### `neurocore --version`

Print the NeuroCore version.

---

## Configuration Reference

### `neurocore.yaml`

```yaml
# Project metadata
project:
  name: "my-agent"
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
  format: "console"          # console (colored) | json (structured)
  file: null                 # Optional: log file path (in addition to stderr)

# Skill configuration (passed to skills at init)
skills:
  neuroweave:
    llm_provider: "anthropic"
    llm_model: "claude-haiku-4-5-20251001"
  my-skill:
    api_key: "from-yaml"
    timeout: 30
```

### Environment variable overrides

Environment variables override `neurocore.yaml` values. Use double underscores for nesting:

```bash
# .env or shell
NEUROCORE_LOGGING__LEVEL=DEBUG
NEUROCORE_LOGGING__FORMAT=json
NEUROCORE_PROJECT__NAME=my-agent
```

**Loading priority** (highest wins):
1. Environment variables
2. `.env` file (project root)
3. `neurocore.yaml`
4. Built-in defaults

### Blueprint format

Blueprints are standard FlowEngine YAML flows. NeuroCore adds skill-aware resolution:

```yaml
name: my-flow
description: "Optional description"

# Declare components — 'type' references a skill name
components:
  - name: step1           # Instance name (unique within blueprint)
    type: my-skill         # Skill name (from registry)
    config:                # Optional: config overlay (merges with neurocore.yaml)
      timeout: 60

  - name: step2
    type: another-skill

# Flow definition — standard FlowEngine syntax
flow:
  type: sequential         # sequential | dag | conditional | cyclic
  steps:
    - component: step1
    - component: step2
```

---

## Project Structure

```
neurocore/
├── pyproject.toml
├── src/neurocore/
│   ├── __init__.py           # Public API, version
│   ├── errors.py             # Exception hierarchy
│   ├── config/               # YAML + .env config loading
│   │   ├── loader.py         # load_config(), path resolution
│   │   └── schema.py         # NeuroCoreConfig (pydantic-settings)
│   ├── logging/              # structlog setup
│   │   └── setup.py          # configure_logging(), get_logger()
│   ├── skills/               # Skill system
│   │   ├── base.py           # Skill, SkillMeta
│   │   ├── registry.py       # SkillRegistry
│   │   └── loader.py         # discover_skills(), entry points
│   ├── runtime/              # Blueprint execution
│   │   ├── blueprint.py      # load_blueprint(), validate_blueprint()
│   │   └── executor.py       # execute_blueprint(), load_and_run()
│   ├── cli/                  # Typer CLI commands
│   │   ├── app.py            # Main app, command wiring
│   │   ├── init_cmd.py       # neurocore init
│   │   ├── run_cmd.py        # neurocore run
│   │   ├── skill_cmd.py      # neurocore skill list/info
│   │   └── validate_cmd.py   # neurocore validate
│   └── scaffold/             # Project templates
│       └── templates/        # neurocore.yaml, .env.example, agent.flow.yaml
├── tests/
│   ├── unit/                 # Unit tests by module
│   └── integration/          # End-to-end tests
└── examples/
    ├── echo_agent/           # Minimal working example
    └── research_agent/       # NeuroWeave-powered example
```

## Development

```bash
# Run tests
pytest

# Run tests with coverage
pytest --cov=neurocore --cov-report=term-missing

# Lint
ruff check src/ tests/
ruff format src/ tests/
```

## License

Apache-2.0 — see [LICENSE](LICENSE) for details.
