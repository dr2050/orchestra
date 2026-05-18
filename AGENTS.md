# Repository Instructions

## Working Principles

- State assumptions explicitly; do not guess silently.
- Prefer the minimum code needed to solve the problem.
- Make surgical changes; do not refactor adjacent code unless required.
- Define what success looks like, then verify the change against it.
- If verification fails, iterate until the issue is resolved or the blocker is clearly explained.

There is no build step for this repo.

ALLOW_TASKS_ON_MASTER

Before staging changes, run the unit tests from this checkout:

```bash
bin/ko-test
```

Use the repo-local paths above directly.
