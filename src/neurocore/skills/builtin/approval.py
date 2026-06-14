"""ApprovalSkill — a human-in-the-loop gate that pauses a run for sign-off.

On first execution the skill suspends the run (``context.suspend``). The
executor persists a SUSPENDED run; a human then approves or rejects via
``neurocore runs approve <run_id>``, which resumes the run with a decision in
``resume_data``. Approval continues the flow; rejection (when ``require`` is
true) fails the run.

Works on both execution paths: flowengine checkpoints the sync path, and
NeuroCore's async/DAG executor detects ``metadata.suspended`` after the step.

Blueprint usage — explicit component::

    components:
      - name: human_review
        type: approval
        config:
          message: "Approve sending the email?"
          require: true

or the ``approval:`` step sugar (desugars to the same component)::

    flow:
      steps:
        - component: draft_answer
        - approval: {name: human_review, require: true}
        - component: send_email
"""
from __future__ import annotations

from flowengine import FlowContext

from neurocore.errors import ExecutionError
from neurocore.skills.base import AsyncSkill, SkillMeta


class ApprovalSkill(AsyncSkill):
    """Suspend the run until a human approval decision is supplied.

    Implemented as an :class:`AsyncSkill` so that any blueprint containing an
    approval gate runs through NeuroCore's own async executor, which re-executes
    the suspended node with ``resume_data`` on resume. (flowengine's sync
    sequential resume skips the suspended node, which would bypass the
    decision.)
    """

    skill_meta = SkillMeta(
        name="approval",
        version="0.1.0",
        description="Pause the run and wait for a human approval decision.",
        author="NeuroCore",
        provides=["approval"],
        config_schema={
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Prompt shown to the approver.",
                },
                "require": {
                    "type": "boolean",
                    "description": "If true (default), a rejection fails the run.",
                },
            },
        },
        tags=["human-in-the-loop", "control", "builtin"],
    )

    async def process(self, context: FlowContext) -> FlowContext:  # type: ignore[override]
        # ``resume_data`` may arrive as a plain dict or flowengine's DotDict;
        # both support ``in`` / ``.get`` but DotDict is not a ``dict`` subclass.
        decision = context.get("resume_data")
        if decision is not None and hasattr(decision, "get") and "approved" in decision:
            # Resumed with a decision.
            context.set("approval", decision)
            context.delete("resume_data")
            require = self.config.get("require", True)
            if not decision.get("approved") and require:
                note = decision.get("note", "")
                raise ExecutionError(
                    f"Run rejected at approval gate '{self.name}'"
                    + (f": {note}" if note else "")
                )
            return context
        # First pass — pause for a human.
        message = self.config.get("message") or f"Approval required at '{self.name}'"
        context.suspend(node_id=self.name, reason=message)
        return context
