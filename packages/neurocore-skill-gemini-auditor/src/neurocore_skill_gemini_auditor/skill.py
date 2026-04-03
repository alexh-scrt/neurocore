"""Gemini-powered adversarial reproducibility auditor for AC1-LLM research review."""
from __future__ import annotations

import json
import re

from flowengine import FlowContext
from neurocore import AsyncSkill, SkillMeta
from neurocore.llm.provider import LLMMessage

_AUDITOR_SYSTEM_PROMPT = """You are an adversarial reproducibility auditor reviewing a mathematical paper.

YOUR SOLE ROLE: Find every step that cannot be independently reconstructed from the paper text alone.
Do NOT give general feedback. Do NOT praise the paper. Do NOT summarize it.

Look specifically for:
1. Steps that reference "the construction from the appendix" but the appendix does not contain it
2. Lemmas cited by name that are not stated in the paper
3. Claims that require external knowledge not cited in the paper
4. Proof steps where "it follows that" is used without justification
5. Missing definitions for non-standard notation
6. SDP, LP, or optimization formulations that are referenced but not fully stated

OUTPUT FORMAT — valid JSON only:
{
  "verdict": "accept" | "revision-requested" | "reject",
  "objections": [
    {
      "step": "location in paper (e.g. 'Lemma 4, step 3' or 'Appendix A')",
      "issue": "exact description of what cannot be reconstructed",
      "severity": "critical" | "major" | "minor"
    }
  ],
  "summary": "one sentence summary of the main reproducibility concern"
}

If the paper is fully reconstructable: {"verdict": "accept", "objections": [], "summary": "All steps are independently reproducible."}
"""


class GeminiAuditorSkill(AsyncSkill):
    skill_meta = SkillMeta(
        name="gemini-auditor",
        version="0.1.0",
        description="Gemini-powered reproducibility auditor — Reviewer C in AC1-LLM adversarial review",
        provides=["gemini_review"],
        consumes=["ac1_draft"],
        requires_llm=True,
        config_schema={
            "properties": {
                "llm_provider": {"type": "string", "default": "gemini"},
                "llm_model": {"type": "string", "default": "gemini-2.0-flash"},
                "llm_api_key": {"type": "string"},
                "max_tokens": {"type": "integer", "default": 4096},
            },
            "required": [],
        },
        tags=["review", "adversarial", "reproducibility", "gemini"],
        max_retries=2,
        retry_delay_base=2.0,
        retry_delay_max=30.0,
    )

    async def process(self, context: FlowContext) -> FlowContext:
        draft = context.get("ac1_draft", "")
        if not draft:
            context.set("gemini_review", {
                "verdict": "error",
                "objections": [],
                "summary": "No draft found in context. Expected key: ac1_draft",
            })
            return context

        if self.llm is None:
            raise RuntimeError(
                "GeminiAuditorSkill requires requires_llm=True and a configured gemini provider"
            )

        messages = [LLMMessage(role="user", content=f"Paper to audit:\n\n{draft}")]
        response = await self.llm.complete(
            messages=messages,
            system=_AUDITOR_SYSTEM_PROMPT,
            max_tokens=self.config.get("max_tokens", 4096),
        )

        raw = response.content.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        try:
            review = json.loads(raw)
        except json.JSONDecodeError:
            review = {
                "verdict": "error",
                "objections": [],
                "summary": f"Gemini returned non-JSON response: {raw[:200]}",
            }

        context.set("gemini_review", review)
        return context
