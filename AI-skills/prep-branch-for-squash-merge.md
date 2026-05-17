Produce a squash-merge commit message for the whole branch vs master, then overwrite `Orchestration/projects/1-ad-hoc-ai-chatter/squash-merge-notes.md` with it.

Steps:

1. Get the current branch name: `git branch --show-current`
2. Get all commits on this branch vs master: `git log master..HEAD --oneline`
3. Get all files changed vs master: `git diff master...HEAD --name-only`
4. Get the full diff summary (stat only, no patch): `git diff master...HEAD --stat`
5. Look for planning documents: `ls Documentation/planning/` and read any `.md` files there to understand stated intent.
6. Read commit messages in full: `git log master..HEAD --format="%H %s%n%b"` to understand the work done.

Now synthesize. Do not list commits one by one. Group changes into coherent logical chunks based on what they collectively accomplish.

Write `Orchestration/projects/1-ad-hoc-ai-chatter/squash-merge-notes.md` with this exact structure (overwrite completely):

```
<Title Case commit title under 80 chars>

## Why

<1-3 concise paragraphs: why this branch exists and what problem it solves>

## Work

<concise bullets or short paragraphs describing major implementation chunks>

## Other

<optional notes: risks, follow-ups, migration notes, or "None">
```

Rules:
- This output is the commit message source for `squash-merge-branch`.
- Keep it factual, concise, and human-readable.
- Do not add separate metadata blocks like "Squash merge title" or "Files Changed".
