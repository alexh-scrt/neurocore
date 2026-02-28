"""Upper skill — converts text to uppercase with optional suffix.

Demonstrates a second skill in a pipeline, reading from the output
of a previous skill and writing to a new context key.
"""

from flowengine import FlowContext

from neurocore import Skill, SkillMeta


class UpperSkill(Skill):
    """Uppercases text with an optional suffix."""

    skill_meta = SkillMeta(
        name="upper",
        version="1.0.0",
        description="Converts text to uppercase with optional suffix",
        provides=["result"],
        consumes=["output"],
        config_schema={
            "properties": {
                "suffix": {
                    "type": "string",
                    "description": "Suffix appended after uppercasing",
                },
            },
        },
    )

    def process(self, context: FlowContext) -> FlowContext:
        text = context.get("output", "")
        suffix = self.config.get("suffix", "")
        context.set("result", f"{text.upper()}{suffix}")
        return context
