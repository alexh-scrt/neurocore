"""Tests for GeminiAuditorSkill."""
import pytest
from flowengine import FlowContext

from neurocore_skill_gemini_auditor.skill import GeminiAuditorSkill


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
