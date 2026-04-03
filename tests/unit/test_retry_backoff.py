"""Tests for NC-FIX-002 — retry/exponential backoff in _run_skill_async."""

from unittest.mock import AsyncMock, patch

import pytest
from flowengine import FlowContext

from neurocore import AsyncSkill, Skill, SkillMeta
from neurocore.runtime.executor import _run_skill_async

# ---------------------------------------------------------------------------
# Test skills
# ---------------------------------------------------------------------------


class NoRetrySkill(AsyncSkill):
    skill_meta = SkillMeta(name="no-retry", version="0.1.0", max_retries=0)

    async def process(self, context: FlowContext) -> FlowContext:
        raise ValueError("boom")


class RetryOnceSkill(AsyncSkill):
    skill_meta = SkillMeta(name="retry-once", version="0.1.0", max_retries=1)
    call_count = 0

    async def process(self, context: FlowContext) -> FlowContext:
        RetryOnceSkill.call_count += 1
        if RetryOnceSkill.call_count <= 1:
            raise ValueError("first failure")
        context.set("result", "ok")
        return context


class RetryThreeSkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="retry-three", version="0.1.0",
        max_retries=3,
        retry_delay_base=0.01,
        retry_delay_max=0.05,
    )
    call_count = 0

    async def process(self, context: FlowContext) -> FlowContext:
        RetryThreeSkill.call_count += 1
        raise ValueError(f"fail #{RetryThreeSkill.call_count}")


class SucceedOnThirdSkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="succeed-third", version="0.1.0",
        max_retries=3,
        retry_delay_base=0.01,
        retry_delay_max=0.05,
    )
    call_count = 0

    async def process(self, context: FlowContext) -> FlowContext:
        SucceedOnThirdSkill.call_count += 1
        if SucceedOnThirdSkill.call_count < 3:
            raise ValueError("not yet")
        context.set("result", "third time")
        return context


class SpecificRetrySkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="specific-retry", version="0.1.0",
        max_retries=3,
        retry_delay_base=0.01,
        retry_on=(ValueError,),
    )
    call_count = 0

    async def process(self, context: FlowContext) -> FlowContext:
        SpecificRetrySkill.call_count += 1
        raise TypeError("wrong type")


class SpecificRetryMatchSkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="specific-match", version="0.1.0",
        max_retries=3,
        retry_delay_base=0.01,
        retry_on=(ValueError,),
    )
    call_count = 0

    async def process(self, context: FlowContext) -> FlowContext:
        SpecificRetryMatchSkill.call_count += 1
        raise ValueError("value error")


class SyncRetrySkill(Skill):
    skill_meta = SkillMeta(
        name="sync-retry", version="0.1.0",
        max_retries=2,
        retry_delay_base=0.01,
        retry_delay_max=0.05,
    )
    call_count = 0

    def process(self, context: FlowContext) -> FlowContext:
        SyncRetrySkill.call_count += 1
        if SyncRetrySkill.call_count < 2:
            raise ValueError("sync fail")
        context.set("result", "sync ok")
        return context


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_skill_with_max_retries_zero_does_not_retry():
    skill = NoRetrySkill()
    skill.init({})
    with pytest.raises(ValueError, match="boom"):
        await _run_skill_async(skill, FlowContext())


async def test_skill_with_max_retries_one_retries_once_on_exception():
    RetryOnceSkill.call_count = 0
    skill = RetryOnceSkill()
    skill.init({})
    result = await _run_skill_async(skill, FlowContext())
    assert result.get("result") == "ok"
    assert RetryOnceSkill.call_count == 2


async def test_skill_with_max_retries_three_retries_three_times():
    RetryThreeSkill.call_count = 0
    skill = RetryThreeSkill()
    skill.init({})
    with pytest.raises(ValueError, match="fail #4"):
        await _run_skill_async(skill, FlowContext())
    assert RetryThreeSkill.call_count == 4  # 1 initial + 3 retries


async def test_retry_stops_after_max_retries_exhausted():
    RetryThreeSkill.call_count = 0
    skill = RetryThreeSkill()
    skill.init({})
    with pytest.raises(ValueError):
        await _run_skill_async(skill, FlowContext())
    assert RetryThreeSkill.call_count == 4


async def test_retry_reraises_last_exception_after_exhaustion():
    RetryThreeSkill.call_count = 0
    skill = RetryThreeSkill()
    skill.init({})
    with pytest.raises(ValueError, match="fail #4"):
        await _run_skill_async(skill, FlowContext())


