# local-ollama-agent

A fully self-hosted NeuroCore agent: a local LLM via **Ollama** plus a **Qdrant**
vector DB, no cloud API keys. Demonstrates the `openai-compatible`/`ollama`
provider added in NeuroCore.

## Run with Docker Compose

```bash
docker compose up -d ollama qdrant
docker compose exec ollama ollama pull llama3.2
docker compose run --rm neurocore run blueprints/chat.flow.yaml \
  --data query="Explain the CAP theorem in two sentences."
```

## Run locally (no Docker)

```bash
pip install "neurocore-ai[local]"
ollama serve & ; ollama pull llama3.2
neurocore run blueprints/chat.flow.yaml --data query="Explain the CAP theorem."
```

Run history is persisted to SQLite — inspect it with `neurocore runs list`.
