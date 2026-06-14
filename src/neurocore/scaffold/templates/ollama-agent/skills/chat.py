"""A minimal LLM chat skill. Reads `query`, writes `answer`."""
from __future__ import annotations

from flowengine import FlowContext

from neurocore.llm.provider import LLMMessage
from neurocore.skills.base import AsyncSkill, SkillMeta


class ChatSkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="chat",
        version="0.1.0",
        description="Answer a query with the configured LLM.",
        requires_llm=True,
        consumes=["query"],
        provides=["answer"],
        config_schema={
            "properties": {
                "system": {"type": "string", "description": "Optional system prompt."}
            }
        },
    )

    async def process(self, context: FlowContext) -> FlowContext:
        query = str(context.get("query", ""))
        system = self.config.get("system")
        response = await self.llm.complete(
            [LLMMessage(role="user", content=query)], system=system
        )
        context.set("answer", response.content)
        return context
