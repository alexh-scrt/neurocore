"""Answer a question grounded in retrieved documents."""
from __future__ import annotations

import json

from flowengine import FlowContext

from neurocore.llm.provider import LLMMessage
from neurocore.skills.base import AsyncSkill, SkillMeta


class AnswerSkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="answer",
        version="0.1.0",
        description="Generate an answer grounded in retrieved context.",
        requires_llm=True,
        consumes=["query", "qdrant_result"],
        provides=["answer"],
    )

    async def process(self, context: FlowContext) -> FlowContext:
        query = str(context.get("query", ""))
        docs = context.get("qdrant_result")
        prompt = (
            f"Question: {query}\n\n"
            f"Retrieved context (JSON):\n{json.dumps(docs, default=str)[:6000]}\n\n"
            "Answer using ONLY the retrieved context. If it is insufficient, say so."
        )
        response = await self.llm.complete([LLMMessage(role="user", content=prompt)])
        context.set("answer", response.content)
        return context
