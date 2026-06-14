# {{ project_name }}

A three-agent debate as a NeuroCore **graph** flow: a *proposer* argues a topic,
a *critic* rebuts, and a *judge* decides — each an LLM agent with its own system
prompt.

## Run

```bash
pip install neurocore-ai
export ANTHROPIC_API_KEY=sk-...
neurocore run blueprints/debate.flow.yaml --data topic="Should AI agents run with human approval gates?"
```

Inspect the run afterwards:

```bash
neurocore runs list
neurocore runs inspect <run_id> --full
```
