Synthesize a squash-merge commit message in memory and immediately squash-merge the branch into master — no intermediate files written.

## Branch Selection

- If a branch name argument is provided, use it.
- If no argument and current branch is not `master`, use current branch as source.
- If no argument and current branch is `master`, ask which branch to merge and suggest the most recently updated local branch that is not `master`.

## Steps

1. Resolve source branch using the rules above. Validate it exists locally.
2. Collect branch context in memory:
   - `git log master..HEAD --oneline` — commit list
   - `git log master..HEAD --format="%H %s%n%b"` — full commit messages
   - `git diff master...HEAD --stat` — change summary
   - `git diff master...HEAD --name-only` — file list
3. Synthesize a commit message in memory using this exact structure:

   ```
   <Title Case commit title under 80 chars>

   Why

   <1-3 concise paragraphs: why this branch exists and what problem it solves>

   Work

   <concise bullets (use • not -) or short paragraphs describing major implementation chunks>

   Other

   <optional notes: risks, follow-ups, migration notes, or "None">
   ```

   Rules:
   - Do not list commits one by one. Group changes into coherent logical chunks.
   - Do not describe changes by file or method name. Write what was done and why at a feature/behavior level. Git has the file-level changes, you don't need to repeat them.
   - Keep it factual, concise, and human-readable. Keep it positive, avoid saying what was NOT done.
   - No AI references.

4. Switch to master: `git checkout master`. Stop and report if checkout fails.
5. Run squash merge: `git merge --squash <source-branch>`.
6. Show the user for explicit confirmation:
   - Source branch and target branch
   - Full synthesized commit message
   Ask: "Proceed with commit?" Do not continue until confirmed.
8. Once confirmed, commit using the synthesized message verbatim.
9. Run `git status` to confirm success. Remind user to push when ready.

## Rules

- Do not push automatically.
- Do not delete the source branch automatically.
- Always require explicit user confirmation immediately before commit.
- No AI references in the commit message.
