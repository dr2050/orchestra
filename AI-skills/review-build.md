**Note**: This is the ad-hoc manual workflow, not the orchestrated pipeline. It reads/writes to `1-ad-hoc-ai-chatter/` and is used outside the orchestrator.

Review the latest build handoff by reading `Orchestration/projects/1-ad-hoc-ai-chatter/build-notes.md`, inspecting the code changes, and writing `Orchestration/projects/1-ad-hoc-ai-chatter/review-notes.md`.

Steps:
1. Read `Orchestration/projects/1-ad-hoc-ai-chatter/build-notes.md`.
2. Inspect the referenced code changes (or current changed files if the note is incomplete).
3. Set:
   - `Reviewed By` to the active assistant name (for example Claude or Codex)
   - `Model` to the most specific model identity known, including reasoning effort or mode when available, else `unknown`
4. Overwrite `Orchestration/projects/1-ad-hoc-ai-chatter/review-notes.md` with this structure:

```
# Review Notes

**Status**: Ready for builder — [approved | rejected | blocked]
**Reviewed By**: <assistant-name>
**Model**: <specific-model-name-and-reasoning-effort-or-unknown>

## Scope Reviewed
<files reviewed, one per line>

## Problems
<actionable defects only; if none, write `- No behavioural regressions detected in scoped changes.`>

## Notes
<non-blocking observations, confirmations, compatibility notes; omit if empty>

## Outcome
OUTCOME: [approved | rejected | blocked]
```

5. Update the `**Status**` line in `build-notes.md` to:
   - `**Status**: Processed by reviewer`

Rules:
- Keep findings focused on regressions and correctness risks.
- Do not propose unrelated feature work.
- Use repository-real file casing.
