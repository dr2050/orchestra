# Safety Rules

**Work Repo** — the project being built (e.g., `midi-designer3`), not the orchestra orchestration repo. See README for full definition. All file edits, commits, and builds occur inside the Work Repo.

- **Never** run `git push` under any circumstances.
- **Never** run `git push --force` or `git push --force-with-lease` under any circumstances.
- **Never** work outside the Work Repo.
- **Never** run destructive git operations (`reset --hard`, `clean -f`, `branch -D`, force push, etc.) — write `OUTCOME: needs-human` and stop.
- **Never** install software (`pip install`, `brew install`, `gem install`, etc.) — write `OUTCOME: needs-human` and stop.
- **Never** modify `.pbxproj` directly as a text file — use the xcode-tool. If you cannot, write `OUTCOME: needs-human` and stop.
- **Never** delete files outside the explicit scope of the task — write `OUTCOME: needs-human` and stop.
- When writing a `**Model**:` field, record the most specific model identity you actually know. Include the vendor/model family, version, and reasoning effort or mode when available, for example `GPT-5.5 medium`, `gpt-5.4 high`, or `Claude Sonnet 4.5`. Use `unknown` only when you cannot identify anything more specific than the agent name.
