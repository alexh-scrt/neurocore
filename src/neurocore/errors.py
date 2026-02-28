"""NeuroCore exception hierarchy.

All NeuroCore-specific exceptions inherit from NeuroCoreError,
making it easy to catch framework errors without catching unrelated ones.

Hierarchy:
    NeuroCoreError
    +-- ConfigError           — configuration loading / validation failures
    +-- SkillError            — skill loading / discovery / execution failures
    +-- BlueprintError        — blueprint parsing / validation failures
    +-- ExecutionError        — runtime execution failures
"""


class NeuroCoreError(Exception):
    """Base exception for all NeuroCore errors."""


class ConfigError(NeuroCoreError):
    """Configuration loading or validation failure."""


class SkillError(NeuroCoreError):
    """Skill loading, discovery, or execution failure."""


class BlueprintError(NeuroCoreError):
    """Blueprint parsing or validation failure."""


class ExecutionError(NeuroCoreError):
    """Runtime execution failure."""
