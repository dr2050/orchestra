**Note**: This is the ad-hoc manual workflow, not the orchestrated pipeline. It writes to `1-ad-hoc-ai-chatter/` and is used outside the orchestrator.

Prepare a build handoff by writing `Orchestration/projects/1-ad-hoc-ai-chatter/build-notes.md`. Overwrite it completely every time.

This workflow is agent-agnostic and reusable across CLI tools.

Steps:
1. Get the current branch with `git branch --show-current`.
2. Check whether changes are committed or only on disk with `git status --short`.
3. Ask the user (or infer from context) for the proposed commit message if one is not already known.
4. Get changed files:
   - If committed branch work is being summarized: `git diff --name-only master...HEAD`
   - If on-disk work is being summarized: `git diff --name-only`
5. Set:
   - `Prepared By` to the active assistant name (for example Claude or Codex)
   - `Model` to the most specific model identity known, including reasoning effort or mode when available, else `unknown`

Write `Orchestration/projects/1-ad-hoc-ai-chatter/build-notes.md` with this exact structure:

```
# Build Notes

**Status**: Waiting for review — code changes [on disk only, not yet committed | committed to branch]
**Prepared By**: <assistant-name>
**Model**: <specific-model-name-and-reasoning-effort-or-unknown>
**Review focus**: Refactor only — no new behaviour. Review for regressions only.
**Branch**: `<branch-name>`

---

## Proposed Commit — <commit title>

**Title**: <commit title>

**Body**:

<commit body>

---

## Files Changed
<list of changed files, one per line, use repository-real casing>

## Next Action
Reviewer should run `review-build`, write `review-notes.md`, and set the final outcome.
```

Keep it factual and concise. No extra commentary.
