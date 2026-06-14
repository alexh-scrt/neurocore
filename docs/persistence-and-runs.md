# Persistence & runs

NeuroCore records every blueprint execution as a durable **run** with an ordered
list of **steps**. This turns a one-shot framework into an operable runtime: you
can inspect what happened, replay from inputs, and resume after a failure.

## Configuration

```yaml
# neurocore.yaml
persistence:
  enabled: true            # on by default
  backend: sqlite          # sqlite | memory
  path: runs.db            # relative to the data directory
  persist_step_snapshots: false   # store a full context snapshot per step
```

The SQLite database lives at `<data_dir>/runs.db` and uses only the Python
standard library (`sqlite3`) — no extra dependencies.

## CLI

```bash
neurocore runs list [--status suspended] [--blueprint research] [--limit 20]
neurocore runs inspect <run_id> [--full] [--json]
neurocore runs replay <run_id>
neurocore runs resume <run_id> [--data key=value ...]
neurocore runs approve <run_id> [--reject] [--note "..."] [--by you@example.com]
```

Run ids may be abbreviated to any unique prefix.

## Statuses

| Status | Meaning |
|--------|---------|
| `running` | in progress |
| `completed` | finished successfully |
| `failed` | raised an error (resume to retry from the failed step) |
| `suspended` | paused at an approval gate (resume/approve to continue) |

## Replay vs resume

- **Replay** re-executes the blueprint from its original `initial_data`, creating
  a *new* run. Deterministic re-run from inputs.
- **Resume** continues an existing `suspended` or `failed` run, skipping
  already-completed steps (tracked via `completed_nodes`).

## Programmatic API

```python
from neurocore.runtime.executor import execute_blueprint_tracked, resume_blueprint
from neurocore.persistence import build_run_store, RunStatus

store = build_run_store(config)
ctx = execute_blueprint_tracked(blueprint, registry, config, run_store=store)
if ctx.metadata.suspended:
    resume_blueprint(run_id, registry, config,
                     resume_data={"approved": True}, run_store=store)

for run in store.list_runs(status=RunStatus.SUSPENDED):
    print(run.run_id, run.suspended_at_node)
```

Implement the `RunStore` ABC (`save_run`, `save_step`, `load_run`, `load_steps`,
`list_runs`, `delete_run`) to add a Postgres or S3 backend.
