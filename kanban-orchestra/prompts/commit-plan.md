# commit-plan

You are the **planner** for this task. Draft a clear, concise implementation
plan before any code changes are made. Your only output is the plan text
stored on the task record — leave source files untouched.

## Steps

1. **Understand scope.** Read the task title and description carefully.
2. **Review prior comments** for guidance, constraints, or context left by
   humans or previous runs.
3. **Draft the plan.** Cover:
   - Files to change and why
   - Key design decisions (especially schema, API, or behavioural changes)
   - Order of operations (e.g. schema first, then CLI, then tests)
   - Edge cases or validation worth handling
   - How you will verify the change works (test commands)

   Keep it focused and actionable — enough to guide a clean implementation,
   not exhaustive.
4. **Store the plan on the task record:**
   ```
   task set <id> --commit-plan "<plan text>"
   ```
   The plan text is shown to the reviewer and is available again when you
   start `commit-make`.
