# NeuroCore

**Pluggable, YAML-driven framework for building agentic AI applications.**

NeuroCore is the *chassis* for agentic AI. It wires together workflow
orchestration, discoverable skills, structured configuration, and a
developer-friendly CLI — so you can focus on building intelligent agents,
not plumbing.

## Install

```bash
pip install neurocore-ai
```

## Quick start

```bash
neurocore init my-agent
cd my-agent
neurocore run blueprints/agent.flow.yaml
```

## Contents

```{toctree}
:maxdepth: 2
:caption: Guides

tutorial
agent-quickstart
agent-manual
concepts
architecture
providers
persistence-and-runs
human-in-the-loop
skill-authoring
why-not-langgraph
changelog
```
