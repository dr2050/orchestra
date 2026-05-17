# Status

Managed by `$ORCHESTRA_DIR/feature-phase-orchestration/scripts/orchestrator.py`.
Set one verb to `status=ready` to queue work.
Orchestrator sets `status=in-progress` while running, then idles the verb with the final outcome.
After `plan-feature-review` is approved, feature-phase planning does not auto-start.
Create or update a feature-phase directory, then set `plan-feature-phase-make` to `status=ready` manually.

- plan-feature-make: status=idle outcome=none
- plan-feature-review: status=idle outcome=none
