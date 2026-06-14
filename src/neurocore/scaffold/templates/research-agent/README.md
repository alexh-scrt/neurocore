# {{ project_name }}

A multi-source research agent: web search (Tavily) + academic papers (arXiv),
summarized into a cited answer by an LLM.

## Setup

```bash
pip install neurocore-ai neurocore-skill-tavily neurocore-skill-arxiv
export ANTHROPIC_API_KEY=sk-...
export TAVILY_API_KEY=tvly-...
```

## Run

```bash
neurocore run blueprints/research.flow.yaml --data query="latest progress on the Riemann hypothesis"
```

The `summarize` skill is bundled in `skills/`; `tavily` and `arxiv` are
installable marketplace skills (`neurocore skill list` shows what's available).
