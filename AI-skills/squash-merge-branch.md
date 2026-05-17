Squash-merge a branch into master and commit using the latest available squash-merge notes.
Target branch: `master`.

Branch selection rules:
- If a branch name argument is provided (for example `/squash-merge-branch 2026-02-auv3/phase3` or `$squash-merge-branch 2026-02-auv3/phase3`), use it.
- If no argument is provided and current branch is not `master`, use the current branch as source and switch to `master`.
- If no argument is provided and current branch is `master`, ask which branch to merge and suggest the most recently updated local branch that is not `master`.

Steps:

1. Resolve the source branch using the rules above. Validate it exists locally.
2. Ensure target branch is `master`:
   - If currently not on `master`, run `git checkout master`.
   - If checkout fails, stop and report the error.
3. Resolve the input notes file from disk, in this order:
   - Look for `Orchestration/projects/*/07-pull-request-make.md` on disk in the feature-phase directory matching the source branch slug.
   - If not found, look for `Orchestration/projects/*/squash-merge-notes.md` on disk in the same way.
   - Final fallback: `Orchestration/projects/1-ad-hoc-ai-chatter/squash-merge-notes.md`.
   - If no candidate file exists on disk, stop and report missing notes source.
4. Extract commit message from the selected notes file:
   - Expected format is:
     - first line: commit title
     - body sections: `## Why`, `## Work`, `## Other`
    - If selected file is `07-pull-request-make.md`, extract the most recent `### Commit Message` block and use its content.
   - If selected file is `squash-merge-notes.md`, use the full file as commit message content.
   - Validate required sections exist (`## Why`, `## Work`, `## Other`); if missing, stop and report.
5. Run the squash merge: `git merge --squash <source-branch>`.
   This stages all changes but does not commit.
6. Update the notes file and stage it as part of the same commit:
   - If the selected notes file is `squash-merge-notes.md`: overwrite it with an empty file, then `git add` it.
   - If the selected notes file is `07-pull-request-make.md`: append a line of the form `\n---\nMerged into master <YYYY-MM-DD>.` to the file, then `git add` it.
7. Update plan files and stage them:
   - Look for a `plan.md` in the same feature-phase directory as the notes file (i.e. `Orchestration/projects/<project>/<feature-phase>/plan.md`).
   - If found, append a log entry to the bottom of the file:
     ```
     ## <YYYY-MM-DD> — Merged into master
     Branch `<source-branch>` squash-merged into master.
     ```
     Then `git add` it.
   - Also look for a parent feature `plan.md` one directory up (`Orchestration/projects/<project>/plan.md`).
   - If found and it contains a `- [ ]` checkbox line matching the phase name or branch slug, change it to `- [x]` and `git add` it.
8. Read staged files (`git diff --cached --name-only`) and present them for explicit human confirmation against the notes intent.
9. Show the user:
   - source branch and target branch
   - selected notes file path
   - commit title and first few lines of body
   - staged file list summary
   Ask for confirmation before committing.
10. Once confirmed, commit:
    `git commit -m "<Title>" -m "<Body>"`
11. Run `git status` to confirm success. Report result and remind user to push when ready.

Rules:
- Do not push automatically.
- Do not delete the branch automatically.
- The commit message must come verbatim from the selected notes file; do not rewrite or summarize it.
- No AI references in the commit message.
- Always require explicit user confirmation immediately before commit.
- Stop if required commit-message sections are missing or extraction fails.
