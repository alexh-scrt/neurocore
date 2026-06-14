"""Two trivial skills bracketing a human-approval gate."""
from __future__ import annotations

from flowengine import FlowContext

from neurocore.skills.base import Skill, SkillMeta


class DraftSkill(Skill):
    skill_meta = SkillMeta(
        name="draft", version="0.1.0", consumes=["topic"], provides=["draft"]
    )

    def process(self, context: FlowContext) -> FlowContext:
        topic = context.get("topic", "the proposal")
        context.set("draft", f"Draft action for: {topic}")
        return context


class SendSkill(Skill):
    skill_meta = SkillMeta(
        name="send", version="0.1.0", consumes=["draft", "approval"], provides=["sent"]
    )

    def process(self, context: FlowContext) -> FlowContext:
        # Only reached after the approval gate is approved.
        context.set("sent", True)
        return context
