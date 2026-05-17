#!/usr/bin/env python3
"""
Standalone test for AI agent CLI invocations.

Tests each agent (claude, codex, gemini) with a model self-report and three file operations:
  0. Report the model it is running, if known
  1. Read a file and report its contents
  2. Write a new file
  3. Modify (append to) an existing file

Cleans up the temp workspace if all tests pass.
Leaves workspace in place on failure for inspection.

Usage:
  python3 feature-phase-orchestration/scripts/test_ai_invocations.py [claude|codex|gemini]

  With no argument, runs all three agents sequentially.
"""

import subprocess
import sys
import time
from pathlib import Path

from shared_config import AGENT_CMD

LOG_PATH = Path(__file__).parent / "test_ai_invocations.log"
_log_fh = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if _log_fh:
        print(line, file=_log_fh, flush=True)


def format_duration(seconds: float) -> str:
    return f"{seconds:.2f}s"


def build_prompt(agent: str, workspace: Path) -> str:
    read_file   = workspace / "read_source.txt"
    write_file  = workspace / f"{agent}_written.txt"
    modify_file = workspace / f"{agent}_modify.txt"

    return f"""\
You are being tested as an AI agent. First report the model you are running, \
then perform the three file operations in order. Do not skip any step.

Print exactly one model line in this format:
MODEL: <model name or unknown>

After completing all three file operations, print exactly:
OUTCOME: pass

If any step fails, print:
OUTCOME: fail

---

STEP 0 — MODEL
Print the model you are running if you can identify it. If you cannot identify it, print:
MODEL: unknown

STEP 1 — READ
Read the file at this path and print its first line to stdout:
  {read_file}

STEP 2 — WRITE
Write a new file at this path containing exactly the text "agent={agent} write=ok":
  {write_file}

STEP 3 — MODIFY
Append a new line containing exactly "modified-by={agent}" to this file:
  {modify_file}

Do not print any other MODEL: or OUTCOME: lines. Print OUTCOME: pass only after all three file operations succeed.
"""


def run_agent(agent: str, prompt: str) -> tuple[int, str, float]:
    """Invoke the agent CLI and return (exit_code, combined_output, duration_seconds)."""
    cmd_template = AGENT_CMD[agent]
    cmd = [part.replace("{prompt}", prompt) for part in cmd_template]

    log(f"  Invoking: {cmd[0]} ...")
    lines = []
    started_at = time.monotonic()
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
        if proc.stdout:
            for line in proc.stdout:
                raw = line.rstrip()
                if raw:
                    out = f"    > {raw}"
                    print(out, flush=True)
                    if _log_fh:
                        print(out, file=_log_fh, flush=True)
                    lines.append(raw)
        proc.wait()
    duration = time.monotonic() - started_at
    return proc.returncode, "\n".join(lines), duration


def extract_model(output: str) -> str:
    """Return the first agent-reported model, or unknown if absent."""
    for line in output.splitlines():
        if line.startswith("MODEL:"):
            model = line.removeprefix("MODEL:").strip()
            return model or "unknown"
    return "unknown"


def check_results(agent: str, workspace: Path, output: str) -> list[str]:
    """Return a list of failure messages (empty = all passed)."""
    failures = []

    # Check OUTCOME: pass in agent output
    if "OUTCOME: pass" not in output:
        failures.append("Agent did not print 'OUTCOME: pass'")

    # Check written file
    write_file = workspace / f"{agent}_written.txt"
    if not write_file.exists():
        failures.append(f"Write file not created: {write_file.name}")
    else:
        content = write_file.read_text().strip()
        if content != f"agent={agent} write=ok":
            failures.append(f"Write file content wrong: {content!r}")

    # Check modified file
    modify_file = workspace / f"{agent}_modify.txt"
    lines = modify_file.read_text().splitlines()
    if f"modified-by={agent}" not in lines:
        failures.append(f"Modify file missing expected line. Contents: {lines}")

    return failures


def run_agent_check(agent: str, workspace: Path) -> tuple[bool, str, float]:
    """Run the test for a single agent. Returns (passed, reported_model, duration_seconds)."""
    log(f"=== Testing agent: {agent} ===")

    prompt = build_prompt(agent, workspace)
    exit_code, output, duration = run_agent(agent, prompt)
    reported_model = extract_model(output)

    log(f"  Exit code: {exit_code}")
    log(f"  Duration: {format_duration(duration)}")
    log(f"  Reported model: {reported_model}")
    failures = check_results(agent, workspace, output)

    if failures:
        log(f"  FAIL ({len(failures)} issue(s)):")
        for f in failures:
            log(f"    - {f}")
        return False, reported_model, duration
    else:
        log(f"  PASS")
        return True, reported_model, duration


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    global _log_fh
    _log_fh = open(LOG_PATH, "a", buffering=1)
    log(f"Log: {LOG_PATH}")

    agents_to_test = sys.argv[1:] if len(sys.argv) > 1 else list(AGENT_CMD.keys())

    for agent in agents_to_test:
        if agent not in AGENT_CMD:
            print(f"Unknown agent: {agent}. Choose from: {', '.join(AGENT_CMD)}")
            sys.exit(1)

    # Workspace inside the project so Gemini's sandbox allows file access
    workspace = Path(__file__).parent / "test_workspace"
    workspace.mkdir(exist_ok=True)
    log(f"Workspace: {workspace}")

    # Seed files
    (workspace / "read_source.txt").write_text("hello from test harness\n")
    for agent in agents_to_test:
        (workspace / f"{agent}_modify.txt").write_text("original line\n")

    run_started_at = time.monotonic()
    results: dict[str, tuple[bool, str, float]] = {}
    for agent in agents_to_test:
        results[agent] = run_agent_check(agent, workspace)
    total_duration = time.monotonic() - run_started_at

    # Summary
    log("")
    log("=== Summary ===")
    all_passed = True
    for agent, (passed, reported_model, duration) in results.items():
        status = "PASS" if passed else "FAIL"
        log(f"  {agent}: {status} ({format_duration(duration)}, model: {reported_model})")
        if not passed:
            all_passed = False
    log(f"  total: {format_duration(total_duration)}")

    if all_passed:
        log("All tests passed. Cleaning up workspace.")
        import shutil
        shutil.rmtree(workspace)
    else:
        log(f"Some tests failed. Workspace left for inspection: {workspace}")
        sys.exit(1)


if __name__ == "__main__":
    main()
