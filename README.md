# Orchestra

Orchestration harness for AI-driven development workflows.

## Runtime

Orchestra uses a checkout-local Python environment at `.venv/`. In the shared
deployment, create or update it with:

```bash
export ORCHESTRA_DIR=/Users/Shared/orchestra
"$ORCHESTRA_DIR/shared_scripts/bootstrap-python-env.sh"
export PATH="$ORCHESTRA_DIR/bin:$PATH"
```

Human-facing commands are the `ko-*` wrappers in `bin/`:

```bash
ko-task list
ko-dashboard
ko-orchestrator
ko-get-update
ko-feature-orchestrator
ko-feature-dashboard
```

The wrappers use `$ORCHESTRA_DIR/.venv/bin/python` and fall back to the checkout
containing the wrapper when `ORCHESTRA_DIR` is unset.

## Systems

- [Feature-Phase Orchestration](feature-phase-orchestration/README.md) —
  end-to-end pipeline for feature planning, phase execution, code review,
  and pull request synthesis.
