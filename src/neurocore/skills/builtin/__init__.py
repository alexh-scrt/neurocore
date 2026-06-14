"""Built-in skills that ship with NeuroCore and are always discoverable.

These are registered by :func:`neurocore.skills.loader.discover_skills` before
the directory/entry-point scans, so blueprints can use them with no setup.
"""
from neurocore.skills.builtin.approval import ApprovalSkill

# Skill classes registered automatically by the loader.
BUILTIN_SKILLS = [ApprovalSkill]

__all__ = ["ApprovalSkill", "BUILTIN_SKILLS"]
