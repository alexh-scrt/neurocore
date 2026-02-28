"""Tests for logging/setup.py — structlog configuration, console/JSON modes, file output."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest
import structlog

from neurocore.config.schema import LoggingConfig, NeuroCoreConfig
from neurocore.logging.setup import configure_logging, get_logger, reset_logging


@pytest.fixture(autouse=True)
def _reset_logging_after_test():
    """Reset logging state after each test to avoid pollution."""
    yield
    reset_logging()


class TestConfigureLogging:
    def test_sets_root_log_level_info(self):
        config = NeuroCoreConfig(logging=LoggingConfig(level="INFO"))
        configure_logging(config)
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_sets_root_log_level_debug(self):
        config = NeuroCoreConfig(logging=LoggingConfig(level="DEBUG"))
        configure_logging(config)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_sets_root_log_level_error(self):
        config = NeuroCoreConfig(logging=LoggingConfig(level="ERROR"))
        configure_logging(config)
        root = logging.getLogger()
        assert root.level == logging.ERROR

    def test_stderr_handler_attached(self):
        config = NeuroCoreConfig()
        configure_logging(config)
        root = logging.getLogger()
        assert len(root.handlers) >= 1
        assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)

    def test_json_format_produces_valid_json(self, capsys: pytest.CaptureFixture[str]):
        config = NeuroCoreConfig(logging=LoggingConfig(format="json"))
        configure_logging(config)

        log = get_logger("test")
        log.info("hello", key="value")

        captured = capsys.readouterr()
        # JSON output goes to stderr
        lines = [line for line in captured.err.strip().split("\n") if line]
        assert len(lines) >= 1
        parsed = json.loads(lines[-1])
        assert parsed["event"] == "hello"
        assert parsed["key"] == "value"
        assert parsed["component"] == "test"

    def test_console_format_does_not_produce_json(self, capsys: pytest.CaptureFixture[str]):
        config = NeuroCoreConfig(logging=LoggingConfig(format="console"))
        configure_logging(config)

        log = get_logger("test")
        log.info("hello_console")

        captured = capsys.readouterr()
        assert "hello_console" in captured.err
        # Console format should NOT be valid JSON
        for line in captured.err.strip().split("\n"):
            if "hello_console" in line:
                with pytest.raises(json.JSONDecodeError):
                    json.loads(line)

    def test_file_handler_writes_json(self, tmp_path: Path):
        log_file = tmp_path / "logs" / "test.log"
        config = NeuroCoreConfig(
            logging=LoggingConfig(file=str(log_file)),
            project_root=tmp_path,
        )
        configure_logging(config)

        log = get_logger("filetest")
        log.warning("file_event", detail="abc")

        # Flush handlers
        for handler in logging.getLogger().handlers:
            handler.flush()

        assert log_file.exists()
        content = log_file.read_text()
        lines = [line for line in content.strip().split("\n") if line]
        assert len(lines) >= 1
        parsed = json.loads(lines[-1])
        assert parsed["event"] == "file_event"
        assert parsed["detail"] == "abc"

    def test_file_handler_creates_parent_dirs(self, tmp_path: Path):
        log_file = tmp_path / "deep" / "nested" / "app.log"
        config = NeuroCoreConfig(
            logging=LoggingConfig(file=str(log_file)),
            project_root=tmp_path,
        )
        configure_logging(config)
        assert log_file.parent.exists()

    def test_noisy_loggers_quieted(self):
        config = NeuroCoreConfig(logging=LoggingConfig(level="DEBUG"))
        configure_logging(config)
        for name in ("uvicorn", "uvicorn.access", "httpx", "httpcore", "asyncio"):
            assert logging.getLogger(name).level >= logging.WARNING


class TestGetLogger:
    def test_returns_bound_logger(self):
        config = NeuroCoreConfig()
        configure_logging(config)
        log = get_logger("mycomp")
        assert log is not None

    def test_bound_to_component_name(self, capsys: pytest.CaptureFixture[str]):
        config = NeuroCoreConfig(logging=LoggingConfig(format="json"))
        configure_logging(config)

        log = get_logger("skills")
        log.info("test_event")

        captured = capsys.readouterr()
        lines = [line for line in captured.err.strip().split("\n") if line]
        parsed = json.loads(lines[-1])
        assert parsed["component"] == "skills"

    def test_no_name_returns_unbound_logger(self, capsys: pytest.CaptureFixture[str]):
        config = NeuroCoreConfig(logging=LoggingConfig(format="json"))
        configure_logging(config)

        log = get_logger()
        log.info("unbound_event")

        captured = capsys.readouterr()
        lines = [line for line in captured.err.strip().split("\n") if line]
        parsed = json.loads(lines[-1])
        assert "component" not in parsed


class TestResetLogging:
    def test_clears_handlers(self):
        config = NeuroCoreConfig()
        configure_logging(config)
        root = logging.getLogger()
        assert len(root.handlers) >= 1

        reset_logging()
        assert len(root.handlers) == 0

    def test_allows_reconfiguration(self):
        config1 = NeuroCoreConfig(logging=LoggingConfig(level="DEBUG"))
        configure_logging(config1)
        assert logging.getLogger().level == logging.DEBUG

        reset_logging()

        config2 = NeuroCoreConfig(logging=LoggingConfig(level="ERROR"))
        configure_logging(config2)
        assert logging.getLogger().level == logging.ERROR