async def test_retry_on_empty_tuple_retries_on_any_exception():
    """When retry_on=() (default), retries on any Exception."""
    RetryOnceSkill.call_count = 0
    skill = RetryOnceSkill()
    skill.init({})
    result = await _run_skill_async(skill, FlowContext())
    assert result.get("result") == "ok"


async def test_retry_on_specific_type_ignores_other_exceptions():
    SpecificRetrySkill.call_count = 0
    skill = SpecificRetrySkill()
    skill.init({})
    with pytest.raises(TypeError, match="wrong type"):
        await _run_skill_async(skill, FlowContext())
    assert SpecificRetrySkill.call_count == 1  # no retry


async def test_retry_on_specific_type_retries_matching_exceptions():
    SpecificRetryMatchSkill.call_count = 0
    skill = SpecificRetryMatchSkill()
    skill.init({})
    with pytest.raises(ValueError, match="value error"):
        await _run_skill_async(skill, FlowContext())
    assert SpecificRetryMatchSkill.call_count == 4  # 1 + 3 retries


async def test_successful_on_third_attempt_returns_result():
    SucceedOnThirdSkill.call_count = 0
    skill = SucceedOnThirdSkill()
    skill.init({})
    result = await _run_skill_async(skill, FlowContext())
    assert result.get("result") == "third time"
    assert SucceedOnThirdSkill.call_count == 3


async def test_non_retryable_exception_reraises_immediately():
    SpecificRetrySkill.call_count = 0
    skill = SpecificRetrySkill()
    skill.init({})
    with pytest.raises(TypeError):
        await _run_skill_async(skill, FlowContext())
    assert SpecificRetrySkill.call_count == 1


async def test_sync_skill_also_gets_retry_logic():
    SyncRetrySkill.call_count = 0
    skill = SyncRetrySkill()
    skill.init({})
    result = await _run_skill_async(skill, FlowContext())
    assert result.get("result") == "sync ok"
    assert SyncRetrySkill.call_count == 2


@patch("neurocore.runtime.executor.asyncio.sleep", new_callable=AsyncMock)
async def test_backoff_delay_increases_exponentially(mock_sleep):
    """Verify that sleep is called with increasing delays."""

    class AlwaysFail(AsyncSkill):
        skill_meta = SkillMeta(
            name="always-fail", version="0.1.0",
            max_retries=3,
            retry_delay_base=1.0,
            retry_delay_max=100.0,
        )

        async def process(self, context: FlowContext) -> FlowContext:
            raise ValueError("fail")

    skill = AlwaysFail()
    skill.init({})
    with pytest.raises(ValueError):
        await _run_skill_async(skill, FlowContext())

    assert mock_sleep.call_count == 3
    delays = [call.args[0] for call in mock_sleep.call_args_list]
    # base * 2^0 = 1.0, base * 2^1 = 2.0, base * 2^2 = 4.0
    # with jitter: delay in [0, cap]
    assert delays[0] <= 1.0
    assert delays[1] <= 2.0
    assert delays[2] <= 4.0


@patch("neurocore.runtime.executor.asyncio.sleep", new_callable=AsyncMock)
async def test_backoff_delay_capped_at_retry_delay_max(mock_sleep):

    class CapFail(AsyncSkill):
        skill_meta = SkillMeta(
            name="cap-fail", version="0.1.0",
            max_retries=3,
            retry_delay_base=10.0,
            retry_delay_max=5.0,  # cap is less than base * 2^n
        )

        async def process(self, context: FlowContext) -> FlowContext:
            raise ValueError("fail")

    skill = CapFail()
    skill.init({})
    with pytest.raises(ValueError):
        await _run_skill_async(skill, FlowContext())

    delays = [call.args[0] for call in mock_sleep.call_args_list]
    for d in delays:
        assert d <= 5.0


@patch("neurocore.runtime.executor.log")
async def test_retry_logs_warning_on_each_attempt(mock_log):

    class LogFail(AsyncSkill):
        skill_meta = SkillMeta(
            name="log-fail", version="0.1.0",
            max_retries=2,
            retry_delay_base=0.01,
        )
        call_count = 0

        async def process(self, context: FlowContext) -> FlowContext:
            LogFail.call_count += 1
            raise ValueError("log test")

    LogFail.call_count = 0
    skill = LogFail()
    skill.init({})
    with pytest.raises(ValueError):
        await _run_skill_async(skill, FlowContext())

    assert mock_log.warning.call_count == 2
    # Check first warning call has expected kwargs
    call_kwargs = mock_log.warning.call_args_list[0]
    assert call_kwargs[0][0] == "skill.retry"
