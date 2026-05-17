# Proposal: task_skips Table

Replace the `skip_commit_plan` boolean column with a normalized `task_skips` table. The supported skip targets are exactly four steps: `commit-plan`, `commit-plan-review`, `commit-review`, and `commit-review-supertask`.

## Schema change

Remove from `tasks`:
```sql
skip_commit_plan  INTEGER NOT NULL DEFAULT 0
```

Add new table:
```sql
CREATE TABLE task_skips (
    task_id  INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    step     TEXT    NOT NULL
                     CHECK(step IN ('commit-plan','commit-plan-review',
                                    'commit-review','commit-review-supertask')),
    PRIMARY KEY (task_id, step)
);
```

The `CHECK` constraint is the authoritative guardrail. CLI and orchestrator validation are a second layer that provides a friendlier error message before the DB is touched.

## Orchestrator changes

Replace `task["skip_commit_plan"]` checks with:
```python
def should_skip_step(conn, task_id, step):
    return conn.execute(
        "SELECT 1 FROM task_skips WHERE task_id = ? AND step = ?",
        (task_id, step)
    ).fetchone() is not None
```

Transition rules for each supported skip:

- **skip `commit-plan`**: new task starts at `commit-make` instead of `commit-plan`.
- **skip `commit-plan-review`**: after plan drafting succeeds, advance directly to `commit-make` instead of waiting for plan review.
- **skip `commit-review`**: after `commit-make` succeeds, execute the exact same state transitions and side effects as the existing approval path (i.e. the code that runs when `last_review_decision = 'approve'`). No review agent is started.
- **skip `commit-review-supertask`**: after supertask planning succeeds, execute the exact same state transitions and side effects as the existing supertask-review approval path (i.e. the code that runs when `last_review_decision = 'approve'` for a supertask review). No review agent is started.

## CLI changes

`task add` gets `--skip <step>` (repeatable). Replaces `--skip-commit-plan`. Only the four step names above are accepted; unknown names are rejected with an error. Duplicate `--skip` values for the same step are silently ignored.

```bash
task add "title" --skip commit-plan --skip commit-review
```

`task set` gets `--add-skip <step>` / `--remove-skip <step>` for post-creation edits. Same validation applies: unsupported step names are rejected.

Skip edits are prospective only. `--add-skip` and `--remove-skip` update `task_skips` immediately; the orchestrator applies the change the next time it reaches that transition point. The CLI does not proactively rewrite in-flight task state.

## User contract

### Commands

```bash
# At creation time (repeatable; duplicates silently ignored)
task add "title" --skip commit-plan --skip commit-review

# After creation
task set <id> --add-skip <step>
task set <id> --remove-skip <step>
```

Both `--skip` and `--add-skip` / `--remove-skip` reject any step name not in the supported set; the error message lists the four valid names.

### Prospective-only semantics

Skip edits take effect the next time the orchestrator evaluates that transition. `--add-skip` and `--remove-skip` write to `task_skips` immediately; no in-flight task state is rewritten by the CLI.

### Visibility in `task show`

`task show <id>` outputs JSON. The task object gains a `skips` field: a list of active skip step names for that task (empty list if none). Example:

```json
{ "id": 7, "title": "...", "skips": ["commit-plan", "commit-review"], ... }
```

The implementation should populate this field from `task_skips`; the exact query/helper shape is up to the builder.

### Supported targets by task kind

| Step | Normal task | Supertask |
|------|-------------|-----------|
| `commit-plan` | yes | no |
| `commit-plan-review` | yes | no |
| `commit-review` | yes | no |
| `commit-review-supertask` | no | yes |

Applying a normal-task skip to a supertask (or vice versa) is rejected with a validation error.

## Spec update

Update `kanban-orchestra-spec.md` in-place: replace the `skip_commit_plan` column description with the `task_skips` table and the four supported skip targets. No version history section.

## Upgrade path

DB is local and expendable. The normal upgrade path is delete and recreate:
```bash
rm kanban-orchestra.db && python3 kanban.py
```

`_check_schema_compatible` rejects three stale shapes:
- DB missing the `task_skips` table.
- DB where `task_skips` exists but its DDL does not include the `CHECK` constraint on `step` (detected via `sqlite_master.sql` inspection).
- DB still carrying the legacy `tasks.skip_commit_plan` column.

All three produce a clear error directing the user to regenerate the DB. No runtime migration logic in `db.connect()`.

The implementer must also produce a throwaway migration script. It must not be wired into the main code path, and it is intended for one-off/manual use only. It may remain in the repo for reuse against other local databases in other repos. The script should copy any `skip_commit_plan = 1` rows into `task_skips` with `step = 'commit-plan'`, then recreate the `tasks` table without `skip_commit_plan` using SQLite's rename-recreate-copy-drop pattern.
