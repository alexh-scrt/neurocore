"""Summarize collected research context into a cited answer."""
from __future__ import annotations

import json

from flowengine import FlowContext

from neurocore.llm.provider import LLMMessage
from neurocore.skills.base import AsyncSkill, SkillMeta


class SummarizeSkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="summarize",
        version="0.1.0",
        description="Summarize search/paper results into an answer.",
        requires_llm=True,
        consumes=["query", "tavily_result", "arxiv_result"],
        provides=["answer"],
    )

    async def process(self, context: FlowContext) -> FlowContext:
        query = str(context.get("query", ""))
        sources = {
            "web": context.get("tavily_result"),
            "papers": context.get("arxiv_result"),
        }
        prompt = (
            f"Question: {query}\n\n"
            f"Sources (JSON):\n{json.dumps(sources, default=str)[:6000]}\n\n"
            "Write a concise, well-structured answer that cites the sources."
        )
        response = await self.llm.complete([LLMMessage(role="user", content=prompt)])
        context.set("answer", response.content)
        return context
