"""T4: Error types — verify hierarchy, catchability, messages, and independence."""

from __future__ import annotations

import pytest

from neurocore.errors import (
    BlueprintError,
    ConfigError,
    ExecutionError,
    NeuroCoreError,
    SkillError,
)


class TestErrorHierarchy:
    """All NeuroCore errors inherit from NeuroCoreError → Exception."""

    @pytest.mark.parametrize(
        "error_cls",
        [ConfigError, SkillError, BlueprintError, ExecutionError],
    )
    def test_subclass_of_neurocore_error(self, error_cls: type):
        assert issubclass(error_cls, NeuroCoreError)

    @pytest.mark.parametrize(
        "error_cls",
        [NeuroCoreError, ConfigError, SkillError, BlueprintError, ExecutionError],
    )
    def test_subclass_of_exception(self, error_cls: type):
        assert issubclass(error_cls, Exception)

    def test_neurocore_error_not_subclass_of_children(self):
        """Parent should not be a subclass of its children."""
        assert not issubclass(NeuroCoreError, ConfigError)
        assert not issubclass(NeuroCoreError, SkillError)


class TestErrorCatching:
    """Verify errors can be raised, caught at different levels."""

    @pytest.mark.parametrize(
        "error_cls",
        [ConfigError, SkillError, BlueprintError, ExecutionError],
    )
    def test_catch_by_base_class(self, error_cls: type):
        with pytest.raises(NeuroCoreError):
            raise error_cls("test")

    @pytest.mark.parametrize(
        "error_cls",
        [ConfigError, SkillError, BlueprintError, ExecutionError],
    )
    def test_catch_by_exact_class(self, error_cls: type):
        with pytest.raises(error_cls):
            raise error_cls("test")

    def test_config_error_not_caught_as_skill_error(self):
        with pytest.raises(ConfigError):
            raise ConfigError("config issue")
        # SkillError should NOT catch ConfigError
        with pytest.raises(ConfigError):
            try:
                raise ConfigError("config issue")
            except SkillError:
                pytest.fail("ConfigError should not be caught by SkillError")


class TestErrorMessages:
    @pytest.mark.parametrize(
        "error_cls",
        [NeuroCoreError, ConfigError, SkillError, BlueprintError, ExecutionError],
    )
    def test_message_preserved(self, error_cls: type):
        msg = f"Something went wrong in {error_cls.__name__}"
        err = error_cls(msg)
        assert str(err) == msg

    def test_empty_message(self):
        err = NeuroCoreError()
        assert str(err) == ""
