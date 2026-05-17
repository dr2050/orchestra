**Note**: This is the ad-hoc manual workflow, not the orchestrated pipeline. It reads/writes to `1-ad-hoc-ai-chatter/` and is used outside the orchestrator.

Respond to a reviewer handoff by reading `Orchestration/projects/1-ad-hoc-ai-chatter/review-notes.md` and acting on its findings.

Steps:
1. Read `Orchestration/projects/1-ad-hoc-ai-chatter/review-notes.md`.
2. Confirm the file is ready for builder action by checking `**Status**` is one of:
   - `Ready for builder — rejected`
   - `Ready for builder — approved`
   If not, stop and tell the user the review is not ready yet.
3. If status is `Ready for builder — approved`:
   - invoke the local git-commit helper (`/git-commit` or `$git-commit`)
4. If status is `Ready for builder — rejected`:
   - fix each listed issue
   - build with `fastlane alpha` to verify
   - invoke prep-for-review (`/prep-for-review` or `$prep-for-review`) for another review round
   - do not commit
5. After handling the review, update the `**Status**` line in `review-notes.md` to:
   - `**Status**: Builder processed`

Keep all updates append-only except replacing the single status line.
