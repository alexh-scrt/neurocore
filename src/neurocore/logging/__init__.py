"""NeuroCore structured logging.

Provides structlog-based logging with console (colored, dev) and
JSON (machine-parseable, production) output modes.

Usage:
    from neurocore.logging import configure_logging, get_logger
    from neurocore.config import load_config

    config = load_config()
    configure_logging(config)

    log = get_logger("my-module")
    log.info("started")
"""

from neurocore.logging.setup import configure_logging, get_logger, reset_logging

__all__ = [
    "configure_logging",
    "get_logger",
    "reset_logging",
]
