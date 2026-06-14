# human-approval-agent

Demonstrates NeuroCore's **human-in-the-loop** approval gate: the flow drafts an
action, *suspends* for a human decision, and only sends after approval. No API
keys required.

```bash
# 1. Run — it suspends at the approval gate.
neurocore run blueprints/approve.flow.yaml --data topic="delete prod database"

# 2. See the pending approval.
neurocore runs list --status suspended

# 3. Approve (or --reject) to resume.
neurocore runs approve <run_id> --by you@example.com
#   neurocore runs approve <run_id> --reject --note "too risky"
```

The `approval:` step desugars to the built-in `approval` skill. A rejected run
ends as `failed`; an approved run resumes and completes.
