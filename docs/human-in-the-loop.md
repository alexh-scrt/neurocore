# Human-in-the-loop

Production agents in legal, finance, healthcare, DevOps, and support need
**approval gates**. NeuroCore ships a built-in `approval` skill that suspends a
run until a human decides.

## The `approval:` step

Use the blueprint sugar — it desugars to a built-in `approval` component:

```yaml
flow:
  type: sequential
  steps:
    - component: draft_answer
    - approval:
        name: human_review
        message: "Approve sending this?"
        require: true        # a rejection fails the run
    - component: send_email
```

Equivalent explicit form:

```yaml
components:
  - name: human_review
    type: approval
    config: { message: "Approve sending this?", require: true }
```

## Lifecycle

1. The run reaches the gate and **suspends**; the run is persisted with status
   `suspended` (see [Persistence & runs](persistence-and-runs.md)).
2. A human reviews:

   ```bash
   neurocore runs list --status suspended
   neurocore runs approve <run_id> --by you@example.com
   #   neurocore runs approve <run_id> --reject --note "too risky"
   ```

3. On **approve**, the run resumes from the gate and continues. On **reject**
   with `require: true`, the run ends `failed`. The decision (`approved`,
   `note`, `by`) is written to the `approval` context key for downstream skills.

## How it works

`ApprovalSkill` is an `AsyncSkill` that calls `context.suspend(...)` on first
pass. Because it's async, the blueprint runs through NeuroCore's own executor,
which re-executes the suspended node with the injected `resume_data` on resume —
so the gate actually consumes the decision. See the
[`human-approval-agent` example](https://github.com/alexh-scrt/neurocore/tree/master/examples/human-approval-agent).
