# Agent Ping / ACK Plan

## Context

We want Kanban Orchestra to detect when an agent is effectively dead before
starting real work on a task step.

The concrete symptom is that an agent may launch but be out of tokens, wedged,
or otherwise non-responsive. Right now the orchestrator only finds out after the
real step fails or stalls in a less legible way.

## Desired Behavior

Before the orchestrator runs a real agent step, it should first do a lightweight
ping:

- open a short-lived agent session
- send a tiny prompt such as: `This is a ping. Respond with ACK.`
- treat any textual response as an ACK

This ping happens:

- once per non-skipped agent per task
- not once per round
- not for skipped steps

## Accepted Tradeoff

There should be no durable ping state in the database.

The orchestrator may keep only process-local memory of which agents have already
ACKed for the currently running tasks. If the orchestrator restarts, that memory
is gone and all bets are off. Re-pinging after restart is acceptable.

## Stuck Behavior

If the required agent does not respond to the ping:

- keep the current task pinned and `running`
- do not mark it `blocked`
- do not return it to the ready queue
- update runtime status to say plainly that the orchestrator is stuck waiting
  for the agent ACK needed for this task step
- retry the ping every minute until the agent responds or the orchestrator is
  interrupted

This preserves the existing invariant that one pinned task owns the queue until
it finishes or genuinely needs human intervention.

## Important Repo Context

The code being edited lives in this checkout under:

- `kanban-orchestra/scripts/orchestrator.py`
- `kanban-orchestra/scripts/test_kanban.py`

The orchestrator a human may actually launch can live in another checkout, but
the implementation work for this change is tracked here. Syncing or deploying it
to another checkout is a separate operational concern.

## Task Split

### Task 1

Implement the runtime behavior in the orchestrator:

- add the process-local ACK cache
- add the ping helper
- gate agent execution behind the ACK check
- keep the task pinned and visibly stalled while retrying every minute

### Task 2

Add verification and operator-facing polish:

- add or update unit tests for one-ACK-per-task semantics and retry behavior
- make runtime and run-log messaging clear enough that a human can tell exactly
  why the orchestrator is stalled
- update any nearby docs or comments needed to explain the new behavior
