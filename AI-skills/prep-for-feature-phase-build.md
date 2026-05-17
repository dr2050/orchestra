Set up a task directory for a specific feature-phase of a project, ready for the orchestrator to pick up.

This workflow requires `$ORCHESTRA_DIR` to point at the Orchestra checkout root. If it is unset or invalid, stop and ask the user to export it before continuing.

Steps:

1. Ask the user for the feature folder name and phase number if not already provided (for example `2026-02-auv3-prep` and `3`).
2. Read the feature plan from `Orchestration/projects/{feature}/01-plan-feature-make.md`.
   - If that file does not exist, fall back to `Orchestration/projects/{feature}/plan.md` for older projects.
   - If neither file exists, stop and tell the user to create the feature plan first.
3. Find the specified feature-phase in the feature plan. Extract its title and suggested branch name.
4. Determine the feature-phase slug:
   - First, check the current git branch (`git branch --show-current`). If it matches the pattern `{feature}/phase{N}-*`, use the segment after `/` as the slug.
   - Otherwise, derive from the plan's branch name: if it includes a feature prefix like `2026-02-auv3-prep/phase3-midi-output-abstraction`, use the segment after `/`.
   - If no slug can be derived, derive from the feature-phase title using lowercase kebab-case.
5. Create the task directory by copying the template:
   ```bash
   cp -r "$ORCHESTRA_DIR"/feature-phase-orchestration/feature-phase-template Orchestration/projects/{feature}/{phase-slug}
   ```
   - If `Orchestration/projects/{feature}/{phase-slug}` already exists, stop and ask whether to reuse it or replace it.
6. Set `plan-feature-phase-make: status=ready outcome=none` in `Orchestration/projects/{feature}/{phase-slug}/status.md` (edit the line in place; leave all other verbs idle).

7. Tell the user:
   - What feature-phase directory was created
   - Which feature-phase from the feature plan it corresponds to
   - Which branch name was identified from the feature plan
   - That feature planning is separate and does not auto-start this directory
   - How to kick off: run `ko-feature-orchestrator`
