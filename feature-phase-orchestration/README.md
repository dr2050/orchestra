# AI Orchestration Pipeline

## Key Terms

**Work Repo** — the git repository where software development work happens. This is the project being built (e.g., `midi-designer3`), not the Orchestra repo. All file edits, commits, and builds occur inside the Work Repo. The Work Repo keeps task state under `Orchestration/`; the Orchestra code itself is resolved through `$ORCHESTRA_DIR`, not an inline `orchestra/` symlink.

---

## Statuses
`idle` `ready` `in-progress`

- **idle** — not currently scheduled
- **ready** — queued, waiting for an AI to pick it up
- **in-progress** — an AI is working on it

## Outcomes
`none` `awaiting-review` `approved` `rejected` `done` `blocked` `error` `needs-human`

- **none** — no outcome yet for the current run
- **awaiting-review** — handoff to a review verb is required
- **approved** — review passed
- **rejected** — review found problems; loop back for fixes
- **done** — verb is complete and pipeline should advance
- **blocked** — logical impasse
- **error** — technical or tooling failure
- **needs-human** — requires a human decision

---

## Verbs
`plan-feature-make` `plan-feature-review` `plan-feature-phase-make` `plan-feature-phase-review` `commits-make` `commits-review` `pull-request-make` `pull-request-review`

- **plan-feature-make** — write the top-level feature plan
- **plan-feature-review** — review the top-level feature plan
- **plan-feature-phase-make** — write the detailed plan for one feature-phase branch
- **plan-feature-phase-review** — review the feature-phase plan before coding starts
- **commits-make** — implement changes, compile, and prepare one reviewable commit chunk
- **commits-review** — review the current commit only; loops back to `commits-make` if issues are found
- **pull-request-make** — synthesize the full branch into a ready-to-use squash commit message
- **pull-request-review** — review the full branch before merge

---

## File Structure

```
/projects
  /add-osc-support
    status.md
    plan.md
    01-plan-feature-make.md
    02-plan-feature-review.md
    /phase1-data-model
      status.md
      plan.md
      03-plan-feature-phase-make.md
      04-plan-feature-phase-review.md
      05-commits-make.md
      06-commits-review.md
      07-pull-request-make.md
      08-pull-request-review.md

/feature-phase-orchestration
  /feature-template
    status.md
    01-plan-feature-make.md
    02-plan-feature-review.md
  /feature-phase-template
    status.md
    03-plan-feature-phase-make.md
    04-plan-feature-phase-review.md
    05-commits-make.md
    06-commits-review.md
    07-pull-request-make.md
    08-pull-request-review.md
  /prompts
    01-plan-feature-make-prompt.md
    02-plan-feature-review-prompt.md
    03-plan-feature-phase-make-prompt.md
    04-plan-feature-phase-review-prompt.md
    05-commits-make-prompt.md
    06-commits-review-prompt.md
    07-pull-request-make-prompt.md
    08-pull-request-review-prompt.md
    dashboard-live-update-prompt.md
  /scripts
    orch-dashboard.py
    orchestrator.py

/AI-skills
  prep-for-feature-phase-build.md
  prep-for-review.md
  review-build.md
  respond-to-review.md
  prep-branch-for-squash-merge.md
  squash-merge-branch.md

/shared_scripts
  shared_config.py
```

---

## Rules

- **Orchestrator updates `status.md`, not task filenames.**
- **Feature planning and feature-phase execution are separate work units.**
- **Feature plan approval does not auto-start a feature-phase.** A human must create or update the feature-phase directory and set `plan-feature-phase-make: status=ready`.
- **Files are append-only logs.** Each AI round appends to the bottom with a timestamp and name.
- **Orchestrator scans status files** once per second and processes exactly one ready verb at a time.
- **Each verb line stores scheduler state and latest result** in the format `status=<...> outcome=<...>`.
- **Diffs are small and focused** — one logical change per session.
- **Killswitch** — rename `killswitch-off.md` to `killswitch-on.md` to freeze everything.
- **Task files stay in git.** The code gets squashed; the task logs are the narrative record.
- **AI skill docs are canonical in `AI-skills/`.**
- **Dashboard live summaries are advisory.** The AI summary is a compact read of the current state, not the source of truth.

