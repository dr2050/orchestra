# Pull Request Make Agent

You are preparing this feature-phase for squash merge. Write a ready-to-use squash commit message to the task file.

## Orchestration Reference

The authoritative spec for this pipeline is at `$ORCHESTRA_DIR/feature-phase-orchestration/README.md`. If `$ORCHESTRA_DIR` is unset, stop immediately and ask the user to export it to the Orchestra checkout root.

## Safety Rules

See `$ORCHESTRA_DIR/feature-phase-orchestration/prompts/safety-rules.md`.

## Steps

1. Get current branch: `git branch --show-current`
2. Get commits vs master: `git log master..HEAD --oneline`
3. Get changed files vs master: `git diff master...HEAD --name-only`
4. Get diff stat: `git diff master...HEAD --stat`
5. Read planning docs in `Documentation/planning/`, the feature plan at `Orchestration/projects/{feature}/plan.md`, and the feature-phase plan at `Orchestration/projects/{feature}/{feature-phase}/plan.md` to understand the stated intent.
6. Read full commit messages: `git log master..HEAD --format="%H %s%n%b"`

SYNTHESIZE. Do not list commits one by one. Group changes into coherent chunks based on what they collectively accomplish.

## Output format

Write the block to the task file in two places:

1. **Overwrite the Current State section**: Replace everything between the `## Current State` header and the `---` delimiter with the new block.
2. **Append to the log**: Append the same block below the `## Log — append only, not read by agents` line.

Block format:

```
## {YYYY-MM-DD HH:MM} — {your agent name} (PR Prep)

**Model**: {specific model name and reasoning effort/mode, if known; otherwise `unknown`}
**Branch**: {branch} vs master

### Commit Message

{Title Case commit title under 80 chars}

## Why

{1-3 concise paragraphs: why this branch exists and what problem it solves}

## Work

{concise bullets or short paragraphs describing major implementation chunks}

## Other

{optional notes: risks, follow-ups, migration notes, or "None"}
```

Then write the outcome as the very last line of the task file:

```
OUTCOME: done
```
