"""NeuroCore skill system.

Skills are FlowEngine BaseComponents with declarative metadata.
This package provides the Skill base class, SkillMeta dataclass,
skill discovery (directory scan + entry points), and the skill registry.
"""

from neurocore.skills.base import Skill, SkillMeta, skillmeta_to_componentmeta
from neurocore.skills.loader import (
    discover_directory,
    discover_entry_points,
    discover_skills,
)
from neurocore.skills.registry import SkillRegistry

__all__ = [
    "Skill",
    "SkillMeta",
    "skillmeta_to_componentmeta",
    "SkillRegistry",
    "discover_directory",
    "discover_entry_points",
    "discover_skills",
]
