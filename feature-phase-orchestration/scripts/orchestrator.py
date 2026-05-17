#!/usr/bin/env python3
"""
AI Orchestration Pipeline

Docs: $ORCHESTRA_DIR/feature-phase-orchestration/README.md

Watches <project>/Orchestration/projects/ and drives agents through two workflows:
  feature: plan-feature-make → plan-feature-review
  feature-phase: plan-feature-phase-make → plan-feature-phase-review
  → commits-make ↔ commits-review (loop)
  → pull-request-make → pull-request-review → done

Usage:
  orchestrator.py [project-dir]   # project-dir defaults to current working directory

Killswitch:
  Rename killswitch-off.md → killswitch-on.md to freeze all activity.
  Rename back to resume.
"""

import argparse
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

from shared_config import (
    AGENT_CMD,
    FEATURE_VERBS,
    FEATURE_PHASE_VERBS,
    VERBS,
    VERB_AGENT,
    VERB_READS_FROM,
    prompt_file_name,
    task_file_name,
)

_log_fh = None  # Opened in main(), shared by log() and agent streaming

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ORCHESTRA_DIR: Path = Path()

# These are set in main() after the project dir is resolved:
ORCH_DIR: Path = Path()    # <project>/Orchestration/
TASKS_DIR: Path = Path()   # <project>/Orchestration/projects/
PROMPTS_DIR: Path = Path() # <orchestra>/prompts/
STATUS_FILE = "status.md"
DEFAULT_STATUS = "idle"
DEFAULT_OUTCOME = "none"

