# Agent Instructions

## Important Instruction Reminders

Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
NEVER include Claude/Codex/Gemini references or any mention of AI assistance in commit messages — always write commits as a single human author.
NEVER force-push. Do not run `git push --force` or `git push --force-with-lease`.

## Orchestra Directory

Skills and prompts reference the Orchestra repo via `$ORCHESTRA_DIR`.
Before running any skill that depends on Orchestra content, verify `$ORCHESTRA_DIR` is set and that `"$ORCHESTRA_DIR"/AI-skills` exists.
If `$ORCHESTRA_DIR` is unset or invalid, stop and tell the user: `export ORCHESTRA_DIR=/path/to/orchestra`.
