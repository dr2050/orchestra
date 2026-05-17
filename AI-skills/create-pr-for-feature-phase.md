Create or update a GitHub PR for the current feature-phase branch, targeting master, using the `07-pull-request-make.md` content from the feature-phase task directory.

Steps:

1. Determine the current branch: `git branch --show-current`
2. Derive the phase slug from the branch name by taking the final branch path segment (for example `auv3/phase6-basic-host-state-restore` → `phase6-basic-host-state-restore`).
3. Resolve the feature-phase task directory by searching `Orchestration/projects/*/{phase-slug}` on disk.
   - If exactly one matching directory exists, use it.
   - If more than one matching directory exists, ask the user which feature directory to use.
   - If none exist, stop and tell the user no matching feature-phase directory was found.
4. Read `Orchestration/projects/{feature}/{phase-slug}/07-pull-request-make.md`. If it does not exist or has no content, stop and tell the user to run pull-request-make first.
5. Extract the PR title and body from `07-pull-request-make.md` (the most recent block in Current State).
   - Build the PR body from the `## Why`, `## Work`, and `## Other` sections in that block.
   - Ensure the final PR body always includes a GitHub task-list **Test Plan** section.
   - If the source block already contains a `## Test Plan` section, keep it.
   - If it does not, append:
     ```
     ## Test Plan
     - [ ] Build the relevant target(s)
     - [ ] Exercise the changed flow manually
     - [ ] Verify the expected post-change behavior
     ```
6. Check for a pull-request review file in this order:
   - `Orchestration/projects/{feature}/{phase-slug}/07-pull-request-review.md`
   - `Orchestration/projects/{feature}/{phase-slug}/08-pull-request-review.md`
   If either file exists, read the entire Log section (all review rounds, not just the latest). Synthesize a high-level **Review** section to append to the PR body:
   - Read all Problems entries across every review round in the log.
   - Write a short bulleted list that summarizes the categories of problems that were found and fixed (e.g. "Direction edge-case after portrait resize", "Wrong duplicate landscape zoom occurrence restored after rebuild"). One bullet per distinct problem type — not per review round. Keep each bullet concise and human-readable.
   - If the final review round has no problems (approved), frame the bullets as issues that were identified and resolved.
   - Format:
     ```
     ## Review
     Issues found and resolved during review:
     - {synthetic bullet}
     - {synthetic bullet}
     ```
   - If neither review file exists, omit the Review section entirely.
   - If a Review section is appended, place it after `## Other` and before `## Test Plan`.
7. Push the current branch: `git push -u origin HEAD`
8. Check if a PR already exists for this branch: `gh pr list --head {branch} --json number,url`
   - If a PR exists: update it with `gh api repos/{owner}/{repo}/pulls/{number} -X PATCH -f title=... -f body=...`
   - If no PR exists: create it with `gh pr create --title ... --body ... --base master`
9. Report the PR URL to the user.
