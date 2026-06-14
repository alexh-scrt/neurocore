# Providers

NeuroCore injects an `LLMProvider` into any skill whose `SkillMeta` sets
`requires_llm=True`. You configure the provider once; skills stay
provider-agnostic.

## Configuration

```yaml
# neurocore.yaml
llm:
  provider: anthropic        # see table below
  model: claude-sonnet-4-6
  api_key_env: ANTHROPIC_API_KEY   # name of the env var holding the key
  # api_key: "sk-..."        # or set the key literally (api_key wins over api_key_env)
  # base_url: ...            # for openai-compatible / ollama / vllm / litellm
  max_tokens: 8192
  temperature: 1.0
```

Per-skill overrides go under `skills.<name>` in `neurocore.yaml` or in a
blueprint component's `config`.

## Supported providers

| `provider` | Backend | Install | Notes |
|------------|---------|---------|-------|
| `anthropic` | Claude | (core dep) | default `claude-sonnet-4-6` |
| `openai` | OpenAI | `pip install "neurocore-ai[openai]"` | set `base_url` to reach a gateway |
| `gemini` | Google Gemini | `pip install "neurocore-ai[gemini]"` | |
| `openai-compatible` | any OpenAI-wire API | `pip install "neurocore-ai[local]"` | **requires** `base_url` |
| `ollama` | local Ollama | `pip install "neurocore-ai[local]"` | default `base_url` `http://localhost:11434/v1` |
| `vllm` | local vLLM | `pip install "neurocore-ai[local]"` | default `base_url` `http://localhost:8000/v1` |
| `litellm` | 100+ APIs via LiteLLM | `pip install "neurocore-ai[litellm]"` | routes by `model` |
| `mock` | deterministic test double | (core dep) | for tests |

`ollama`, `vllm`, and `openai-compatible` all speak the OpenAI chat-completions
wire format, so they share one implementation and need only the `openai` SDK.

## Local models, zero cloud keys

```yaml
llm:
  provider: ollama
  model: llama3.2
  base_url: http://localhost:11434/v1
  api_key_env: OLLAMA_API_KEY   # Ollama ignores it; any non-empty value works
```

```bash
pip install "neurocore-ai[local]"
ollama serve & ; ollama pull llama3.2
neurocore run blueprints/chat.flow.yaml --data query="Hello"
```

## Using the provider in a skill

```python
from neurocore import AsyncSkill, SkillMeta
from neurocore.llm.provider import LLMMessage

class ChatSkill(AsyncSkill):
    skill_meta = SkillMeta(name="chat", version="0.1.0",
                           requires_llm=True, consumes=["query"], provides=["answer"])

    async def process(self, context):
        resp = await self.llm.complete(
            [LLMMessage(role="user", content=context.get("query", ""))]
        )
        context.set("answer", resp.content)
        return context
```
