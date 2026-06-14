# {{ project_name }}

Retrieval-augmented generation: retrieve relevant chunks from a
[Qdrant](https://qdrant.tech) collection, then answer grounded in them.

## Setup

```bash
pip install neurocore-ai neurocore-skill-qdrant
docker run -p 6333:6333 qdrant/qdrant      # local Qdrant
export ANTHROPIC_API_KEY=sk-...
```

## Run

```bash
neurocore run blueprints/rag.flow.yaml --data query="What does the onboarding doc say about API keys?"
```

The `answer` skill is bundled; `qdrant` is an installable marketplace skill.
Populate the `documents` collection first (see the qdrant skill's README).
