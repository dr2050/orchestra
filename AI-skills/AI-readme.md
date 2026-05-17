# AI Agent Command/Skill Docs

How each agent discovers and loads custom commands and skills:

- **Claude**: https://code.claude.com/docs/en/slash-commands
- **Gemini CLI**: https://geminicli.com/docs/cli/gemini-md/
- **Codex (skills)**: https://developers.openai.com/codex/skills
- **Codex (AGENTS.md)**: https://developers.openai.com/codex/guides/agents-md

---

## Adding a Skill to All Three Agents

All skills live in `AI-skills/{skill-name}.md` as the canonical source. Each agent gets a thin wrapper in its own skills directory that points to the canonical file.

### 1. Write the canonical skill

Create `AI-skills/{skill-name}.md` with the instructions the agent should follow.

### 2. Start the skill file with a one-line summary

The wrapper sync script reads `AI-skills/{skill-name}.md` directly. It uses the first non-empty line of the file as the wrapper description, so keep that opening line short and descriptive.

### 3. Sync wrappers into the target repo

From the repo that should receive the wrappers:

```bash
ko-sync-skills
```

This creates or refreshes:

- `.claude/skills/{skill-name}/SKILL.md`
- `.gemini/skills/{skill-name}/SKILL.md`
- `.codex/skills/{skill-name}/SKILL.md`
- `.agents/skills/{skill-name}/SKILL.md`

Each wrapper uses the same thin shared format:

```markdown
---
name: {skill-name}
description: {one-line description}
---

Follow the shared skill:

- Location: $ORCHESTRA_DIR/AI-skills/{skill-name}.md
- Least Seen at: /absolute/path/to/orchestra/AI-skills/{skill-name}.md
```
