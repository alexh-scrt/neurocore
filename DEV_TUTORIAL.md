# NeuroCore Developer Tutorial

> Build agentic AI applications with pluggable, YAML-driven workflows.
>
> NeuroCore v0.1.0 · Python 3.13+

---

## What You Will Build

By the end of this tutorial you will have built:

1. **Custom skills** — reusable AI components with metadata and config validation
2. **A personal experiences collector** — a chat app that remembers your experiences using NeuroWeave's knowledge graph
3. **A multi-provider LLM agent** — a single skill that talks to OpenAI, Anthropic, or Ollama based on config
4. **A multi-agent research pipeline** — parallel worker agents orchestrated by a coordinator using graph flows

---

## Table of Contents

- [Part 1: Getting Started](#part-1-getting-started)
- [Part 2: Building Your First Skill](#part-2-building-your-first-skill)
- [Part 3: Configuration Deep Dive](#part-3-configuration-deep-dive)
- [Part 4: Blueprints and Flow Orchestration](#part-4-blueprints-and-flow-orchestration)
- [Part 5: Adding NeuroWeave](#part-5-adding-neuroweave-knowledge-graph-memory)
- [Part 6: Chat App — Personal Experiences Collector](#part-6-chat-app--personal-experiences-collector)
- [Part 7: Multi-Provider LLM Chat Agent](#part-7-multi-provider-llm-chat-agent)
- [Part 8: Multi-Agent Parallel Architecture](#part-8-multi-agent-parallel-architecture)
- [Part 9: Packaging and Distribution](#part-9-packaging-and-distribution)
- [Part 10: Deployment and Operations](#part-10-deployment-and-operations)

---

## Part 1: Getting Started

### 1.1 Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.13+ | Required |
| pip | Latest | Package manager |
| git | Any | For cloning repos |
| Anthropic API key | — | Optional, for LLM skills |
| OpenAI API key | — | Optional, for LLM skills |
| Ollama | Latest | Optional, for local LLM deployment |

### 1.2 Installation

**From source (recommended for development):**

```bash
# Clone both repos
git clone <neurocore-repo-url> neurocore
git clone <flowengine-repo-url> flowengine

# Install FlowEngine (editable)
pip install -e ./flowengine

# Install NeuroCore with dev dependencies
pip install -e "./neurocore[dev]"

# Verify
neurocore --version
# neurocore 0.1.0
```

### 1.3 Scaffold Your First Project

```bash
neurocore init my-first-agent
cd my-first-agent
```

Output:

```
Created NeuroCore project: my-first-agent

  /path/to/my-first-agent/
  ├── neurocore.yaml
  ├── .env.example
  ├── blueprints/
  │   └── agent.flow.yaml
  ├── skills/
  ├── data/
  └── logs/

Next steps:
  cd my-first-agent
  cp .env.example .env
  neurocore run blueprints/agent.flow.yaml
```

### 1.4 Project Structure

| File/Directory | Purpose |
|----------------|---------|
| `neurocore.yaml` | Project configuration — paths, logging, skill settings |
| `.env.example` | Template for environment variables (copy to `.env`) |
| `blueprints/` | YAML flow definitions that wire skills together |
| `skills/` | Your custom skill Python files (auto-discovered) |
| `data/` | Persistent data directory |
| `logs/` | Log output directory |

### 1.5 Copy the Environment Template

```bash
cp .env.example .env
```

Now open `neurocore.yaml` to see the default configuration:

```yaml
# neurocore.yaml — project configuration
project:
  name: "my-first-agent"
  version: "0.1.0"

paths:
  skills: "skills"
  blueprints: "blueprints"
  data: "data"
  logs: "logs"

logging:
  level: "INFO"
  format: "console"
  file: null

skills: {}
```

The `skills/` directory is empty — time to create your first skill.

---

## Part 2: Building Your First Skill

### 2.1 Anatomy of a Skill

Every NeuroCore skill is a Python class that:

1. Extends `Skill` (which extends FlowEngine's `BaseComponent`)
2. Defines a `skill_meta` class attribute (a `SkillMeta` instance)
3. Implements `process(context)` — the main logic

**SkillMeta fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Unique skill identifier |
| `version` | `str` | Yes | Semantic version |
| `description` | `str` | No | Human-readable description |
| `author` | `str` | No | Author or maintainer |
| `requires` | `list[str]` | No | pip dependencies |
| `provides` | `list[str]` | No | Context keys this skill produces |
| `consumes` | `list[str]` | No | Context keys this skill reads |
| `config_schema` | `dict` | No | JSON Schema for config validation |
| `tags` | `list[str]` | No | Categorization tags |

**Skill lifecycle:**

| Method | Frequency | Purpose |
|--------|-----------|---------|
| `__init__(name)` | Once | Instance creation |
| `init(config)` | Once | Store config, connect to services |
| `setup(context)` | Per run | Per-run preparation |
| `process(context)` | Per run | **Main logic** (must implement) |
| `teardown(context)` | Per run | Cleanup, close connections |
| `validate_config()` | After init | Return `list[str]` of errors |
| `health_check()` | On demand | Return `bool` |

### 2.2 Create a Greeting Skill

Create `skills/greet.py`:

```python
"""Greeting skill — says hello with configurable style."""

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class GreetSkill(Skill):
    """Greets the user by name with a configurable style."""

    skill_meta = SkillMeta(
        name="greet",
        version="1.0.0",
        description="Greets the user by name",
        provides=["greeting"],
        consumes=["user_name"],
        config_schema={
            "properties": {
                "style": {
                    "type": "string",
                    "description": "Greeting style: formal or casual",
                },
            },
        },
    )

    def process(self, context: FlowContext) -> FlowContext:
        name = context.get("user_name", "World")
        style = self.config.get("style", "casual")

        if style == "formal":
            greeting = f"Good day, {name}. How may I assist you?"
        else:
            greeting = f"Hey {name}! What's up?"

        context.set("greeting", greeting)
        return context
```

### 2.3 Write a Blueprint

Create `blueprints/greet.flow.yaml`:

```yaml
name: greet-flow
description: "Greet the user"

components:
  - name: greeter
    type: greet
    config:
      style: casual

flow:
  type: sequential
  steps:
    - component: greeter
```

### 2.4 Run It

```bash
# Execute the blueprint
neurocore run blueprints/greet.flow.yaml --data user_name=Alice

# Output:
# ╭─ Result ──────────────────────╮
# │ {                             │
# │   "user_name": "Alice",      │
# │   "greeting": "Hey Alice!..."│
# │ }                             │
# ╰───────────────────────────────╯
```

Discover your skill:

```bash
# List all discovered skills
neurocore skill list

# Show detailed info
neurocore skill info greet
```

### 2.5 Add Config Validation

Enhance the skill to require a `style` config key:

```python
    skill_meta = SkillMeta(
        name="greet",
        version="1.0.0",
        description="Greets the user by name",
        provides=["greeting"],
        consumes=["user_name"],
        config_schema={
            "properties": {
                "style": {"type": "string"},
            },
            "required": ["style"],   # Now required
        },
    )
```

If you remove `style` from the blueprint config, the executor will raise a `BlueprintError` with a validation message like: `Missing required config key: 'style'`.

You can also add custom validation by overriding `validate_config()`:

```python
    def validate_config(self) -> list[str]:
        errors = super().validate_config()  # Run JSON Schema checks first
        style = self.config.get("style", "")
        if style not in ("formal", "casual"):
            errors.append(f"Invalid style '{style}': must be 'formal' or 'casual'")
        return errors
```

### 2.6 Test Your Skill

Create `tests/test_greet.py`:

```python
"""Tests for the greeting skill."""

from flowengine import FlowContext

from skills.greet import GreetSkill


class TestGreetSkill:
    """Test suite for GreetSkill."""

    def test_casual_greeting(self):
        skill = GreetSkill()
        skill.init({"style": "casual"})

        ctx = FlowContext()
        ctx.set("user_name", "Alice")

        result = skill.process(ctx)

        assert "Alice" in result.get("greeting")
        assert "Hey" in result.get("greeting")

    def test_formal_greeting(self):
        skill = GreetSkill()
        skill.init({"style": "formal"})

        ctx = FlowContext()
        ctx.set("user_name", "Dr. Smith")

        result = skill.process(ctx)

        assert "Dr. Smith" in result.get("greeting")
        assert "Good day" in result.get("greeting")

    def test_default_name(self):
        skill = GreetSkill()
        skill.init({"style": "casual"})

        ctx = FlowContext()
        result = skill.process(ctx)

        assert "World" in result.get("greeting")

    def test_config_validation_valid(self):
        skill = GreetSkill()
        skill.init({"style": "formal"})
        errors = skill.validate_config()
        assert errors == []

    def test_config_validation_missing_style(self):
        skill = GreetSkill()
        skill.init({})
        errors = skill.validate_config()
        assert any("style" in e for e in errors)
```

Run:

```bash
pytest tests/test_greet.py -v
```

---

## Part 3: Configuration Deep Dive

### 3.1 neurocore.yaml Reference

```yaml
# Project metadata
project:
  name: "my-agent"          # Project identifier
  version: "0.1.0"          # Project version

# Paths (relative to project root, resolved at load time)
paths:
  skills: "skills"          # Local skills directory (auto-discovered)
  blueprints: "blueprints"  # Flow definition files
  data: "data"              # Persistent data directory
  logs: "logs"              # Log output directory

# Logging configuration
logging:
  level: "INFO"             # DEBUG | INFO | WARNING | ERROR
  format: "console"         # console (colored, dev) | json (structured, production)
  file: null                # Optional: log file path (always JSON format)

# Per-skill configuration (passed to skill.init())
skills:
  greet:
    style: "casual"
  neuroweave:
    mode: "context"
    llm_provider: "anthropic"
    llm_model: "claude-haiku-4-5-20251001"
```

### 3.2 Environment Variables and .env

Override any config value using the `NEUROCORE_` prefix with double underscores for nesting:

```bash
# .env file (or shell environment)
NEUROCORE_LOGGING__LEVEL=DEBUG
NEUROCORE_LOGGING__FORMAT=json
NEUROCORE_PROJECT__NAME=production-agent
```

### 3.3 Config Priority

| Priority | Source | Example |
|----------|--------|---------|
| 1 (highest) | Environment variables | `NEUROCORE_LOGGING__LEVEL=DEBUG` |
| 2 | `.env` file | Same syntax, loaded from project root |
| 3 | `neurocore.yaml` | `logging: level: INFO` |
| 4 (lowest) | Built-in defaults | `INFO`, `console`, etc. |

### 3.4 Per-Skill Configuration

The `skills:` section in `neurocore.yaml` provides base configuration for each skill by name:

```yaml
skills:
  greet:
    style: "formal"     # Base config for any "greet" skill instance
  llm-chat:
    provider: "anthropic"
    model: "claude-haiku-4-5-20251001"
```

Access in your skill via `self.config`:

```python
def process(self, context):
    style = self.config.get("style", "casual")
    # ...
```

### 3.5 Config Merging

When a blueprint specifies component-level config, it merges with the neurocore.yaml base config. **Blueprint values win** (shallow merge):

```yaml
# neurocore.yaml
skills:
  greet:
    style: "formal"
    language: "en"
```

```yaml
# blueprint.flow.yaml
components:
  - name: greeter
    type: greet
    config:
      style: "casual"     # Overrides "formal"
      # language not set — inherits "en" from neurocore.yaml
```

| Key | neurocore.yaml (base) | Blueprint (overlay) | Merged result |
|-----|----------------------|---------------------|---------------|
| `style` | `"formal"` | `"casual"` | `"casual"` |
| `language` | `"en"` | _(not set)_ | `"en"` |

### 3.6 Using Config Programmatically

```python
from pathlib import Path

from neurocore.config.loader import load_config

# Auto-detect project root (walks up from cwd looking for neurocore.yaml)
config = load_config()

# Or specify explicitly
config = load_config(project_root=Path("/path/to/project"))

# Access config
print(config.project.name)           # "my-agent"
print(config.logging.level)          # LogLevel.INFO
print(config.skills_dir)             # Path("/path/to/project/skills")
print(config.get_skill_config("greet"))  # {"style": "formal", "language": "en"}
```

---

## Part 4: Blueprints and Flow Orchestration

Blueprints are YAML files that wire skills together into executable workflows. NeuroCore supports three flow types: sequential, conditional, and graph.

### 4.1 Sequential Flows

All steps execute in order. The most common pattern.

Create two skills for a text processing pipeline:

`skills/prep.py`:

```python
from flowengine import FlowContext
from neurocore import Skill, SkillMeta


class PrepSkill(Skill):
    skill_meta = SkillMeta(
        name="prep",
        version="1.0.0",
        description="Prepares text for processing",
        provides=["prepared"],
        consumes=["raw_text"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        raw = context.get("raw_text", "")
        cleaned = raw.strip().lower()
        context.set("prepared", cleaned)
        return context
```

`skills/format_output.py`:

```python
from flowengine import FlowContext
from neurocore import Skill, SkillMeta


class FormatOutputSkill(Skill):
    skill_meta = SkillMeta(
        name="format-output",
        version="1.0.0",
        description="Formats processed text for display",
        provides=["formatted"],
        consumes=["prepared"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        prepared = context.get("prepared", "")
        word_count = len(prepared.split())
        context.set("formatted", f"[{word_count} words] {prepared}")
        return context
```

`blueprints/pipeline.flow.yaml`:

```yaml
name: text-pipeline
description: "Clean text, then format for display"

components:
  - name: cleaner
    type: prep
  - name: formatter
    type: format-output

flow:
  type: sequential
  steps:
    - component: cleaner
    - component: formatter
```

Run:

```bash
neurocore run blueprints/pipeline.flow.yaml --data raw_text="  Hello World  "
```

Data flows through: `raw_text` → prep → `prepared` → format-output → `formatted`.

### 4.2 Conditional Flows

Conditional flows use first-match branching — only the first step whose condition evaluates to `True` executes (like a switch/case):

`blueprints/conditional.flow.yaml`:

```yaml
name: language-router
description: "Route to different handlers based on language"

components:
  - name: english-handler
    type: greet
    config:
      style: "casual"
  - name: formal-handler
    type: greet
    config:
      style: "formal"

flow:
  type: conditional
  steps:
    - component: english-handler
      condition: "context.get('language') == 'en'"
    - component: formal-handler
      condition: "context.get('language') == 'de'"
```

```bash
neurocore run blueprints/conditional.flow.yaml \
  --data language=en --data user_name=Alice
```

Conditions are Python expressions evaluated against the `FlowContext`. Only the **first** matching step runs.

### 4.3 Graph Flows (DAG)

Graph flows use nodes and edges for complex orchestration. Nodes execute in topological order, and edges define data flow between them.

```
  ┌──────────┐
  │  fetch    │
  └────┬─────┘
       │
  ┌────▼─────┐
  │ transform │
  └────┬─────┘
       │
  ┌────▼─────┐
  │  store    │
  └──────────┘
```

`blueprints/dag-pipeline.flow.yaml`:

```yaml
name: dag-pipeline
description: "Fetch → Transform → Store using graph flow"

components:
  - name: fetcher
    type: prep
  - name: transformer
    type: format-output
  - name: storer
    type: greet
    config:
      style: "formal"

flow:
  type: graph
  nodes:
    - id: fetch
      component: fetcher
    - id: transform
      component: transformer
    - id: store
      component: storer
  edges:
    - source: fetch
      target: transform
    - source: transform
      target: store
```

**Port-based routing** allows nodes to select which edge to follow:

```python
def process(self, context: FlowContext) -> FlowContext:
    if context.get("score", 0) > 0.8:
        context.set_port("high_quality")
    else:
        context.set_port("needs_review")
    return context
```

```yaml
edges:
  - source: evaluator
    target: publish
    port: high_quality
  - source: evaluator
    target: reviewer
    port: needs_review
```

### 4.4 Flow Settings

Control execution behavior with settings:

```yaml
flow:
  type: sequential
  settings:
    fail_fast: true          # Stop on first error (default: true)
    timeout_seconds: 300     # Max execution time in seconds (default: 300)
  steps:
    - component: step1
      on_error: fail         # fail | skip | continue (default: fail)
    - component: step2
      on_error: skip         # Skip this step if it errors
    - component: step3
      on_error: continue     # Continue even if this step errors
```

| Setting | Default | Description |
|---------|---------|-------------|
| `fail_fast` | `true` | Stop flow on first error |
| `timeout_seconds` | `300` | Maximum execution time |
| `on_error` (per step) | `"fail"` | `fail` = stop, `skip` = skip step, `continue` = proceed |

For graph flows with cycles:

```yaml
flow:
  type: graph
  settings:
    max_iterations: 10        # Max loop iterations (default: 10)
    on_max_iterations: "exit"  # fail | exit | warn (default: fail)
  nodes:
    - id: worker
      component: my-worker
      max_visits: 5            # Per-node iteration limit
```

### 4.5 Blueprint Validation

Validate a blueprint without running it:

```bash
neurocore validate blueprints/pipeline.flow.yaml
```

Three-stage validation:

1. **YAML parsing** — is the file valid YAML?
2. **Structure validation** — does it have `name`, `components`, `flow` with correct types?
3. **Skill references** — do all `type:` values match registered skills?

```
Validating: blueprints/pipeline.flow.yaml

  ✓ YAML parsing OK
  ✓ Blueprint structure valid
    Name: text-pipeline  |  Components: 2  |  Flow: sequential
  ✓ All skill references resolved

Blueprint is valid.
```

---

## Part 5: Adding NeuroWeave (Knowledge Graph Memory)

[NeuroWeave](https://github.com/alexh-scrt/neuroweave) is a real-time knowledge graph memory for agentic AI. The `neurocore-skill-neuroweave` package wraps it as a NeuroCore skill.

### 5.1 Install

```bash
pip install neurocore-skill-neuroweave
```

Verify:

```bash
neurocore skill list
# Should show "neuroweave" in the table

neurocore skill info neuroweave
```

The skill is discovered automatically via Python entry points — no need to copy files into `skills/`.

### 5.2 NeuroWeave Modes

| Mode | Consumes | Provides | Description |
|------|----------|----------|-------------|
| `process` | `message` | `neuroweave_result` | Extract knowledge from text into the graph |
| `query` | `query` | `neuroweave_result` | Search the knowledge graph |
| `context` | `message` | `neuroweave_result`, `neuroweave_context` | Extract + retrieve in one step (default) |

### 5.3 LLM Provider Setup

NeuroWeave uses an LLM for knowledge extraction. Configure the provider:

**Anthropic:**

```yaml
# neurocore.yaml
skills:
  neuroweave:
    mode: "context"
    llm_provider: "anthropic"
    llm_model: "claude-haiku-4-5-20251001"
```

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
```

**OpenAI:**

```yaml
skills:
  neuroweave:
    mode: "context"
    llm_provider: "openai"
    llm_model: "gpt-4o-mini"
```

```bash
# .env
OPENAI_API_KEY=sk-...
```

**Mock (no API key needed — for testing):**

```yaml
skills:
  neuroweave:
    mode: "context"
    llm_provider: "mock"
```

### 5.4 Knowledge Extraction Pipeline

`blueprints/extract.flow.yaml`:

```yaml
name: knowledge-extraction
description: "Extract knowledge from a message"

components:
  - name: memory
    type: neuroweave
    config:
      mode: "process"

flow:
  type: sequential
  steps:
    - component: memory
```

```bash
neurocore run blueprints/extract.flow.yaml \
  --data message="Marie Curie discovered radium in 1898"
```

### 5.5 Querying the Knowledge Graph

`blueprints/query.flow.yaml`:

```yaml
name: knowledge-query
description: "Query the knowledge graph"

components:
  - name: memory
    type: neuroweave
    config:
      mode: "query"

flow:
  type: sequential
  steps:
    - component: memory
```

```bash
neurocore run blueprints/query.flow.yaml \
  --data query="What did Marie Curie discover?"
```

---

## Part 6: Chat App — Personal Experiences Collector

Let's build a complete chat application that remembers your personal experiences using NeuroWeave as a knowledge graph memory.

### 6.1 Design

```
User Input
    │
    ▼
┌──────────────┐
│ ChatInputSkill│  Normalizes user message
└──────┬───────┘
       │ message
       ▼
┌──────────────┐
│  NeuroWeave  │  Extracts knowledge + retrieves memories
│ (context mode)│
└──────┬───────┘
       │ neuroweave_result, neuroweave_context
       ▼
┌──────────────┐
│  Response    │  Formats response with relevant memories
│  Formatter   │
└──────┬───────┘
       │ response
       ▼
   Print Output
```

### 6.2 Project Setup

```bash
neurocore init experience-collector
cd experience-collector
pip install neurocore-skill-neuroweave
cp .env.example .env
```

Edit `.env` with your API key:

```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 6.3 ChatInputSkill

`skills/chat_input.py`:

```python
"""Chat input skill — normalizes user input for the pipeline."""

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class ChatInputSkill(Skill):
    skill_meta = SkillMeta(
        name="chat-input",
        version="1.0.0",
        description="Normalizes user chat input",
        provides=["message", "timestamp"],
        consumes=["user_message"],
        tags=["chat", "input"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        import time

        user_message = context.get("user_message", "")
        # Pass the message through for NeuroWeave
        context.set("message", user_message.strip())
        context.set("timestamp", time.strftime("%Y-%m-%d %H:%M:%S"))
        return context
```

### 6.4 ResponseFormatterSkill

`skills/response_formatter.py`:

```python
"""Response formatter — combines extraction results with retrieved memories."""

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class ResponseFormatterSkill(Skill):
    skill_meta = SkillMeta(
        name="response-formatter",
        version="1.0.0",
        description="Formats response with memories",
        provides=["response"],
        consumes=["message", "neuroweave_result", "neuroweave_context"],
        tags=["chat", "output"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        message = context.get("message", "")
        nw_result = context.get("neuroweave_result")
        nw_context = context.get("neuroweave_context")

        parts = [f"You said: {message}", ""]

        # Show what was extracted
        if nw_result:
            result_dict = (
                nw_result if isinstance(nw_result, dict) else nw_result.to_dict()
                if hasattr(nw_result, "to_dict") else {}
            )
            entities = result_dict.get("entities_extracted", 0)
            relations = result_dict.get("relations_extracted", 0)
            if entities or relations:
                parts.append(
                    f"Noted: {entities} entities, {relations} relations extracted."
                )

        # Show related memories
        if nw_context:
            context_dict = (
                nw_context if isinstance(nw_context, dict) else nw_context.to_dict()
                if hasattr(nw_context, "to_dict") else {}
            )
            nodes = context_dict.get("nodes", [])
            if nodes:
                parts.append("Related memories:")
                for node in nodes[:5]:  # Show top 5
                    label = (
                        node.get("label", str(node))
                        if isinstance(node, dict)
                        else str(node)
                    )
                    parts.append(f"  - {label}")

        if len(parts) == 2:
            parts.append("(No related memories yet — keep chatting!)")

        context.set("response", "\n".join(parts))
        return context
```

### 6.5 Configure

`neurocore.yaml`:

```yaml
project:
  name: "experience-collector"
  version: "0.1.0"

paths:
  skills: "skills"
  blueprints: "blueprints"
  data: "data"
  logs: "logs"

logging:
  level: "INFO"
  format: "console"

skills:
  neuroweave:
    mode: "context"
    llm_provider: "anthropic"
    llm_model: "claude-haiku-4-5-20251001"
    enable_visualization: false
```

### 6.6 Blueprint

`blueprints/chat.flow.yaml`:

```yaml
name: experience-chat
description: "Chat pipeline with experience memory"

components:
  - name: input
    type: chat-input
  - name: memory
    type: neuroweave
  - name: formatter
    type: response-formatter

flow:
  type: sequential
  steps:
    - component: input
    - component: memory
    - component: formatter
```

### 6.7 Chat Loop

`chat.py`:

```python
#!/usr/bin/env python3
"""Personal Experiences Collector — interactive chat with memory."""

from pathlib import Path

from neurocore.errors import ExecutionError, NeuroCoreError
from neurocore.runtime.executor import load_and_run


def main():
    project_root = Path(__file__).parent
    blueprint = project_root / "blueprints" / "chat.flow.yaml"

    print("Experience Collector")
    print("Tell me about your experiences. I'll remember them!")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input or user_input.lower() == "quit":
            print("Goodbye!")
            break

        try:
            result = load_and_run(
                blueprint_path=blueprint,
                project_root=project_root,
                initial_data={"user_message": user_input},
            )
            response = result.get("response", "")
            print(f"\nAssistant: {response}\n")

        except ExecutionError as e:
            print(f"\n[Error] Execution failed: {e}\n")
        except NeuroCoreError as e:
            print(f"\n[Error] {e}\n")


if __name__ == "__main__":
    main()
```

### 6.8 Run It

```bash
python chat.py
```

Example session:

```
Experience Collector
Tell me about your experiences. I'll remember them!
Type 'quit' to exit.

You: My wife Lena and I went to Tokyo last summer
Assistant: You said: My wife Lena and I went to Tokyo last summer

Noted: 3 entities, 2 relations extracted.
(No related memories yet — keep chatting!)

You: We loved the sushi at Tsukiji market
Assistant: You said: We loved the sushi at Tsukiji market

Noted: 2 entities, 1 relations extracted.
Related memories:
  - Lena (Person)
  - Tokyo (Location)
```

You can also run individual messages from the CLI:

```bash
neurocore run blueprints/chat.flow.yaml \
  --data user_message="I learned to surf in Bali"
```

---

## Part 7: Multi-Provider LLM Chat Agent

Build a single skill that can talk to OpenAI, Anthropic, or a local Ollama deployment — switched by configuration.

### 7.1 Design

NeuroCore deliberately has no built-in LLM abstraction. Skills own their provider logic. This pattern demonstrates a config-driven provider selection:

```
neurocore.yaml                    Blueprint config (overlay)
  skills.llm-chat:                  config:
    provider: "anthropic"     ───►    provider: "openai"   (wins)
    model: "claude-haiku"             model: "gpt-4o-mini" (wins)
    api_key: "sk-ant-..."
```

### 7.2 LLMChatSkill

`skills/llm_chat.py`:

```python
"""LLM Chat skill — multi-provider chat with OpenAI, Anthropic, and Ollama."""

from __future__ import annotations

import asyncio
from typing import Any

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class LLMChatSkill(Skill):
    """Chat skill supporting multiple LLM providers."""

    skill_meta = SkillMeta(
        name="llm-chat",
        version="1.0.0",
        description="Multi-provider LLM chat (OpenAI, Anthropic, Ollama)",
        author="Tutorial",
        provides=["llm_response"],
        consumes=["prompt"],
        config_schema={
            "properties": {
                "provider": {
                    "type": "string",
                    "description": "LLM provider: openai, anthropic, ollama, or mock",
                },
                "model": {
                    "type": "string",
                    "description": "Model identifier",
                },
                "api_key": {
                    "type": "string",
                    "description": "API key (not needed for ollama/mock)",
                },
                "base_url": {
                    "type": "string",
                    "description": "Base URL for Ollama (default: http://localhost:11434)",
                },
                "system_prompt": {
                    "type": "string",
                    "description": "System prompt for the conversation",
                },
            },
            "required": ["provider", "model"],
        },
        tags=["llm", "chat", "openai", "anthropic", "ollama"],
    )

    def init(self, config: dict[str, Any]) -> None:
        super().init(config)
        self._provider = config["provider"]
        self._model = config["model"]
        self._api_key = config.get("api_key", "")
        self._base_url = config.get("base_url", "http://localhost:11434")
        self._system_prompt = config.get(
            "system_prompt", "You are a helpful assistant."
        )

    def process(self, context: FlowContext) -> FlowContext:
        prompt = context.get("prompt", "")
        if not prompt:
            context.set("llm_response", "[Error: no prompt provided]")
            return context

        if self._provider == "openai":
            response = self._call_openai(prompt)
        elif self._provider == "anthropic":
            response = self._call_anthropic(prompt)
        elif self._provider == "ollama":
            response = self._call_ollama(prompt)
        elif self._provider == "mock":
            response = f"[Mock LLM] Echo: {prompt}"
        else:
            response = f"[Error: unknown provider '{self._provider}']"

        context.set("llm_response", response)
        return context

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI Chat Completions API."""
        from openai import OpenAI

        client = OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic Messages API."""
        import anthropic

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=self._system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama REST API."""
        import httpx

        response = httpx.post(
            f"{self._base_url}/api/chat",
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def health_check(self) -> bool:
        """Check if the LLM provider is reachable."""
        if self._provider == "mock":
            return True
        if self._provider == "ollama":
            try:
                import httpx

                r = httpx.get(f"{self._base_url}/api/tags", timeout=5.0)
                return r.status_code == 200
            except Exception:
                return False
        return self.is_initialized
```

### 7.3 Blueprints per Provider

`blueprints/chat-openai.flow.yaml`:

```yaml
name: chat-openai
description: "Chat using OpenAI GPT"

components:
  - name: llm
    type: llm-chat
    config:
      provider: "openai"
      model: "gpt-4o-mini"

flow:
  type: sequential
  steps:
    - component: llm
```

`blueprints/chat-anthropic.flow.yaml`:

```yaml
name: chat-anthropic
description: "Chat using Anthropic Claude"

components:
  - name: llm
    type: llm-chat
    config:
      provider: "anthropic"
      model: "claude-haiku-4-5-20251001"

flow:
  type: sequential
  steps:
    - component: llm
```

`blueprints/chat-ollama.flow.yaml`:

```yaml
name: chat-ollama
description: "Chat using local Ollama"

components:
  - name: llm
    type: llm-chat
    config:
      provider: "ollama"
      model: "llama3.2"
      base_url: "http://localhost:11434"

flow:
  type: sequential
  steps:
    - component: llm
```

### 7.4 Configure and Run

Set API keys in `neurocore.yaml` or `.env`:

```yaml
# neurocore.yaml
skills:
  llm-chat:
    api_key: ""  # Override via .env for security
    system_prompt: "You are a helpful, concise assistant."
```

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

Run with each provider:

```bash
# OpenAI
neurocore run blueprints/chat-openai.flow.yaml \
  --data prompt="Explain quantum computing in 2 sentences"

# Anthropic
neurocore run blueprints/chat-anthropic.flow.yaml \
  --data prompt="Explain quantum computing in 2 sentences"

# Ollama (ensure ollama serve is running)
neurocore run blueprints/chat-ollama.flow.yaml \
  --data prompt="Explain quantum computing in 2 sentences"

# Mock (no API key needed)
neurocore run blueprints/chat-openai.flow.yaml \
  --data prompt="Hello" --data provider=mock
```

### 7.5 Switching Providers via Environment

Override the provider at runtime without changing files:

```bash
# Switch to OpenAI for this run
NEUROCORE_SKILLS__LLM_CHAT__PROVIDER=openai \
NEUROCORE_SKILLS__LLM_CHAT__MODEL=gpt-4o-mini \
  neurocore run blueprints/chat-anthropic.flow.yaml \
    --data prompt="Hello"
```

### 7.6 Testing with Mock

`tests/test_llm_chat.py`:

```python
"""Tests for the LLM chat skill."""

from flowengine import FlowContext

from skills.llm_chat import LLMChatSkill


class TestLLMChatSkill:
    def test_mock_provider(self):
        skill = LLMChatSkill()
        skill.init({"provider": "mock", "model": "test"})

        ctx = FlowContext()
        ctx.set("prompt", "Hello world")
        result = skill.process(ctx)

        assert "Hello world" in result.get("llm_response")
        assert "Mock" in result.get("llm_response")

    def test_empty_prompt(self):
        skill = LLMChatSkill()
        skill.init({"provider": "mock", "model": "test"})

        ctx = FlowContext()
        result = skill.process(ctx)

        assert "Error" in result.get("llm_response")

    def test_unknown_provider(self):
        skill = LLMChatSkill()
        skill.init({"provider": "unknown", "model": "test"})

        ctx = FlowContext()
        ctx.set("prompt", "Hello")
        result = skill.process(ctx)

        assert "unknown" in result.get("llm_response").lower()

    def test_config_validation(self):
        skill = LLMChatSkill()
        skill.init({})
        errors = skill.validate_config()
        assert any("provider" in e for e in errors)

    def test_health_check_mock(self):
        skill = LLMChatSkill()
        skill.init({"provider": "mock", "model": "test"})
        assert skill.health_check() is True
```

---

## Part 8: Multi-Agent Parallel Architecture

Build a research pipeline where a coordinator dispatches tasks to multiple worker agents, then merges their results.

### 8.1 Design

```
                    ┌──────────────┐
                    │ Coordinator  │  Splits topic into sub-tasks
                    └──────┬───────┘
                      ┌────┼────┐
                      │    │    │
                      ▼    ▼    ▼
               ┌──────┐ ┌──────┐ ┌──────┐
               │ Web  │ │ Acad │ │Social│  Independent workers
               │Rsrch │ │Rsrch │ │Rsrch │
               └──┬───┘ └──┬───┘ └──┬───┘
                  │    │    │
                  └────┼────┘
                       ▼
                ┌──────────────┐
                │   Merger     │  Aggregates all results
                └──────────────┘
```

> **Note:** In v0.1.0, FlowEngine executes graph nodes in topological order
> (not truly concurrent threads). Workers are logically independent — they
> don't depend on each other's output — so the graph executor runs them in
> sequence but the architecture is designed for future parallel execution.

### 8.2 Skills

`skills/coordinator.py`:

```python
"""Coordinator skill — splits a research topic into sub-tasks."""

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class CoordinatorSkill(Skill):
    skill_meta = SkillMeta(
        name="coordinator",
        version="1.0.0",
        description="Splits research topic into sub-tasks for workers",
        provides=["task_web", "task_academic", "task_social"],
        consumes=["research_topic"],
        tags=["orchestration"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        topic = context.get("research_topic", "")

        # Split the topic into specialized sub-tasks
        context.set("task_web", f"Search the web for recent news about: {topic}")
        context.set("task_academic", f"Find academic papers about: {topic}")
        context.set("task_social", f"Find social media discussions about: {topic}")

        return context
```

`skills/web_researcher.py`:

```python
"""Web researcher — searches the web for information."""

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class WebResearcherSkill(Skill):
    skill_meta = SkillMeta(
        name="web-researcher",
        version="1.0.0",
        description="Researches a topic on the web",
        provides=["result_web"],
        consumes=["task_web"],
        tags=["research", "web"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        task = context.get("task_web", "")

        # In production, this would call a web search API
        result = {
            "source": "web",
            "task": task,
            "findings": [
                f"Web finding 1 for: {task}",
                f"Web finding 2 for: {task}",
            ],
            "confidence": 0.85,
        }

        context.set("result_web", result)
        return context
```

`skills/academic_researcher.py`:

```python
"""Academic researcher — searches academic databases."""

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class AcademicResearcherSkill(Skill):
    skill_meta = SkillMeta(
        name="academic-researcher",
        version="1.0.0",
        description="Researches academic papers on a topic",
        provides=["result_academic"],
        consumes=["task_academic"],
        tags=["research", "academic"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        task = context.get("task_academic", "")

        result = {
            "source": "academic",
            "task": task,
            "findings": [
                f"Paper: 'A Survey of {task}' (2024)",
                f"Paper: 'Advances in {task}' (2025)",
            ],
            "confidence": 0.92,
        }

        context.set("result_academic", result)
        return context
```

`skills/social_researcher.py`:

```python
"""Social researcher — searches social media discussions."""

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class SocialResearcherSkill(Skill):
    skill_meta = SkillMeta(
        name="social-researcher",
        version="1.0.0",
        description="Researches social media discussions",
        provides=["result_social"],
        consumes=["task_social"],
        tags=["research", "social"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        task = context.get("task_social", "")

        result = {
            "source": "social",
            "task": task,
            "findings": [
                f"Thread: Discussion about {task} (Reddit)",
                f"Post: Expert opinion on {task} (Twitter/X)",
            ],
            "confidence": 0.70,
        }

        context.set("result_social", result)
        return context
```

`skills/merger.py`:

```python
"""Merger skill — aggregates results from all workers."""

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class MergerSkill(Skill):
    skill_meta = SkillMeta(
        name="merger",
        version="1.0.0",
        description="Merges research results from all workers",
        provides=["final_report"],
        consumes=["result_web", "result_academic", "result_social"],
        tags=["orchestration"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        results = []

        for source in ["result_web", "result_academic", "result_social"]:
            result = context.get(source)
            if result:
                result_dict = result if isinstance(result, dict) else {}
                results.append(result_dict)

        # Aggregate findings
        all_findings = []
        avg_confidence = 0.0

        for r in results:
            all_findings.extend(r.get("findings", []))
            avg_confidence += r.get("confidence", 0.0)

        if results:
            avg_confidence /= len(results)

        report = {
            "topic": context.get("research_topic", ""),
            "sources_consulted": len(results),
            "total_findings": len(all_findings),
            "average_confidence": round(avg_confidence, 2),
            "findings": all_findings,
        }

        context.set("final_report", report)
        return context
```

### 8.3 Blueprint: Graph Flow

`blueprints/research-pipeline.flow.yaml`:

```yaml
name: multi-agent-research
description: "Parallel research pipeline with coordinator and workers"

components:
  - name: coordinator
    type: coordinator
  - name: web-worker
    type: web-researcher
  - name: academic-worker
    type: academic-researcher
  - name: social-worker
    type: social-researcher
  - name: merger
    type: merger

flow:
  type: graph
  settings:
    fail_fast: false
    timeout_seconds: 600
  nodes:
    - id: split
      component: coordinator
    - id: web
      component: web-worker
      on_error: skip
    - id: academic
      component: academic-worker
      on_error: skip
    - id: social
      component: social-worker
      on_error: skip
    - id: merge
      component: merger
  edges:
    # Coordinator dispatches to all workers
    - source: split
      target: web
    - source: split
      target: academic
    - source: split
      target: social
    # All workers report to merger
    - source: web
      target: merge
    - source: academic
      target: merge
    - source: social
      target: merge
```

### 8.4 Run It

```bash
neurocore run blueprints/research-pipeline.flow.yaml \
  --data research_topic="quantum computing" --json
```

Output (JSON):

```json
{
  "research_topic": "quantum computing",
  "task_web": "Search the web for recent news about: quantum computing",
  "task_academic": "Find academic papers about: quantum computing",
  "task_social": "Find social media discussions about: quantum computing",
  "result_web": {"source": "web", "findings": ["..."], "confidence": 0.85},
  "result_academic": {"source": "academic", "findings": ["..."], "confidence": 0.92},
  "result_social": {"source": "social", "findings": ["..."], "confidence": 0.70},
  "final_report": {
    "topic": "quantum computing",
    "sources_consulted": 3,
    "total_findings": 6,
    "average_confidence": 0.82,
    "findings": ["..."]
  }
}
```

### 8.5 Cyclic Retry Pattern

Add quality checking with a retry loop. If the merger determines the results are insufficient, route back to a worker for deeper research:

`skills/quality_checker.py`:

```python
"""Quality checker — evaluates research quality and routes for retry."""

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class QualityCheckerSkill(Skill):
    skill_meta = SkillMeta(
        name="quality-checker",
        version="1.0.0",
        description="Checks research quality and triggers retry if needed",
        provides=["quality_passed"],
        consumes=["final_report"],
        config_schema={
            "properties": {
                "min_findings": {"type": "integer"},
                "min_confidence": {"type": "number"},
            },
        },
    )

    def process(self, context: FlowContext) -> FlowContext:
        report = context.get("final_report", {})
        report_dict = report if isinstance(report, dict) else {}

        min_findings = self.config.get("min_findings", 5)
        min_confidence = self.config.get("min_confidence", 0.8)

        total = report_dict.get("total_findings", 0)
        confidence = report_dict.get("average_confidence", 0.0)

        passed = total >= min_findings and confidence >= min_confidence
        context.set("quality_passed", passed)

        if passed:
            context.set_port("done")
        else:
            context.set_port("retry")

        return context
```

`blueprints/research-with-retry.flow.yaml`:

```yaml
name: research-with-retry
description: "Research pipeline with quality checking and retry"

components:
  - name: coordinator
    type: coordinator
  - name: web-worker
    type: web-researcher
  - name: merger
    type: merger
  - name: checker
    type: quality-checker
    config:
      min_findings: 5
      min_confidence: 0.8

flow:
  type: graph
  settings:
    max_iterations: 3
    on_max_iterations: "exit"
  nodes:
    - id: split
      component: coordinator
    - id: web
      component: web-worker
      max_visits: 3
    - id: merge
      component: merger
    - id: check
      component: checker
  edges:
    - source: split
      target: web
    - source: web
      target: merge
    - source: merge
      target: check
    - source: check
      target: web
      port: retry
```

When the quality checker signals `retry`, the flow loops back to the web worker (up to `max_iterations` times).

---

## Part 9: Packaging and Distribution

### 9.1 Skill Package Structure

To distribute a skill as a pip-installable package:

```
neurocore-skill-myskill/
├── pyproject.toml
├── README.md
├── src/
│   └── neurocore_skill_myskill/
│       ├── __init__.py
│       └── skill.py
└── tests/
    └── test_skill.py
```

### 9.2 pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "neurocore-skill-myskill"
version = "0.1.0"
description = "My custom NeuroCore skill"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "neurocore>=0.1.0",
]

[project.entry-points."neurocore.skills"]
my-skill = "neurocore_skill_myskill:MySkill"

[tool.hatch.build.targets.wheel]
packages = ["src/neurocore_skill_myskill"]
```

The critical line is the entry point declaration. The key (`my-skill`) must match your `skill_meta.name`.

### 9.3 Package Files

`src/neurocore_skill_myskill/__init__.py`:

```python
"""My custom NeuroCore skill package."""

from neurocore_skill_myskill.skill import MySkill

__all__ = ["MySkill"]
```

`src/neurocore_skill_myskill/skill.py`:

```python
"""My custom skill implementation."""

from flowengine import FlowContext
from neurocore import Skill, SkillMeta


class MySkill(Skill):
    skill_meta = SkillMeta(
        name="my-skill",
        version="0.1.0",
        description="My distributed skill",
        requires=["some-dependency>=1.0"],
        provides=["my_output"],
        consumes=["my_input"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        value = context.get("my_input", "")
        context.set("my_output", f"Processed: {value}")
        return context
```

### 9.4 Install and Verify

```bash
# Install locally (editable)
pip install -e ./neurocore-skill-myskill

# Verify discovery
neurocore skill list
# Should show "my-skill" discovered via entry points

neurocore skill info my-skill
```

### 9.5 Publish to PyPI

```bash
# Install build tools
pip install build twine

# Build
cd neurocore-skill-myskill
python -m build

# Upload to Test PyPI first
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

### 9.6 Versioning

Follow semantic versioning for your skill package:

| Version bump | When |
|-------------|------|
| **Patch** (0.1.0 → 0.1.1) | Bug fixes, no API changes |
| **Minor** (0.1.0 → 0.2.0) | New features, backward compatible |
| **Major** (0.1.0 → 1.0.0) | Breaking changes to provides/consumes/config |

Pin your NeuroCore dependency range:

```toml
dependencies = [
    "neurocore>=0.1.0,<1.0.0",  # Compatible with 0.x releases
]
```

---

## Part 10: Deployment and Operations

### 10.1 Environment-Based Configuration

Use different `neurocore.yaml` settings per environment:

**Development:**

```yaml
logging:
  level: "DEBUG"
  format: "console"
  file: null

skills:
  neuroweave:
    llm_provider: "mock"    # No API key needed
```

**Staging:**

```yaml
logging:
  level: "INFO"
  format: "console"
  file: "logs/staging.log"

skills:
  neuroweave:
    llm_provider: "anthropic"
    llm_model: "claude-haiku-4-5-20251001"
```

**Production:**

```yaml
logging:
  level: "WARNING"
  format: "json"
  file: "logs/production.log"

skills:
  neuroweave:
    llm_provider: "anthropic"
    llm_model: "claude-sonnet-4-20250514"
```

Override per environment without changing files:

```bash
NEUROCORE_LOGGING__LEVEL=WARNING \
NEUROCORE_LOGGING__FORMAT=json \
  neurocore run blueprints/agent.flow.yaml
```

### 10.2 Structured Logging

In production, use JSON logging for machine-parseable output:

```yaml
logging:
  format: "json"
  file: "logs/app.log"
```

Console output (development):

```
2026-02-28 10:30:15 [info] skill.discovered  name=greet version=1.0.0
2026-02-28 10:30:15 [info] flow.started      blueprint=greet-flow
```

JSON output (production):

```json
{"event": "skill.discovered", "name": "greet", "version": "1.0.0", "timestamp": "2026-02-28T10:30:15Z", "level": "info"}
{"event": "flow.started", "blueprint": "greet-flow", "timestamp": "2026-02-28T10:30:15Z", "level": "info"}
```

Use the logger in your skills:

```python
from neurocore.logging.setup import get_logger

log = get_logger("my-skill")

class MySkill(Skill):
    # ...
    def process(self, context):
        log.info("processing.started", input_key="user_message")
        # ... do work ...
        log.info("processing.completed", result_size=len(result))
        return context
```

### 10.3 Error Handling

NeuroCore provides a structured error hierarchy:

```python
from neurocore.errors import (
    NeuroCoreError,     # Base — catch all framework errors
    ConfigError,        # Config loading/validation failure
    SkillError,         # Skill loading/discovery failure
    BlueprintError,     # Blueprint parsing/validation failure
    ExecutionError,     # Runtime execution failure
)
```

Pattern for production scripts:

```python
from pathlib import Path

from neurocore.errors import (
    BlueprintError,
    ConfigError,
    ExecutionError,
    NeuroCoreError,
)
from neurocore.runtime.executor import load_and_run


def run_safely(blueprint_path: Path, data: dict) -> dict | None:
    try:
        result = load_and_run(
            blueprint_path=blueprint_path,
            initial_data=data,
        )
        return result.to_dict()

    except ConfigError as e:
        print(f"Configuration error: {e}")
        print("Check your neurocore.yaml and .env files.")

    except BlueprintError as e:
        print(f"Blueprint error: {e}")
        print("Run: neurocore validate <blueprint> to diagnose.")

    except ExecutionError as e:
        print(f"Execution error: {e}")
        print("Check skill logs and error output.")

    except NeuroCoreError as e:
        print(f"Framework error: {e}")

    return None
```

### 10.4 Health Checks

Override `health_check()` in your skills to verify external dependencies:

```python
class DatabaseSkill(Skill):
    skill_meta = SkillMeta(name="database", version="1.0.0")

    def init(self, config):
        super().init(config)
        self._connection_string = config.get("connection_string", "")

    def health_check(self) -> bool:
        """Check database connectivity."""
        if not self.is_initialized:
            return False
        try:
            # Try a lightweight connection test
            import psycopg2

            conn = psycopg2.connect(self._connection_string)
            conn.close()
            return True
        except Exception:
            return False
```

Check health from the CLI:

```bash
neurocore skill info database
# Shows: Health: ✓ healthy (or ✗ unhealthy)
```

### 10.5 Docker Deployment

`Dockerfile`:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install dependencies first (cache layer)
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application
COPY neurocore.yaml .
COPY .env .
COPY skills/ skills/
COPY blueprints/ blueprints/
COPY data/ data/

# Create logs directory
RUN mkdir -p logs

# Default command
CMD ["neurocore", "run", "blueprints/agent.flow.yaml"]
```

`docker-compose.yaml`:

```yaml
version: "3.8"

services:
  agent:
    build: .
    environment:
      - NEUROCORE_LOGGING__LEVEL=INFO
      - NEUROCORE_LOGGING__FORMAT=json
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

Run:

```bash
# Build and start
docker compose up -d

# Run a specific blueprint
docker compose exec agent neurocore run blueprints/research.flow.yaml \
  --data research_topic="AI safety"

# View logs
docker compose logs agent
```

---

## Quick Reference

### CLI Commands

| Command | Description |
|---------|-------------|
| `neurocore init <name>` | Scaffold a new project |
| `neurocore run <blueprint>` | Execute a blueprint |
| `neurocore run <bp> --data K=V` | Pass initial data |
| `neurocore run <bp> --json` | JSON output |
| `neurocore run <bp> --verbose` | Verbose output |
| `neurocore skill list` | List discovered skills |
| `neurocore skill info <name>` | Show skill details |
| `neurocore validate <blueprint>` | Validate without running |
| `neurocore --version` | Show version |

### Python API

```python
from neurocore import Skill, SkillMeta          # Skill development
from neurocore.runtime.executor import (
    load_and_run,                                # High-level execution
    execute_blueprint,                           # Low-level execution
)
from neurocore.config.loader import load_config  # Config loading
from neurocore.skills.loader import discover_skills  # Skill discovery
from neurocore.logging.setup import get_logger   # Structured logging
from neurocore.errors import (                   # Error handling
    NeuroCoreError, ConfigError, SkillError,
    BlueprintError, ExecutionError,
)
```

### Blueprint YAML Format

```yaml
name: "flow-name"                # Required
description: "..."               # Optional
components:                      # Required (at least 1)
  - name: "instance-name"       # Unique per blueprint
    type: "skill-name"          # Registered skill name
    config: {}                  # Optional config overlay
flow:
  type: sequential              # sequential | conditional | graph
  settings: {}                  # Optional flow settings
  steps:                        # For sequential/conditional
    - component: "instance-name"
      condition: "expr"         # Optional (conditional only)
      on_error: "fail"          # fail | skip | continue
  # OR for graph:
  nodes:
    - id: "node-id"
      component: "instance-name"
      max_visits: 5             # Optional cycle limit
  edges:
    - source: "node-id"
      target: "node-id"
      port: "port-name"        # Optional port routing
```
