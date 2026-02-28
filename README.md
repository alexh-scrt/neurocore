# NeuroCore

**Pluggable, YAML-driven framework for building agentic AI applications.**

NeuroCore is the chassis for agentic AI. It wires together workflow orchestration, discoverable skills, structured configuration, and a developer-friendly CLI — so you can focus on building intelligent agents, not plumbing.

## Architecture

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

## Key Features

- **YAML-driven configuration** — `neurocore.yaml` with `.env` overlay and env var overrides
- **Skill system** — extend `Skill` (a FlowEngine `BaseComponent` with metadata), discoverable via directory scan or `pyproject.toml` entry points
- **Blueprint execution** — standard FlowEngine YAML flows with skill-aware resolution
- **Structured logging** — `structlog` with console (dev) and JSON (production) modes
- **CLI** — `neurocore init`, `run`, `skill list/info`, `validate`, `version`

## Installation

### Development Setup

NeuroCore depends on [FlowEngine](https://github.com/alexh-scrt/flowengine). For local development with an editable FlowEngine:

```bash
# Clone the repos
git clone <neurocore-repo-url> neurocore
git clone <flowengine-repo-url> flowengine

# Install FlowEngine (editable)
pip install -e ./flowengine

# Install NeuroCore (editable, with dev dependencies)
pip install -e "./neurocore[dev]"
```

### Verify Installation

```bash
neurocore --version
# neurocore 0.1.0
```

## Project Structure

```
neurocore/
├── pyproject.toml
├── src/neurocore/
│   ├── __init__.py           # Public API, version
│   ├── errors.py             # Exception hierarchy
│   ├── config/               # YAML + .env config loading
│   ├── logging/              # structlog setup
│   ├── skills/               # Skill base class, registry, discovery
│   ├── runtime/              # Blueprint parser + FlowEngine executor
│   ├── cli/                  # Typer CLI commands
│   └── scaffold/             # Project templates for `neurocore init`
├── tests/
│   ├── unit/
│   └── integration/
└── examples/
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
