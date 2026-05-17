Trigger a restart of the claude-discord supervisor by dropping the restart file.

## Steps

1. Write the desired restart prompt to `$CLAUDE_DISCORD_RESTART_FILE`. An empty file is valid and restarts with no initial prompt.

```bash
echo "your restart prompt here" > "$CLAUDE_DISCORD_RESTART_FILE"
```

The supervisor detects the file within 2 seconds, kills the current Claude process, and relaunches it with the file contents as the opening prompt.
