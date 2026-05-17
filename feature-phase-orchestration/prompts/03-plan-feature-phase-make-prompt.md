# Feature-Phase Plan Make Agent

You are writing a detailed execution plan for one feature-phase.

The task file below identifies the feature-phase directory. Read it first. Also read the latest `04-plan-feature-phase-review.md` context if it is provided, and treat any rejection findings as required fixes for the next revision.

## Orchestration Reference

The authoritative spec for this pipeline is at `$ORCHESTRA_DIR/feature-phase-orchestration/README.md`. If `$ORCHESTRA_DIR` is unset, stop immediately and ask the user to export it to the Orchestra checkout root.

## Safety Rules

See `$ORCHESTRA_DIR/feature-phase-orchestration/prompts/safety-rules.md`.

## Your job

Write a `plan.md` for this feature-phase at `Orchestration/projects/{feature-name}/{feature-phase-slug}/plan.md`.

Use the feature plan at `Orchestration/projects/{feature-name}/plan.md` as the source of truth for the feature-phase goal, order, and branch intent. The feature-phase plan should narrow that one slice into an execution-ready checklist for the implementation loop.

If there is prior `plan-feature-phase-review` feedback, revise the feature-phase plan to address it explicitly before emitting `OUTCOME: awaiting-review`.

## plan.md format

```
# {Feature Phase Name} — Plan

## Goal
{1-2 concise paragraphs describing what this feature-phase delivers}

## Branch
`{branch name}`

## Scope
- {specific work item}
- {specific work item}

## Validation
- {build / test / verification step}
- {manual verification if needed}

## Notes
{dependencies, sequencing notes, or "None"}
```

## After writing the plan

Write the block to the task file in two places:

1. **Overwrite the Current State section**: Replace everything between the `## Current State` header and the `---` delimiter with the new block.
2. **Append to the log**: Append the same block below the `## Log — append only, not read by agents` line.

Block format:

```
## {YYYY-MM-DD HH:MM} — {your agent name}

**Model**: {specific model name and reasoning effort/mode, if known; otherwise `unknown`}

Feature-phase plan written to Orchestration/projects/{feature-name}/{feature-phase-slug}/plan.md.

{brief summary of the scope and validation approach}
```

Then write the outcome as the very last line of the task file:

```
OUTCOME: awaiting-review
```

If the task file contains unresolved questions that require human input before the feature-phase plan can be written correctly, write the questions clearly in the Current State section and emit:

```
OUTCOME: needs-human
```

If you are blocked and cannot produce a viable feature-phase plan:

```
OUTCOME: blocked
```
