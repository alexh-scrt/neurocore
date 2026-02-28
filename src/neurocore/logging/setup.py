"""NeuroCore structured logging — configures structlog for the entire application.

Reuses the same pattern as NeuroWeave: structlog with console (colored, dev)
and JSON (machine-parseable, production) modes. Adds optional file handler
support for persistent log output.

Usage:
    from neurocore.logging import configure_logging, get_logger
    from neurocore.config import load_config

    config = load_config()
    configure_logging(config)

    log = get_logger("my-component")
    log.info("started", version="0.1.0")
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from neurocore.config.schema import NeuroCoreConfig

# Track whether logging has been configured to prevent double-init
_configured: bool = False


def configure_logging(config: NeuroCoreConfig) -> None:
    """Configure structlog and stdlib logging from NeuroCoreConfig.

    Call once at startup. After this, any module can do:

        from neurocore.logging import get_logger
        log = get_logger("skills")
        log.info("skill.loaded", name="neuroweave", version="0.1.0")

    Args:
        config: NeuroCoreConfig with logging.level, logging.format, logging.file.
    """
    global _configured

    log_level = getattr(logging, config.logging.level.value.upper(), logging.INFO)

    # Shared processors — run for every log event
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    # Choose renderer based on format
    from neurocore.config.schema import LogFormat

    if config.logging.format == LogFormat.JSON:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=not _configured,  # Don't cache on reconfig
    )

    # Configure stdlib root logger so structlog output actually appears
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Optional file handler
    if config.logging.file is not None:
        file_path = config.resolve_path(config.logging.file)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # File output always uses JSON for machine parseability
        file_formatter = structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
        )
        file_handler = logging.FileHandler(str(file_path), encoding="utf-8")
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # Quiet noisy third-party loggers
    for name in ("uvicorn", "uvicorn.access", "httpx", "httpcore", "asyncio"):
        logging.getLogger(name).setLevel(max(log_level, logging.WARNING))

    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger, optionally bound to a component name.

    Args:
        name: Component name (e.g. "skills", "config", "runtime").
              Added as 'component' key in log events.

    Returns:
        A bound structlog logger.
    """
    log = structlog.get_logger()
    if name:
        log = log.bind(component=name)
    return log


def reset_logging() -> None:
    """Reset logging configuration. Primarily for testing."""
    global _configured
    structlog.reset_defaults()
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.WARNING)
    _configured = False
