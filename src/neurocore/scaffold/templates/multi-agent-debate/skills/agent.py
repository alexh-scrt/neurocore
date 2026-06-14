"""A configurable LLM agent used as proposer, critic, and judge."""
from __future__ import annotations

from flowengine import FlowContext

from neurocore.llm.provider import LLMMessage
from neurocore.skills.base import AsyncSkill, SkillMeta


class AgentSkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="agent",
        version="0.1.0",
        description="A role-driven LLM agent (proposer / critic / judge).",
        requires_llm=True,
        consumes=["topic", "proposal", "critique"],
        provides=["proposal", "critique", "verdict"],
        config_schema={
            "properties": {
                "system": {"type": "string"},
                "input_key": {"type": "string"},
                "output_key": {"type": "string"},
            }
        },
    )

    async def process(self, context: FlowContext) -> FlowContext:
        input_key = self.config.get("input_key", "topic")
        output_key = self.config.get("output_key", "proposal")
        system = self.config.get("system", "You are a thoughtful debater.")
        prompt_parts = [f"Topic: {context.get('topic', '')}"]
        if input_key != "topic":
            prompt_parts.append(f"{input_key}: {context.get(input_key, '')}")
        response = await self.llm.complete(
            [LLMMessage(role="user", content="\n".join(prompt_parts))],
            system=system,
        )
        context.set(output_key, response.content)
        return context
