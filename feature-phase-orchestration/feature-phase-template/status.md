# Status

Managed by `$ORCHESTRA_DIR/feature-phase-orchestration/scripts/orchestrator.py`.
Set one verb to `status=ready` to queue work.
Orchestrator sets `status=in-progress` while running, then idles the verb with the final outcome.
Kick off a feature-phase by setting `plan-feature-phase-make` to `status=ready` manually after the feature plan is approved.

- plan-feature-phase-make: status=idle outcome=none
- plan-feature-phase-review: status=idle outcome=none
- commits-make: status=idle outcome=none
- commits-review: status=idle outcome=none
- pull-request-make: status=idle outcome=none
- pull-request-review: status=idle outcome=none
