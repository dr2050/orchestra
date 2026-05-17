Create and publish a GitHub PR for the current branch, targeting master.

Steps:

1. Determine the current branch: `git branch --show-current`. If it is `master`, stop and tell the user to switch to a feature branch.
2. Verify there are commits on the branch vs master: `git log master..HEAD --oneline`. If empty, stop and tell the user there is nothing to PR.
3. Inspect the branch contents to draft a title and body:
   - `git log master..HEAD --reverse --pretty=format:'%s%n%n%b'` for commit history
   - `git diff master...HEAD --stat` for scope
4. Draft a PR title (under 70 chars) and a body with these sections:
   - `## Summary` — 1–3 bullets on what changed and why.
   - `## Review` (optional) — scan the commit log for follow-up/fix commits (subjects starting with `fix`, `address`, `review`, `cr`, or commits that revise earlier work in the same branch). Synthesize one bullet per distinct issue category that was identified and resolved during the branch's life. Format:
     ```
     ## Review
     Issues found and resolved during development:
     - {synthetic bullet}
     - {synthetic bullet}
     ```
     If no such commits exist, omit the section entirely.
   - `## Test Plan` — GitHub task-list:
     ```
     - [ ] Build the relevant target(s)
     - [ ] Exercise the changed flow manually
     - [ ] Verify the expected post-change behavior
     ```
   Order: Summary → Review (if present) → Test Plan.
5. Push the current branch: `git push -u origin HEAD`
6. Check if a PR already exists for this branch: `gh pr list --head {branch} --json number,url`
   - If a PR exists: update it with `gh api repos/{owner}/{repo}/pulls/{number} -X PATCH -f title=... -f body=...`
   - If no PR exists: create it with `gh pr create --title ... --body ... --base master`
7. Report the PR URL to the user.
