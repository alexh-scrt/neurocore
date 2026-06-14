# {{ project_name }}

A local LLM agent powered by [Ollama](https://ollama.com) through NeuroCore's
OpenAI-compatible provider — no cloud API key required.

## Setup

```bash
pip install "neurocore-ai[local]"
ollama serve &          # start Ollama
ollama pull llama3.2    # pull the model in neurocore.yaml
```

## Run

```bash
neurocore run blueprints/chat.flow.yaml --data query="Explain the Riemann hypothesis in two sentences."
```

Swap `llm.provider` to `vllm` (or any `openai-compatible` endpoint) in
`neurocore.yaml` to target a different local server.
