"""NeuroCore skill system.

Skills are FlowEngine BaseComponents with declarative metadata.
This package provides the Skill base class, SkillMeta dataclass,
skill discovery (directory scan + entry points), and the skill registry.
"""

from neurocore.skills.base import Skill, SkillMeta

__all__ = [
    "Skill",
    "SkillMeta",
]
