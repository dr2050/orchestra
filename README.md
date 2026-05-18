# Orchestra

Orchestra is local infrastructure for agent-driven development work. It is
Python that moves configured local agent CLIs through a SQLite-backed task
queue. A task is scoped to one git commit: the system prompts an agent to make
the change, can route the staged diff through review/rejection cycles, and then
finalizes the approved commit.

This is not meant to be a human-facing CLI product. Humans should not normally
drive the task CLI by hand. The intended interface is: install the skills into
your local agent setup, invoke the Kanban skill, and ask the AI to queue or run
a task.

## For Users

1. Clone the repo:

   ```bash
   git clone https://github.com/dr2050/orchestra.git /path/to/orchestra
   ```

2. Set `ORCHESTRA_DIR` to this checkout in your shell startup file (`.zshrc`,
   `.bashrc`, or equivalent):

   ```bash
   export ORCHESTRA_DIR="/path/to/orchestra"
   ```

3. Build Orchestra's checkout-local Python environment:

   ```bash
   "$ORCHESTRA_DIR/shared_scripts/bootstrap-python-env.sh"
   ```

4. Sync the canonical skills **into each repo** where you want to use Orchestra:

   ```bash
   cd /path/to/work-repo
   "$ORCHESTRA_DIR/bin/ko-sync-skills"
   ```

5. Start one `orchestra-ui` for each work repo:

   ```bash
   "$ORCHESTRA_DIR/bin/ko-ui"
   ```

   Use the Browser button in `orchestra-ui` to open the HTML dashboard. 
   
6. In your work repository, use your local AI agent and invoke the `kanban` skill. The normal request is
   plain language, for example: "Using the Kanban skill, queue a task to fix
   X." The skill handles bootstrapping, task creation, status checks, and
   wrapper commands. Frontier models can also figure out why the orchestra might be blocked, and how to unblock it.

### Notes

* Orchestra will not launch against a dirty worktree.
* Queued runs can block if the worktree becomes dirty between task runs. Therefore, the agent who has run the `kanban` skill should not modify the work tree.
* Have your agent set your task to `none` status until you're ready to have it
  picked up. Then set it to `ready`.
* An agent using the Kanban skill can adjust task details before launch,
  including adding/removing skipped steps, changing the coding agent, and
  changing the review agent. An agent that has run the `kanban` skill will be well-equipped to help.

## For Developers Of This Repo

Skip the orchestration workflow unless you are intentionally testing it. Treat
this as a normal Python repo:

```bash
export ORCHESTRA_DIR="/path/to/orchestra"
"$ORCHESTRA_DIR/shared_scripts/bootstrap-python-env.sh"
"$ORCHESTRA_DIR/bin/ko-test"
```

## Source Layout

- `$ORCHESTRA_DIR/AI-skills/` contains the canonical skill instructions.
  Generated agent-local skill folders such as `.claude/`, `.codex/`,
  `.gemini/`, and `.agents/` are local artifacts and are ignored in this repo.
- `$ORCHESTRA_DIR/kanban-orchestra/scripts/` contains the Python task queue,
  dashboard, orchestrator, and task CLI implementation.
- `$ORCHESTRA_DIR/kanban-orchestra/prompts/` contains the prompts injected into
  task agents.
- `$ORCHESTRA_DIR/bin/` contains thin wrappers that run scripts through the
  checkout-local Python environment.
- `$ORCHESTRA_DIR/shared_scripts/` contains optional setup/helper scripts.

## Operating Model

Kanban state lives in the work repo, not in the Orchestra checkout:

- `kanban-orchestra.db` stores task state.
- `.kanban-orchestra/` stores runtime files and logs.
- The work repo's current branch is the branch the task should target unless
  the task says otherwise.

The Kanban skill is the gateway for normal work. It bootstraps a work repo,
queues tasks, checks stuck state, and uses wrappers as
`"$ORCHESTRA_DIR/bin/..."` so no global `PATH` install is required.

Manual wrapper commands exist for debugging and for the skill to call, but they
are not the preferred human workflow.

The orchestrator expects a clean worktree. It refuses to launch when the work
repo is dirty and blocks rather than continuing through unexpected uncommitted
changes.

## Agent Configuration

Orchestra does not provide hosted model access, accounts, subscriptions, API
keys, or provider billing. It shells out to whatever local agent commands are
configured on the machine.

Review `$ORCHESTRA_DIR/shared_scripts/shared_config.py` before running the
orchestrator. That file maps logical agent names to local command lines.
Install and authenticate only the agent CLIs you intend to use, then adjust
the config or environment defaults for your machine.

Default agent roles can also be overridden with environment variables:
set each one to an agent key configured in
`$ORCHESTRA_DIR/shared_scripts/shared_config.py`.

```bash
export ORCHESTRA_DEFAULT_CODER=haiku
export ORCHESTRA_DEFAULT_REVIEWER=codex
export ORCHESTRA_DEFAULT_PLANNER=sonnet
export ORCHESTRA_DEFAULT_PLAN_REVIEWER=codex
export ORCHESTRA_DEFAULT_SUPER_PLANNER=sonnet
export ORCHESTRA_DEFAULT_SUPER_REVIEWER=codex
```

## Policies

Orchestra is not a sandbox or permission boundary. Configured agent commands
run as your local user and may read or write files available to that user.

Automatic task execution expects non-interactive agent CLI modes. If an agent
requires a permission prompt for every command or file edit, queued work cannot
complete reliably.

Branch safety is handled separately: tasks on `master` or `main` are blocked
by default unless the work repo explicitly opts in with
`ALLOW_TASKS_ON_MASTER` in its root `AGENTS.md`.

## License

Orchestra is available under the MIT License. See [LICENSE](LICENSE).