STATUS_LINE_RE = re.compile(
    r"^- (plan-feature-make|plan-feature-review|plan-feature-phase-make|plan-feature-phase-review|commits-make|commits-review|pull-request-make|pull-request-review):\s*status=([\w-]+)\s+outcome=([\w-]+)\s*$"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def killswitch_on() -> bool:
    return (ORCH_DIR / "killswitch-on.md").exists()


def resolve_orchestra_dir() -> Path:
    raw = os.environ.get("ORCHESTRA_DIR")
    if not raw:
        raise RuntimeError(
            "ORCHESTRA_DIR is not set. Export ORCHESTRA_DIR to the Orchestra checkout root "
            "before running feature-phase orchestration."
        )

    orchestra_dir = Path(raw).expanduser().resolve()
    if not orchestra_dir.exists():
        raise RuntimeError(f"ORCHESTRA_DIR points to a missing path: {orchestra_dir}")

    prompts_dir = orchestra_dir / "feature-phase-orchestration" / "prompts"
    if not prompts_dir.is_dir():
        raise RuntimeError(
            "ORCHESTRA_DIR does not look like an Orchestra checkout: "
            f"missing {prompts_dir}"
        )

    return orchestra_dir


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if _log_fh:
        print(line, file=_log_fh, flush=True)


def drain_agent_output(stream, captured_lines: list[str]) -> None:
    """
    Drain a binary agent output stream, capturing complete OUTCOME lines.

    Agents sometimes emit carriage-return progress updates, or may exit without
    a trailing newline. Treat both ``\\r`` and ``\\n`` as line breaks and flush
    any final partial line on EOF.
    """
    buffer = bytearray()

    def flush_buffer() -> None:
        if not buffer:
            return
        line = buffer.decode("utf-8", errors="replace").strip()
        buffer.clear()
        if line.startswith("OUTCOME:"):
            captured_lines.append(line)

    while True:
        try:
            chunk = stream.read(1)
        except (OSError, ValueError):
            break

        if not chunk:
            break

        if chunk in (b"\n", b"\r"):
            flush_buffer()
            continue

        buffer.extend(chunk)

    flush_buffer()


def _display_verb(verb: str) -> str:
    return "-".join(part.capitalize() for part in verb.split("-"))


def _display_agent(agent: str) -> str:
    return agent.capitalize()


def status_path(phase_dir: Path) -> Path:
    return phase_dir / STATUS_FILE


def task_file_path(phase_dir: Path, verb: str) -> Path:
    return phase_dir / task_file_name(verb)


def verbs_for_dir(task_dir: Path) -> list[str]:
    rel_parts = task_dir.resolve().relative_to(TASKS_DIR.resolve()).parts
    if len(rel_parts) == 1:
        return FEATURE_VERBS
    if len(rel_parts) == 2:
        return FEATURE_PHASE_VERBS
    raise ValueError(f"Unexpected task directory depth: {task_dir}")


def read_state(phase_dir: Path) -> dict[str, dict[str, str]]:
    """Read status.md into a verb->{status,outcome} map."""
    state = {verb: {"status": DEFAULT_STATUS, "outcome": DEFAULT_OUTCOME} for verb in verbs_for_dir(phase_dir)}
    path = status_path(phase_dir)

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return state

    for line in text.splitlines():
        m = STATUS_LINE_RE.match(line)
        if not m:
            continue
        verb, status, outcome = m.group(1), m.group(2), m.group(3)
        state[verb] = {"status": status, "outcome": outcome}

    return state


def write_state(phase_dir: Path, state: dict[str, dict[str, str]]) -> None:
    """Write status.md in a deterministic, human-readable format."""
    path = status_path(phase_dir)
    verbs = verbs_for_dir(phase_dir)
    is_feature_dir = verbs == FEATURE_VERBS

    lines = [
        "# Status",
        "",
        "Managed by `$ORCHESTRA_DIR/feature-phase-orchestration/scripts/orchestrator.py`.",
        "Set one verb to `status=ready` to queue work.",
        "Orchestrator sets `status=in-progress` while running, then idles the verb with the final outcome.",
        *(
            [
                "After `plan-feature-review` is approved, feature-phase planning does not auto-start.",
                "Create or update a feature-phase directory, then set `plan-feature-phase-make` to `status=ready` manually.",
            ]
            if is_feature_dir
            else [
                "Kick off a feature-phase by setting `plan-feature-phase-make` to `status=ready` manually after the feature plan is approved.",
            ]
        ),
        "",
    ]
    for verb in verbs:
        status = state.get(verb, {}).get("status", DEFAULT_STATUS)
        outcome = state.get(verb, {}).get("outcome", DEFAULT_OUTCOME)
        lines.append(f"- {verb}: status={status} outcome={outcome}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_verb_state(phase_dir: Path, verb: str, status: str, outcome: str) -> None:
    state = read_state(phase_dir)
    state[verb] = {"status": status, "outcome": outcome}
    write_state(phase_dir, state)
    try:
        rel = phase_dir.resolve().relative_to(ORCH_DIR.resolve())
    except ValueError:
        rel = phase_dir
    log(f"{rel}: {verb} -> status={status}, outcome={outcome}")


def queue_verb(phase_dir: Path, verb: str) -> None:
    set_verb_state(phase_dir, verb, "ready", "none")


def find_all_ready_targets() -> list[tuple[Path, str]]:
    targets: list[tuple[Path, str]] = []
    status_paths = sorted(TASKS_DIR.glob(f"*/{STATUS_FILE}")) + sorted(TASKS_DIR.glob(f"*/*/{STATUS_FILE}"))

    for spath in status_paths:
        task_dir = spath.parent
        state = read_state(task_dir)

        for verb in verbs_for_dir(task_dir):
            if state.get(verb, {}).get("status") == "ready":
                targets.append((task_dir, verb))

    return targets


def read_last_outcome(task_file: Path) -> str:
    """Return the value of the last OUTCOME: line in the task file."""
    try:
        text = task_file.read_text(encoding="utf-8")
    except OSError:
        return "unknown"

    outcomes = re.findall(r"^OUTCOME:\s*(\S+)", text, re.MULTILINE)
    if outcomes:
        return outcomes[-1]

    # Legacy fallback for older task files.
    signals = re.findall(r"^SIGNAL:\s*(\S+)", text, re.MULTILINE)
    return signals[-1] if signals else "unknown"


def replace_current_state_block(dst_file: Path, src_file: Path) -> None:
    """Copy the Current State block from src_file into dst_file."""
    try:
        src_text = src_file.read_text(encoding="utf-8")
        dst_text = dst_file.read_text(encoding="utf-8")
    except OSError as exc:
        log(f"WARNING: failed to read task file for Current State handoff: {exc}")
        return

    src_match = re.search(
        r"(## Current State\s*\n)(.*?)(\n---\n)",
        src_text,
        re.DOTALL,
    )
    dst_match = re.search(
        r"(## Current State\s*\n)(.*?)(\n---\n)",
        dst_text,
        re.DOTALL,
    )
    if not src_match or not dst_match:
        log(
            "WARNING: failed to hand off Current State "
            f"from {src_file.name} to {dst_file.name} (missing section)"
        )
        return

    updated = (
        dst_text[:dst_match.start(2)]
        + src_match.group(2)
        + dst_text[dst_match.end(2):]
    )
    try:
        dst_file.write_text(updated, encoding="utf-8")
    except OSError as exc:
        log(f"WARNING: failed to write task file for Current State handoff: {exc}")
        return

    log(f"Handed off Current State: {src_file.name} -> {dst_file.name}")


def handoff_current_state(task_dir: Path, src_verb: str, dst_verb: str) -> None:
    replace_current_state_block(
        task_file_path(task_dir, dst_verb),
        task_file_path(task_dir, src_verb),
    )



def run_agent(verb: str, task_file: Path) -> int:
    """
    Build a compact prompt from prompts/{verb}-prompt.md that points the agent to the
    task/context files on disk (instead of embedding full file contents), then
    invoke the appropriate agent CLI and return the exit code.
    """
    agent = VERB_AGENT[verb]
    prompt_path = PROMPTS_DIR / prompt_file_name(verb)

    try:
        prompt_text = prompt_path.read_text(encoding="utf-8")
    except OSError:
        log(f"ERROR: prompt file not found: {prompt_path}")
        return 1

    context_paths: list[Path] = []
    for prior_verb in VERB_READS_FROM.get(verb, []):
        prior_file = task_file_path(task_file.parent, prior_verb)
        if prior_file.exists():
            context_paths.append(prior_file)
            log(f"  context: {prior_file.name}")

    context_list = ""
    if context_paths:
        context_list = "\n".join(f"- `{p.resolve()}`" for p in context_paths)
    else:
        context_list = "- none"

    full_prompt = (
        f"{prompt_text}\n\n"
        f"---\n\n"
        "## Runtime Input Policy\n\n"
        "Read files from disk directly. Do not assume file contents are included in this prompt.\n"
        "Read the task file tail first to recover recent context, then read further up only if needed.\n"
        "Suggested command: `tail -n 300 <task-file-path>`.\n\n"
        "## Task File\n\n"
        f"- `{task_file.resolve()}`\n\n"
        "## Prior Context Files\n\n"
        f"{context_list}\n"
    )

    cmd_template = AGENT_CMD.get(agent)
    if not cmd_template:
        log(f"ERROR: no command configured for agent '{agent}'")
        return 1

    cmd = [part.replace("{prompt}", full_prompt) for part in cmd_template]

    log(f"Invoking {_display_agent(agent)} for verb={verb} ({task_file.name})")
    result = subprocess.run(cmd, stdin=subprocess.DEVNULL)
    return result.returncode


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

def advance(task_dir: Path, verb: str, outcome: str) -> None:
    """Trigger the next step after a verb completes with the given outcome."""

    if killswitch_on():
        log("Killswitch is ON — not advancing")
        return

    if verb == "plan-feature-make":
        if outcome == "awaiting-review":
            queue_verb(task_dir, "plan-feature-review")
        elif outcome == "needs-human":
            log("plan-feature-make paused for human input — check 01-plan-feature-make.md Current State for questions")
        else:
            log(f"plan-feature-make ended with outcome={outcome} — needs human attention")

    elif verb == "plan-feature-review":
        if outcome == "approved":
            log("Feature plan approved — create or update a feature-phase directory and set plan-feature-phase-make to ready manually")
        elif outcome == "rejected":
            handoff_current_state(task_dir, "plan-feature-review", "plan-feature-make")
            queue_verb(task_dir, "plan-feature-make")
        else:
            log(f"plan-feature-review ended with outcome={outcome} — needs human attention")

    elif verb == "plan-feature-phase-make":
        if outcome == "awaiting-review":
            queue_verb(task_dir, "plan-feature-phase-review")
        elif outcome == "needs-human":
            log("plan-feature-phase-make paused for human input — check 03-plan-feature-phase-make.md Current State for questions")
        else:
            log(f"plan-feature-phase-make ended with outcome={outcome} — needs human attention")

    elif verb == "plan-feature-phase-review":
        if outcome == "approved":
            queue_verb(task_dir, "commits-make")
        elif outcome == "rejected":
            handoff_current_state(task_dir, "plan-feature-phase-review", "plan-feature-phase-make")
            queue_verb(task_dir, "plan-feature-phase-make")
        else:
            log(f"plan-feature-phase-review ended with outcome={outcome} — needs human attention")

    elif verb == "commits-make":
        if outcome == "awaiting-review":
            queue_verb(task_dir, "commits-review")
        elif outcome == "done":
            queue_verb(task_dir, "pull-request-make")
        else:
            log(f"commits-make ended with outcome={outcome} — stopped")

    elif verb == "commits-review":
        if outcome == "approved":
            handoff_current_state(task_dir, "commits-review", "commits-make")
            queue_verb(task_dir, "commits-make")
            log("commits-make set to ready (approved — back to commits-make)")
        elif outcome == "rejected":
            handoff_current_state(task_dir, "commits-review", "commits-make")
            queue_verb(task_dir, "commits-make")
            log("commits-make set to ready (loop)")
        else:
            log(f"commits-review ended with outcome={outcome} — needs human attention")

    elif verb == "pull-request-make":
        if outcome == "done":
            queue_verb(task_dir, "pull-request-review")
        else:
            log(f"pull-request-make ended with outcome={outcome} — needs human attention")

    elif verb == "pull-request-review":
        if outcome == "approved":
            log(f"Feature-phase complete — ready for merge: {task_dir.relative_to(ORCH_DIR)}")
        elif outcome == "rejected":
            handoff_current_state(task_dir, "pull-request-review", "commits-make")
            queue_verb(task_dir, "commits-make")
        else:
            log(f"pull-request-review ended with outcome={outcome} — needs human attention")


def handle_ready_target(task_dir: Path, verb: str) -> None:
    """Process a ready verb from task_dir/status.md."""
    if killswitch_on():
        log(f"Killswitch is ON — skipping {task_dir.relative_to(ORCH_DIR)}:{verb}")
        return

    state = read_state(task_dir)
    if state.get(verb, {}).get("status") != "ready":
        return

    task_file = task_file_path(task_dir, verb)
    if not task_file.exists():
        task_file.touch()
        log(f"Created {task_file.relative_to(ORCH_DIR)}")

    # Move to in-progress and clear any prior outcome.
    set_verb_state(task_dir, verb, "in-progress", "none")

    # Run the agent.
    exit_code = run_agent(verb, task_file)
    outcome = read_last_outcome(task_file)

    if exit_code != 0 and outcome == "unknown":
        outcome = "error"
        log(f"Agent exited {exit_code} with no outcome — treating as error")
    else:
        log(f"Agent exited {exit_code}, outcome={outcome}")

    # Set verb idle with final outcome, then advance workflow.
    set_verb_state(task_dir, verb, "idle", outcome)
    advance(task_dir, verb, outcome)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    global _log_fh, ORCH_DIR, ORCHESTRA_DIR, TASKS_DIR, PROMPTS_DIR

    parser = argparse.ArgumentParser(description="AI Orchestration Pipeline")
    parser.add_argument(
        "project_dir",
        nargs="?",
        default=".",
        help="Root of the project to orchestrate (default: current directory)",
    )
    args = parser.parse_args()

    try:
        ORCHESTRA_DIR = resolve_orchestra_dir()
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)

    project_dir = Path(args.project_dir).resolve()
    ORCH_DIR = project_dir / "Orchestration"
    TASKS_DIR = ORCH_DIR / "projects"
    PROMPTS_DIR = ORCHESTRA_DIR / "feature-phase-orchestration" / "prompts"

    print()
    print(f"  Orchestra:  {ORCHESTRA_DIR}")
    print(f"  Project:    {project_dir}")
    print(f"  Tasks dir:  {TASKS_DIR}")
    print(f"  Prompts:    {PROMPTS_DIR}")
    print(f"  Killswitch: {'ON' if killswitch_on() else 'off'}")
    print()

    if not ORCH_DIR.exists():
        print(f"ERROR: {ORCH_DIR} does not exist — is this the right project directory?")
        raise SystemExit(1)

    answer = input("Is this correct? [y/N] ").strip().lower()
    if answer != "y":
        print("Aborted.")
        raise SystemExit(0)

    print()
    TASKS_DIR.mkdir(parents=True, exist_ok=True)

    log_path = ORCH_DIR / "orchestrator.log"
    _log_fh = open(log_path, "a", buffering=1)
    log(f"Logging to {log_path}")
    log(f"Scanning {TASKS_DIR} for {STATUS_FILE}")
    log(f"Killswitch: {'ON' if killswitch_on() else 'off'}")
    log("Ctrl-C to stop")

    confirmed = False

    try:
        while True:
            ready = find_all_ready_targets()
            if len(ready) > 1:
                log(f"ABORT: {len(ready)} ready targets found simultaneously — stopping")
                for phase_dir, verb in ready:
                    rel = phase_dir.relative_to(ORCH_DIR)
                    log(f"  {rel}: {verb}")
                return

            if len(ready) == 1:
                phase_dir, verb = ready[0]
                if not confirmed:
                    rel = phase_dir.relative_to(ORCH_DIR)
                    answer = input(f"\n  Ready: {rel} → {verb}\n  Proceed? [y/N] ").strip().lower()
                    if answer != "y":
                        log(f"Skipped {rel}:{verb} — user declined")
                        time.sleep(5)
                        continue
                    confirmed = True
                handle_ready_target(phase_dir, verb)

            time.sleep(1)
    except KeyboardInterrupt:
        log("Stopping.")


if __name__ == "__main__":
    main()
