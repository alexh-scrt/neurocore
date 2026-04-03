"""Tests for SkillMeta retry/backoff fields (NC-FIX-002)."""

from neurocore import SkillMeta


def test_skill_meta_default_max_retries_is_zero():
    meta = SkillMeta(name="test", version="0.1.0")
    assert meta.max_retries == 0


def test_skill_meta_default_retry_on_is_empty_tuple():
    meta = SkillMeta(name="test", version="0.1.0")
    assert meta.retry_on == ()


def test_skill_meta_default_retry_delay_base_is_one():
    meta = SkillMeta(name="test", version="0.1.0")
    assert meta.retry_delay_base == 1.0


def test_skill_meta_default_retry_delay_max_is_sixty():
    meta = SkillMeta(name="test", version="0.1.0")
    assert meta.retry_delay_max == 60.0


def test_skill_meta_custom_max_retries():
    meta = SkillMeta(name="test", version="0.1.0", max_retries=5)
    assert meta.max_retries == 5


def test_skill_meta_custom_retry_on():
    meta = SkillMeta(name="test", version="0.1.0", retry_on=(ValueError, TypeError))
    assert meta.retry_on == (ValueError, TypeError)


def test_skill_meta_is_still_frozen_with_retry_fields():
    import pytest

    meta = SkillMeta(name="test", version="0.1.0", max_retries=3)
    with pytest.raises(AttributeError):
        meta.max_retries = 5  # type: ignore[misc]
