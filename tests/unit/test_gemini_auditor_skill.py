"""Tests for NC-FIX-001 — GeminiAuditorSkill."""

import json

# Import the skill directly from the package source
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from flowengine import FlowContext

from neurocore.llm.provider import LLMResponse

# Add the gemini-auditor package to path for testing
_pkg = Path(__file__).resolve().parents[2] / "packages" / "neurocore-skill-gemini-auditor" / "src"
if str(_pkg) not in sys.path:
    sys.path.insert(0, str(_pkg))

from neurocore_skill_gemini_auditor.skill import _AUDITOR_SYSTEM_PROMPT, GeminiAuditorSkill  # noqa: E402, I001


def test_gemini_auditor_has_correct_skill_meta_name():
    assert GeminiAuditorSkill.skill_meta.name == "gemini-auditor"


def test_gemini_auditor_provides_gemini_review():
    assert "gemini_review" in GeminiAuditorSkill.skill_meta.provides


def test_gemini_auditor_consumes_ac1_draft():
    assert "ac1_draft" in GeminiAuditorSkill.skill_meta.consumes


def test_gemini_auditor_requires_llm_is_true():
    assert GeminiAuditorSkill.skill_meta.requires_llm is True


def test_gemini_auditor_max_retries_is_nonzero():
    assert GeminiAuditorSkill.skill_meta.max_retries == 2


async def test_gemini_auditor_returns_error_when_no_draft():
    skill = GeminiAuditorSkill()
    skill.init({})
    ctx = FlowContext()
    result = await skill.process(ctx)
    review = result.get("gemini_review")
    assert review.verdict == "error"
    assert "No draft" in review.summary


async def test_gemini_auditor_returns_error_when_llm_is_none():
    skill = GeminiAuditorSkill()
    skill.init({})
    skill.llm = None
    ctx = FlowContext()
    ctx.set("ac1_draft", "some paper draft")
    with pytest.raises(RuntimeError, match="requires_llm=True"):
        await skill.process(ctx)


async def test_gemini_auditor_parses_valid_json_response():
    skill = GeminiAuditorSkill()
    skill.init({})

    mock_llm = AsyncMock()
    review_json = json.dumps({
        "verdict": "accept",
        "objections": [],
        "summary": "All steps are independently reproducible.",
    })
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content=review_json, model="gemini-2.0-flash",
    ))
    skill.llm = mock_llm

    ctx = FlowContext()
    ctx.set("ac1_draft", "A paper about math.")
    result = await skill.process(ctx)
    review = result.get("gemini_review")
    assert review.verdict == "accept"
    assert review.objections == []


async def test_gemini_auditor_handles_markdown_fenced_json():
    skill = GeminiAuditorSkill()
    skill.init({})

    review_data = {"verdict": "reject", "objections": [], "summary": "Bad paper."}
    fenced = f"```json\n{json.dumps(review_data)}\n```"
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content=fenced, model="gemini-2.0-flash",
    ))
    skill.llm = mock_llm

    ctx = FlowContext()
    ctx.set("ac1_draft", "Paper text here.")
    result = await skill.process(ctx)
    review = result.get("gemini_review")
    assert review.verdict == "reject"


async def test_gemini_auditor_handles_malformed_json_gracefully():
    skill = GeminiAuditorSkill()
    skill.init({})

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content="not valid json at all", model="gemini-2.0-flash",
    ))
    skill.llm = mock_llm

    ctx = FlowContext()
    ctx.set("ac1_draft", "Paper.")
    result = await skill.process(ctx)
    review = result.get("gemini_review")
    assert review.verdict == "error"
    assert "non-JSON" in review.summary


async def test_gemini_auditor_accept_verdict_when_no_objections():
    skill = GeminiAuditorSkill()
    skill.init({})

    review_data = {
        "verdict": "accept",
        "objections": [],
        "summary": "All steps are independently reproducible.",
    }
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content=json.dumps(review_data), model="gemini-2.0-flash",
    ))
    skill.llm = mock_llm

    ctx = FlowContext()
    ctx.set("ac1_draft", "Good paper.")
    result = await skill.process(ctx)
    assert result.get("gemini_review").verdict == "accept"


async def test_gemini_auditor_revision_requested_with_objections():
    skill = GeminiAuditorSkill()
    skill.init({})

    review_data = {
        "verdict": "revision-requested",
        "objections": [
            {"step": "Lemma 4", "issue": "missing proof", "severity": "critical"},
        ],
        "summary": "Key lemma lacks proof.",
    }
    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content=json.dumps(review_data), model="gemini-2.0-flash",
    ))
    skill.llm = mock_llm

    ctx = FlowContext()
    ctx.set("ac1_draft", "Paper with issues.")
    result = await skill.process(ctx)
    review = result.get("gemini_review")
    assert review.verdict == "revision-requested"
    assert len(review.objections) == 1


async def test_gemini_auditor_passes_system_prompt_to_llm():
    skill = GeminiAuditorSkill()
    skill.init({})

    mock_llm = AsyncMock()
    mock_llm.complete = AsyncMock(return_value=LLMResponse(
        content='{"verdict":"accept","objections":[],"summary":"ok"}',
        model="gemini-2.0-flash",
    ))
    skill.llm = mock_llm

    ctx = FlowContext()
    ctx.set("ac1_draft", "Paper text.")
    await skill.process(ctx)

    call_kwargs = mock_llm.complete.call_args
    assert call_kwargs.kwargs["system"] == _AUDITOR_SYSTEM_PROMPT
