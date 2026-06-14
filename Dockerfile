# NeuroCore runtime image.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install NeuroCore with local-provider support (OpenAI-compatible / Ollama / vLLM).
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[local]"

# Project files (blueprints/, skills/, neurocore.yaml) are mounted or copied in.
# Example:
#   docker run --rm -v "$PWD":/project -w /project neurocore \
#     run blueprints/agent.flow.yaml --data query="hello"
ENTRYPOINT ["neurocore"]
CMD ["--help"]
