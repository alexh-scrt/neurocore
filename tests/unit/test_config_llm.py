"""Tests for NC-007 — Config Schema Extensions."""

from neurocore.config.schema import LLMConfig, NeuroCoreConfig


def test_llm_config_defaults_are_empty():
    config = LLMConfig()
    assert config.provider == ""
    assert config.model == ""
    assert config.api_key == ""
    assert config.max_tokens == 8192
    assert config.temperature == 1.0


def test_llm_config_loaded_from_yaml():
    config = NeuroCoreConfig(
        llm=LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-6",
            api_key="sk-test",
        )
    )
    assert config.llm.provider == "anthropic"
    assert config.llm.model == "claude-sonnet-4-6"
    assert config.llm.api_key == "sk-test"


def test_llm_config_env_var_override(monkeypatch):
    """LLM config should be overridable, even if env prefix isn't auto-wired."""
    config = NeuroCoreConfig(
        llm=LLMConfig(provider="openai", model="gpt-4o", api_key="key123")
    )
    assert config.llm.provider == "openai"


def test_get_skill_config_injects_llm_from_project():
    config = NeuroCoreConfig(
        llm=LLMConfig(provider="anthropic", model="claude-sonnet-4-6", api_key="sk-proj"),
        skills={"my-skill": {"custom_key": "value"}},
    )
    result = config.get_skill_config("my-skill")
    assert result["llm_provider"] == "anthropic"
    assert result["llm_model"] == "claude-sonnet-4-6"
    assert result["llm_api_key"] == "sk-proj"
    assert result["custom_key"] == "value"


def test_get_skill_config_skill_level_wins_over_project():
    config = NeuroCoreConfig(
        llm=LLMConfig(provider="anthropic", model="claude-sonnet-4-6"),
        skills={"my-skill": {"llm_provider": "openai", "llm_model": "gpt-4o"}},
    )
    result = config.get_skill_config("my-skill")
    # Skill-level llm_provider is set, so project LLM should NOT be injected
    assert result["llm_provider"] == "openai"
    assert result["llm_model"] == "gpt-4o"


def test_get_skill_config_no_injection_when_project_llm_empty():
    config = NeuroCoreConfig(
        llm=LLMConfig(),  # empty provider
        skills={"my-skill": {"custom": "val"}},
    )
    result = config.get_skill_config("my-skill")
    assert "llm_provider" not in result
    assert "llm_base_url" not in result
    assert result["custom"] == "val"


def test_get_skill_config_injects_base_url():
    config = NeuroCoreConfig(
        llm=LLMConfig(provider="ollama", model="llama3.3", base_url="http://x/v1"),
    )
    result = config.get_skill_config("my-skill")
    assert result["llm_provider"] == "ollama"
    assert result["llm_base_url"] == "http://x/v1"


def test_get_skill_config_resolves_api_key_env(monkeypatch):
    monkeypatch.setenv("MY_LLM_KEY", "sk-from-env")
    config = NeuroCoreConfig(
        llm=LLMConfig(provider="openai", model="gpt-4o", api_key_env="MY_LLM_KEY"),
    )
    result = config.get_skill_config("my-skill")
    assert result["llm_api_key"] == "sk-from-env"


def test_get_skill_config_literal_api_key_wins_over_env(monkeypatch):
    monkeypatch.setenv("MY_LLM_KEY", "sk-from-env")
    config = NeuroCoreConfig(
        llm=LLMConfig(
            provider="openai", model="gpt-4o", api_key="sk-literal", api_key_env="MY_LLM_KEY"
        ),
    )
    result = config.get_skill_config("my-skill")
    assert result["llm_api_key"] == "sk-literal"
