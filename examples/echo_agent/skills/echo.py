"""Echo skill — echoes input with an optional prefix.

This is a minimal skill example showing the core pattern:
1. Define SkillMeta with metadata
2. Implement process() to read from and write to FlowContext
3. Use self.config to access merged configuration
"""

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class EchoSkill(Skill):
    """Echoes input to output with an optional prefix."""

    skill_meta = SkillMeta(
        name="echo",
        version="1.0.0",
        description="Echoes input with optional prefix",
        provides=["output"],
        consumes=["input"],
        config_schema={
            "properties": {
                "prefix": {
                    "type": "string",
                    "description": "Prefix prepended to the echoed message",
                },
            },
        },
    )

    def process(self, context: FlowContext) -> FlowContext:
        prefix = self.config.get("prefix", "")
        message = context.get("input", "")
        context.set("output", f"{prefix}{message}")
        return context
