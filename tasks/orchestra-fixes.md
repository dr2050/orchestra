# CHANGES

## 2026-03-18 Changes

### Commits

#### 1. Fix Verbs in Prompts [DONE]

The verbs are all crossed up and messy. Let's go with this scheme. Note that you'll have to rename in lots of text files that refer to the old names. 

* 01-plan-make.md
* 02-plan-review.md
* 03-commits-make.md
* 04-commits-review.md
* 05-pull-request-make.md
* 06-pull-request-review.md

Also rename: `feature-phase-build-template` should be `feature-phase-template`

Also add "-prompt" to every prompt.

NOTE: You'll also have to rename the prompts, and the python files that use all this shit.

#### 2. Split feature planning and review from (non-existent now) Feature-Phase Planning and Review.

THE BUG: the outer plan for the "project" is for the Feature. The plan.md and review_plan.md (now 01-plan-make.md 02-plan-review.md) are referring to that quite clearly. 

I guess the best way to go is to add the feature planning to the orchestrator and create 03 and 04 (new).

* 01-plan-feature-make.md
* 02-plan-feature-review.md
* 03-plan-feature-phase-make.md
* 04-plan-feature-phase-review.md
* 05-commits-make.md
* 06-commits-review.md
* 07-pull-request-make.md
* 08-pull-request-review.md

Note: `prep-for-feature-phase-build.md` is affected and others may be too. That prep skill probably needs to be paired down. Because it doesn't really need to fill in the feature-phase plan anymore. 

Somehow we honestly need a feature-template directory which has skeletons of these two:
* 01-plan-feature-make.md
* 02-plan-feature-review.md

In Python: Feature Plan approved shouldn't go automatically anywhere. 03 needs to get status set manually. Status file should mention this.

#### 3. Dashboard Gets AI! Agent helps with reviewing changes.

We need a new section added to the orch-dashboard that gives VERY summary output about what's happening in orchestration. We've now got four cycles: feature plan, feature-phase plan, commit, and PR. And in each of those we've got a MAKE and a Review. So I'd love a brief summary of where we are.

Important: feature planning and feature-phase execution are separate now. The dashboard summary should understand that `plan-feature-review` approval does not automatically start `plan-feature-phase-make`, and it should be able to say that a feature is waiting for a human to kick off a feature-phase.

Dashboard will need agent choice just like orchestrator.py. Some stuff has already been extracted for your use (the agent prompts).

We need a new prompt for this, something like `dashboard-live-update.md`

EXAMPLE OUTPUTS
* We're back in the Make Pull Request for the third time. The last time, it sent the PR back to Make Commit because of a novel zoom bug in OuterViewControllerTablet. The PR contains three commits.
* We're building for the third time (2 commits with no extra cycles, and this is a third and final commit. So far we're fixing one bug the reviewer found). 
* The feature plan is approved, but no feature-phase has been kicked off yet. We're waiting for a human to create the feature-phase directory and set `plan-feature-phase-make` to ready.
* We're in feature-phase planning review. The reviewer kicked it back because the validation steps were too vague.



------

# Chrono

2026-03-18 19:32: 2026-03-18 Changes in with three commits.
2026-03-18 23:43: Commit 1 done. Renamed orchestration verbs/files to numbered plan/commits/pull-request prompts and renamed `feature-phase-build-template` to `feature-phase-template`.
2026-03-19 00:xx: Commit 2 done. Split feature planning from feature-phase orchestration, added feature-template, updated prompts/templates/status handling, and paired down prep-for-feature-phase-build.
2026-03-19 01:xx: Commit 3 done. Added AI live summaries to orch-dashboard with a dedicated prompt, dashboard agent selection, and feature/feature-phase aware focus reporting. Gemini review: "The implementation is clean, follows the project's architectural patterns (threading for I/O, shared config for constants), and directly addresses the requirements from tasks/orchestra-fixes.md. It provides a significant UX improvement for monitoring complex multi-stage orchestration."