---

## Task File Format

```
## 2026-02-26 14:32 — Codex
**Model**: gpt-5
...

OUTCOME: awaiting-review
```

---

## Workflow

### Feature Plan Loop

```
plan-feature-make: status=ready outcome=none
  → status=in-progress outcome=none
  → OUTCOME: awaiting-review
  → status=idle outcome=awaiting-review
  → queue plan-feature-review as status=ready outcome=none
    → OUTCOME: approved  → stop; human must start a feature-phase manually
    → OUTCOME: rejected  → queue plan-feature-make as status=ready outcome=none
```

### Feature-Phase Plan Loop

```
plan-feature-phase-make: status=ready outcome=none
  → status=in-progress outcome=none
  → OUTCOME: awaiting-review
  → status=idle outcome=awaiting-review
  → queue plan-feature-phase-review as status=ready outcome=none
  → OUTCOME: approved  → queue commits-make as status=ready outcome=none
    → OUTCOME: rejected  → queue plan-feature-phase-make as status=ready outcome=none
```

### Commit Loop

```
commits-make: status=ready outcome=none
  → status=in-progress outcome=none
  → OUTCOME: awaiting-review
  → status=idle outcome=awaiting-review
  → queue commits-review as status=ready outcome=none
    → OUTCOME: approved  → queue commits-make (next chunk)
    → OUTCOME: rejected  → queue commits-make (fix loop)
    → OUTCOME: done      → queue pull-request-make
```

### Pull Request Loop

```
pull-request-make: status=ready outcome=none
  → status=in-progress outcome=none
  → OUTCOME: done
  → status=idle outcome=done
  → queue pull-request-review as status=ready outcome=none
    → OUTCOME: approved  → ready for human merge
    → OUTCOME: rejected  → queue commits-make
```

Blocked, error, and needs-human outcomes idle the verb and stop automatic advancement.

---

## Kickoff

Export `$ORCHESTRA_DIR` to the Orchestra checkout root before running any of these commands.

### 1. Create the feature directory

```bash
cp -r "$ORCHESTRA_DIR"/feature-phase-orchestration/feature-template Orchestration/projects/{feature}
```

### 2. Write the feature goal

Write the feature goal into `01-plan-feature-make.md`.

### 3. Set the feature verb to ready

Edit `Orchestration/projects/{feature}/status.md` and set:

```text
- plan-feature-make: status=ready outcome=none
```

### 4. Run the orchestrator

```bash
ko-feature-orchestrator
```

Optional: run the live dashboard with AI summaries:

```bash
ko-feature-dashboard
```

### 5. Start a feature-phase after the feature plan is approved

```bash
cp -r "$ORCHESTRA_DIR"/feature-phase-orchestration/feature-phase-template Orchestration/projects/{feature}/{feature-phase}
```

Then set this line in the feature-phase `status.md`:

```text
- plan-feature-phase-make: status=ready outcome=none
```

Shortcut: run `/prep-for-feature-phase-build` to automate the feature-phase directory setup.

---

## Chrono Updates

### 2026-02-24 — Implementation

Workspace moved into `Orchestration/`. No separate `/diffs` directory.

### 2026-03-18 — Workflow Split

Feature planning moved to top-level feature directories with `01/02`.
Feature-phase execution directories now start at `03` and continue through `08`.
Feature plan approval no longer auto-starts a feature-phase.

### 2026-03-19 — Random Agent Selection

Removed per-verb agent mapping. The orchestrator now picks randomly from the three available agents (claude, codex, gemini) on each verb invocation.
