"""Tests for NC-FIX-001 — GeminiProvider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from neurocore.llm.provider import (
    LLMMessage,
    LLMProvider,
    build_provider,
)

# ---------------------------------------------------------------------------
# Helper: create a GeminiProvider with a mocked client
# ---------------------------------------------------------------------------

def _make_provider(model: str = "gemini-2.0-flash"):
    """Create a GeminiProvider by mocking the google.genai import inside __init__."""
    with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": MagicMock()}):
        from neurocore.llm.provider import GeminiProvider
        provider = GeminiProvider(api_key="test-key", model=model)
    return provider


# ---------------------------------------------------------------------------
# Basic property tests
# ---------------------------------------------------------------------------


def test_gemini_provider_implements_llm_provider_protocol():
    provider = _make_provider()
    assert isinstance(provider, LLMProvider)


def test_gemini_provider_name_is_gemini():
    provider = _make_provider()
    assert provider.provider_name == "gemini"


def test_gemini_provider_default_model_is_flash():
    provider = _make_provider()
    assert provider.model == "gemini-2.0-flash"


def test_gemini_provider_custom_model():
    provider = _make_provider("gemini-pro")
    assert provider.model == "gemini-pro"


# ---------------------------------------------------------------------------
# Message conversion tests
# ---------------------------------------------------------------------------


def test_gemini_provider_convert_messages_user_role():
    provider = _make_provider()
    messages = [LLMMessage(role="user", content="hello")]
    contents, system_instruction = provider._convert_messages(messages, None)
    assert len(contents) == 1
    assert contents[0]["role"] == "user"
    assert contents[0]["parts"] == [{"text": "hello"}]
    assert system_instruction is None


def test_gemini_provider_convert_messages_assistant_becomes_model():
    provider = _make_provider()
    messages = [LLMMessage(role="assistant", content="hi")]
    contents, _ = provider._convert_messages(messages, None)
    assert contents[0]["role"] == "model"


def test_gemini_provider_convert_messages_system_extracted_to_instruction():
    provider = _make_provider()
    messages = [
        LLMMessage(role="system", content="be helpful"),
        LLMMessage(role="user", content="hi"),
    ]
    contents, system_instruction = provider._convert_messages(messages, None)
    assert len(contents) == 1  # system message not in contents
    assert system_instruction == "be helpful"


def test_gemini_provider_convert_messages_mixed_roles():
    provider = _make_provider()
    messages = [
        LLMMessage(role="system", content="sys"),
        LLMMessage(role="user", content="u1"),
        LLMMessage(role="assistant", content="a1"),
        LLMMessage(role="user", content="u2"),
    ]
    contents, system_instruction = provider._convert_messages(messages, None)
    assert len(contents) == 3
    assert system_instruction == "sys"
    assert contents[0]["role"] == "user"
    assert contents[1]["role"] == "model"
    assert contents[2]["role"] == "user"


def test_gemini_provider_system_param_merged_with_system_messages():
    provider = _make_provider()
    messages = [
        LLMMessage(role="system", content="msg-system"),
        LLMMessage(role="user", content="hi"),
    ]
    _, system_instruction = provider._convert_messages(messages, "param-system")
    assert "param-system" in system_instruction
    assert "msg-system" in system_instruction


# ---------------------------------------------------------------------------
# build_provider() tests
# ---------------------------------------------------------------------------


def test_build_provider_gemini_returns_gemini_provider():
    with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": MagicMock()}):
        provider = build_provider({"llm_provider": "gemini", "llm_api_key": "key"})
    assert provider is not None
    assert provider.provider_name == "gemini"


def test_build_provider_gemini_uses_default_model():
    with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": MagicMock()}):
        provider = build_provider({"llm_provider": "gemini", "llm_api_key": "key"})
    assert provider.model == "gemini-2.0-flash"


def test_build_provider_gemini_uses_custom_model():
    with patch.dict("sys.modules", {"google": MagicMock(), "google.genai": MagicMock()}):
        provider = build_provider({
            "llm_provider": "gemini",
            "llm_api_key": "key",
            "llm_model": "gemini-pro",
        })
    assert provider.model == "gemini-pro"


def test_build_provider_error_message_includes_gemini():
    with pytest.raises(ValueError, match="gemini"):
        build_provider({"llm_provider": "foobar"})


# ---------------------------------------------------------------------------
# Async tests (mock the SDK client)
# ---------------------------------------------------------------------------


async def test_gemini_provider_complete_calls_aio_generate_content():
    provider = _make_provider()

    mock_usage = MagicMock()
    mock_usage.prompt_token_count = 10
    mock_usage.candidates_token_count = 20

    mock_response = MagicMock()
    mock_response.text = "test response"
    mock_response.usage_metadata = mock_usage

    provider._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch.dict("sys.modules", {
        "google.genai": MagicMock(),
        "google.genai.types": MagicMock(),
    }):
        result = await provider.complete([LLMMessage(role="user", content="hi")])

    assert result.content == "test response"
    assert result.input_tokens == 10
    assert result.output_tokens == 20
    provider._client.aio.models.generate_content.assert_called_once()


async def test_gemini_provider_empty_response_text_returns_empty_string():
    provider = _make_provider()

    mock_response = MagicMock()
    mock_response.text = None
    mock_response.usage_metadata = None

    provider._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

    with patch.dict("sys.modules", {
        "google.genai": MagicMock(),
        "google.genai.types": MagicMock(),
    }):
        result = await provider.complete([LLMMessage(role="user", content="hi")])

    assert result.content == ""
    assert result.input_tokens == 0
    assert result.output_tokens == 0
