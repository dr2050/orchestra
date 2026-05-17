#!/usr/bin/env python3
"""
orch-dashboard.py — Live terminal dashboard for the AI orchestration pipeline.

Usage:
    ko-feature-dashboard
    ko-feature-dashboard --worktree /path/to/worktree
    ko-feature-dashboard --threshold 300
"""

import argparse
import os
import queue
import re
import subprocess
import sys
import termios
import threading
import time
import tty
from pathlib import Path

from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from shared_config import (
    AGENT_CMD,
    DASHBOARD_AGENT,
    FEATURE_PHASE_VERBS,
    FEATURE_VERBS,
    VERB_READS_FROM,
    task_file_name,
)

REFRESH_SECONDS = 2
DEFAULT_STUCK_THRESHOLD = 5 * 60  # seconds
FLASH_DURATION = 4  # seconds
SUMMARY_PROMPT_FILE = "dashboard-live-update-prompt.md"


def parse_args():
    parser = argparse.ArgumentParser(description="Orchestration pipeline dashboard")
    parser.add_argument(
        "--worktree",
        default=None,
        help="Path to the worktree root (default: auto-detected from script location)",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_STUCK_THRESHOLD,
        help="Stuck detection threshold in seconds (default: 300)",
    )
    parser.add_argument(
        "--agent",
        default=DASHBOARD_AGENT,
        choices=sorted(AGENT_CMD.keys()),
        help=f"Agent to use for live summary generation (default: {DASHBOARD_AGENT})",
    )
    return parser.parse_args()


def resolve_orchestra_dir() -> Path:
    raw = os.environ.get("ORCHESTRA_DIR")
    if not raw:
        raise RuntimeError(
            "ORCHESTRA_DIR is not set. Export ORCHESTRA_DIR to the Orchestra checkout root "
            "before running the dashboard."
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


def find_worktree_root(script_path: Path) -> Path:
    # The dashboard is usually launched from the worktree root.
    return Path.cwd()


def verbs_for_status(status_path: Path, projects_dir: Path) -> list[str]:
    rel_parts = status_path.parent.relative_to(projects_dir).parts
    return FEATURE_VERBS if len(rel_parts) == 1 else FEATURE_PHASE_VERBS


def unit_label(status_path: Path, projects_dir: Path) -> tuple[str, str]:
    rel_parts = status_path.parent.relative_to(projects_dir).parts
    if len(rel_parts) == 1:
        return rel_parts[0], "feature"
    return rel_parts[0], rel_parts[1]


def is_feature_unit(status_path: Path, projects_dir: Path) -> bool:
    return len(status_path.parent.relative_to(projects_dir).parts) == 1


def feature_unit_complete(status_path: Path) -> bool:
    verbs = parse_status(status_path)
    status, outcome = verbs.get("plan-feature-review", ("idle", "none"))
    return status == "idle" and outcome == "approved"


def find_all_units(orch_dir: Path):
    """Return sorted list of (feature, unit, status_path) tuples."""
    projects_dir = orch_dir / "projects"
    if not projects_dir.exists():
        return []
    units = []
    status_paths = sorted(projects_dir.glob("*/status.md")) + sorted(projects_dir.glob("*/*/status.md"))
    for p in status_paths:
        verbs = parse_status(p)
        if is_feature_unit(p, projects_dir):
            if feature_unit_complete(p):
                phase_statuses = list(p.parent.glob("*/status.md"))
                if not phase_statuses:
                    units.append((*unit_label(p, projects_dir), p))
                    continue
                phase_in_flight = any(
                    parse_status(sp).get("pull-request-review", ("idle", "none"))[1] != "approved"
                    for sp in phase_statuses
                )
                if not phase_in_flight:
                    continue
        else:
            _, pr_review_outcome = verbs.get("pull-request-review", ("idle", "none"))
            if pr_review_outcome == "approved":
                continue
            expected_verbs = verbs_for_status(p, projects_dir)
            if not any(v in verbs for v in expected_verbs):
                continue
        feature, unit = unit_label(p, projects_dir)
        units.append((feature, unit, p))
    return units


def parse_status(status_path: Path) -> dict:
    """Returns dict of verb -> (status, outcome)."""
    result = {}
    try:
        text = status_path.read_text()
    except OSError:
        return result
    for line in text.splitlines():
        m = re.match(r"\s*-\s+(\S+):\s+status=(\S+)\s+outcome=(\S+)", line)
        if m:
            result[m.group(1)] = (m.group(2), m.group(3))
    return result


def is_xcodebuild_running() -> bool:
    try:
        return subprocess.run(["pgrep", "-x", "xcodebuild"], capture_output=True).returncode == 0
    except OSError:
        return False


def tail_file(path: Path, n: int) -> Text:
    if not path.exists():
        return Text(f"(file not found: {path})", style="dim")
    try:
        lines = path.read_text(errors="replace").splitlines()
        content = "\n".join(lines[-n:]) if lines else "(empty)"
        return Text.from_markup(escape(content))
    except OSError as e:
        return Text(f"(error: {e})", style="dim")


def read_last_outcome(task_file: Path) -> str:
    try:
        text = task_file.read_text(errors="replace")
    except OSError:
        return "unknown"
    outcomes = re.findall(r"^OUTCOME:\s*(\S+)", text, re.MULTILINE)
    return outcomes[-1] if outcomes else "none"


def read_latest_heading(task_file: Path) -> str:
    try:
        lines = task_file.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        if line.startswith("## "):
            return line[3:].strip()
    return ""


def format_age(timestamp: float, now: float | None = None) -> str:
    now = now or time.time()
    seconds = max(0, int(now - timestamp))
    if seconds < 60:
        return f"{seconds}s ago"
    if seconds < 3600:
        return f"{seconds // 60}m ago"
    if seconds < 86400:
        return f"{seconds // 3600}h ago"
    return f"{seconds // 86400}d ago"


def latest_code_update(worktree: Path) -> tuple[Path, float] | None:
    code_exts = {
        ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html", ".java",
        ".js", ".jsx", ".kt", ".m", ".mm", ".php", ".py", ".rb", ".rs", ".scss",
        ".sh", ".swift", ".ts", ".tsx",
    }
    skip_dirs = {
        ".git", ".build", ".idea", ".swiftpm", ".venv", "DerivedData", "Orchestration",
        "Pods", "build", "dist", "node_modules", "vendor",
    }

    latest_path = None
    latest_mtime = 0.0
    for path in worktree.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix.lower() not in code_exts:
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime > latest_mtime:
            latest_mtime = mtime
            latest_path = path

    if latest_path is None:
        return None
    return latest_path, latest_mtime


def get_unit_activity(status_path: Path, projects_dir: Path) -> tuple[float, list[tuple[float, str, Path]]]:
    task_dir = status_path.parent
    entries = []
    latest = status_path.stat().st_mtime if status_path.exists() else 0.0
    for verb in verbs_for_status(status_path, projects_dir):
        verb_file = task_dir / task_file_name(verb)
        if not verb_file.exists():
            continue
        mtime = verb_file.stat().st_mtime
        latest = max(latest, mtime)
        entries.append((mtime, verb, verb_file))
    entries.sort(reverse=True)
    return latest, entries


def verb_status_style(status: str) -> str:
    if status == "in-progress":
        return "bold yellow"
    if status == "ready":
        return "bold cyan"
    return "dim"


def outcome_display(outcome: str) -> str:
    return "—" if outcome in ("none", "", "?") else outcome


def restart_current_unit(units, projects_dir: Path) -> str:
    """Set the in-progress verb to ready. Returns a message describing what happened."""
    for feature, unit, status_path in units:
        verb_statuses = parse_status(status_path)
        for verb in verbs_for_status(status_path, projects_dir):
            status, _ = verb_statuses.get(verb, ("idle", "none"))
            if status == "in-progress":
                try:
                    text = status_path.read_text()
                    new_text = re.sub(
                        rf"(-\s+{re.escape(verb)}:\s+)status=in-progress",
                        r"\1status=ready",
                        text,
                    )
                    status_path.write_text(new_text)
                    return f"Set {verb} → ready. Restart orchestrator to pick up."
                except OSError as e:
                    return f"Error writing status.md: {e}"
    return "No in-progress verb found."


def find_focus_unit(units, projects_dir: Path):
    prioritized = []
    for feature, unit, status_path in units:
        verb_statuses = parse_status(status_path)
        latest_activity, recent_files = get_unit_activity(status_path, projects_dir)

        priority = 2
        for verb in verbs_for_status(status_path, projects_dir):
            status, _ = verb_statuses.get(verb, ("idle", "none"))
            if status == "in-progress":
                priority = 0
                break
            if status == "ready" and priority > 1:
                priority = 1

        prioritized.append((priority, -latest_activity, feature, unit, status_path, verb_statuses, recent_files))

    if not prioritized:
        return None

    prioritized.sort()
    _, _, feature, unit, status_path, verb_statuses, recent_files = prioritized[0]
    return {
        "feature": feature,
        "unit": unit,
        "status_path": status_path,
        "verb_statuses": verb_statuses,
        "recent_files": recent_files,
    }


def find_focus_verb(unit_info, projects_dir: Path) -> str | None:
    verb_statuses = unit_info["verb_statuses"]
    for verb in verbs_for_status(unit_info["status_path"], projects_dir):
        status, _ = verb_statuses.get(verb, ("idle", "none"))
        if status == "in-progress":
            return verb
    for verb in verbs_for_status(unit_info["status_path"], projects_dir):
        status, _ = verb_statuses.get(verb, ("idle", "none"))
        if status == "ready":
            return verb
    for _, verb, _ in unit_info["recent_files"]:
        return verb
    return None


def next_verbs_for(verb: str, outcome: str) -> list[str]:
    if verb == "plan-feature-make" and outcome == "awaiting-review":
        return ["plan-feature-review"]
    if verb == "plan-feature-review" and outcome == "rejected":
        return ["plan-feature-make"]
    if verb == "plan-feature-phase-make" and outcome == "awaiting-review":
        return ["plan-feature-phase-review"]
    if verb == "plan-feature-phase-review" and outcome == "approved":
        return ["commits-make"]
    if verb == "plan-feature-phase-review" and outcome == "rejected":
        return ["plan-feature-phase-make"]
    if verb == "commits-make" and outcome == "awaiting-review":
        return ["commits-review"]
    if verb == "commits-make" and outcome == "done":
        return ["pull-request-make"]
    if verb == "commits-review" and outcome in ("approved", "rejected"):
        return ["commits-make"]
    if verb == "pull-request-make" and outcome == "done":
        return ["pull-request-review"]
    if verb == "pull-request-review" and outcome == "rejected":
        return ["commits-make"]
    return []


def unit_kind(status_path: Path, projects_dir: Path) -> str:
    return "feature" if is_feature_unit(status_path, projects_dir) else "feature-phase"


def summarize_units_for_prompt(units, projects_dir: Path) -> str:
    lines = []
    for feature, unit, status_path in units:
        verb_statuses = parse_status(status_path)
        statuses = []
        for verb in verbs_for_status(status_path, projects_dir):
            status, outcome = verb_statuses.get(verb, ("idle", "none"))
            if status != "idle" or outcome != "none":
                statuses.append(f"{verb}={status}/{outcome}")
        status_summary = ", ".join(statuses) if statuses else "all idle"
        lines.append(f"- {feature} / {unit} ({unit_kind(status_path, projects_dir)}): {status_summary}")
    return "\n".join(lines) if lines else "- none"


def build_summary_context_paths(unit_info, projects_dir: Path) -> list[Path]:
    status_path = unit_info["status_path"]
    task_dir = status_path.parent
    paths = [status_path]

    plan_path = task_dir / "plan.md"
    if plan_path.exists():
        paths.append(plan_path)

    for verb in verbs_for_status(status_path, projects_dir):
        task_path = task_dir / task_file_name(verb)
        if task_path.exists():
            paths.append(task_path)

    if not is_feature_unit(status_path, projects_dir):
        feature_dir = task_dir.parent
        for name in ("status.md", "plan.md", "01-plan-feature-make.md", "02-plan-feature-review.md"):
            path = feature_dir / name
            if path.exists():
                paths.append(path)

    return paths


def summary_signature(units, unit_info, projects_dir: Path) -> tuple:
    latest_activity, recent_files = get_unit_activity(unit_info["status_path"], projects_dir)
    unit_parts = []
    for feature, unit, status_path in units:
        unit_parts.append((feature, unit, int(status_path.stat().st_mtime)))
    recent_parts = [(verb, int(mtime)) for mtime, verb, _ in recent_files[:4]]
    return (
        unit_info["feature"],
        unit_info["unit"],
        int(unit_info["status_path"].stat().st_mtime),
        int(latest_activity),
        tuple(unit_parts),
        tuple(recent_parts),
    )


def extract_summary_text(output: str) -> str:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return " ".join(lines)


class SummaryWorker:
    def __init__(self, orch_dir: Path, agent: str, orchestra_dir: Path):
        self.orch_dir = orch_dir
        self.agent = agent
        self.prompts_dir = orchestra_dir / "feature-phase-orchestration" / "prompts"
        self.prompt_path = self.prompts_dir / SUMMARY_PROMPT_FILE
        self._requests: queue.Queue = queue.Queue(maxsize=1)
        self._lock = threading.Lock()
        self._snapshot = {
            "key": None,
            "status": "idle",
            "text": "Waiting for an active work unit.",
            "updated_at": 0.0,
            "error": "",
            "agent": agent,
        }
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._snapshot)

    def invalidate(self) -> None:
        with self._lock:
            self._snapshot["status"] = "idle"

    def request(self, key: tuple, prompt: str) -> None:
        snap = self.snapshot()
        if snap["status"] == "running" and snap["key"] == key:
            return
        if snap["status"] == "done" and snap["key"] == key:
            return
        while True:
            try:
                self._requests.get_nowait()
            except queue.Empty:
                break
        self._requests.put((key, prompt))

    def _run(self) -> None:
        while True:
            key, prompt = self._requests.get()
            with self._lock:
                self._snapshot.update({"key": key, "status": "running", "error": ""})
            text = ""
            error = ""
            try:
                prompt_text = self.prompt_path.read_text(encoding="utf-8")
                cmd_template = AGENT_CMD[self.agent]
                full_prompt = f"{prompt_text}\n\n---\n\n{prompt}"
                cmd = [part.replace("{prompt}", full_prompt) for part in cmd_template]
                result = subprocess.run(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=45,
                )
                text = extract_summary_text(result.stdout or "")
                if result.returncode != 0:
                    error = f"{self.agent} exited {result.returncode}"
                elif not text:
                    error = "agent returned no summary"
            except FileNotFoundError:
                error = f"agent not available: {self.agent}"
            except subprocess.TimeoutExpired:
                error = f"{self.agent} timed out"
            except OSError as exc:
                error = str(exc)

            with self._lock:
                self._snapshot.update(
                    {
                        "key": key,
                        "status": "done" if not error else "error",
                        "text": text if text else "Live summary unavailable.",
                        "updated_at": time.time(),
                        "error": error,
                        "agent": self.agent,
                    }
                )


def build_summary_prompt(units, unit_info, orch_dir: Path) -> tuple[tuple, str]:
    projects_dir = orch_dir / "projects"
    focus_verb = find_focus_verb(unit_info, projects_dir) or "none"
    all_units = summarize_units_for_prompt(units, projects_dir)
    context_paths = build_summary_context_paths(unit_info, projects_dir)
    context_list = "\n".join(f"- `{path.resolve()}`" for path in context_paths)

    prompt = (
        "## Runtime Input Policy\n\n"
        "Read files from disk directly. Do not assume file contents are embedded in this prompt.\n"
        "Use only the current orchestration state and the referenced files.\n\n"
        "## Focus Work Unit\n\n"
        f"- Feature: `{unit_info['feature']}`\n"
        f"- Unit: `{unit_info['unit']}`\n"
        f"- Kind: `{unit_kind(unit_info['status_path'], projects_dir)}`\n"
        f"- Focus verb: `{focus_verb}`\n"
        f"- Status file: `{unit_info['status_path'].resolve()}`\n\n"
        "## All Current Work Units\n\n"
        f"{all_units}\n\n"
        "## Relevant Files\n\n"
        f"{context_list}\n"
    )
    return summary_signature(units, unit_info, projects_dir), prompt


def build_summary_panel(units, orch_dir: Path, worker: SummaryWorker, flash: dict) -> Panel:
    projects_dir = orch_dir / "projects"
    unit_info = find_focus_unit(units, projects_dir)
    now = time.time()
    toast = flash.get("msg") if flash.get("msg") and now < flash.get("until", 0) else None

    if not unit_info:
        items = []
        if toast:
            items.append(Text(f"→ {toast}", style="bold green"))
        items.append(Text("Waiting for an active work unit."))
        return Panel(Group(*items), title=f"Live Summary ({worker.agent.capitalize()})", border_style="dim")

    key, prompt = build_summary_prompt(units, unit_info, orch_dir)
    worker.request(key, prompt)
    snapshot = worker.snapshot()
    display_agent = worker.agent.capitalize()

    lines = [
        Text(f"Focus: {unit_info['feature']} / {unit_info['unit']}", style="bold white"),
    ]

    if toast:
        lines.append(Text(f"→ {toast}", style="bold green"))

    lines.append(Text(""))
    lines.append(Text(snapshot["text"], style="white"))
    if snapshot["status"] == "running" and snapshot["key"] == key:
        lines.append(Text("updating…", style="dim"))

    if snapshot.get("error"):
        lines.append(Text(""))
        lines.append(Text(f"Agent status: {snapshot['error']}", style="dim"))
    else:
        updated_at = snapshot.get("updated_at", 0.0)
        if updated_at:
            lines.append(Text(""))
            lines.append(Text(f"Updated: {format_age(updated_at)}   [s] refresh", style="dim"))

    return Panel(Group(*lines), title=f"Live Summary ({display_agent})", border_style="green")


def build_focus_panel(units, orch_dir: Path) -> Panel:
    projects_dir = orch_dir / "projects"
    worktree = orch_dir.parent
    unit_info = find_focus_unit(units, projects_dir)
    if not unit_info:
        return Panel("(no active unit)", title="Focus", border_style="dim")

    now = time.time()
    feature = unit_info["feature"]
    unit = unit_info["unit"]
    status_path = unit_info["status_path"]
    task_dir = status_path.parent
    verb_statuses = unit_info["verb_statuses"]
    focus_verb = find_focus_verb(unit_info, projects_dir)

    lines = [
        Text(f"{feature} / {unit}", style="bold white"),
        Text(""),
    ]

    latest_activity, _ = get_unit_activity(status_path, projects_dir)
    lines.append(Text(f"Unit activity: {format_age(latest_activity, now)}", style="dim"))
    latest_code = latest_code_update(worktree)
    if latest_code:
        _, latest_code_mtime = latest_code
        lines.append(Text(f"Last code update: {format_age(latest_code_mtime, now)}", style="dim"))

    if not focus_verb:
        lines.append(Text("No focus verb", style="dim"))
        return Panel(Group(*lines), title="Focus", border_style="dim")

    focus_status, focus_outcome = verb_statuses.get(focus_verb, ("idle", "none"))
    focus_file = task_dir / task_file_name(focus_verb)
    lines.append(Text(f"Focus: {focus_verb}", style="bold yellow"))
    lines.append(Text(f"Status: {focus_status}   Outcome: {outcome_display(focus_outcome)}", style="dim"))
    if focus_file.exists():
        lines.append(Text(f"Updated: {format_age(focus_file.stat().st_mtime, now)}", style="dim"))
        heading = read_latest_heading(focus_file)
        if heading:
            lines.append(Text(f'Latest: "{heading}"', style="white"))

    prior_verbs = VERB_READS_FROM.get(focus_verb, [])
    lines.append(Text(""))
    lines.append(Text("Reads from:", style="bold cyan"))
    if prior_verbs:
        for prior_verb in prior_verbs:
            prior_file = task_dir / task_file_name(prior_verb)
            if prior_file.exists():
                outcome = read_last_outcome(prior_file)
                age = format_age(prior_file.stat().st_mtime, now)
                heading = read_latest_heading(prior_file)
                lines.append(Text(f"{prior_verb}   outcome={outcome_display(outcome)}   {age}", style="white"))
                if heading:
                    lines.append(Text(f'  "{heading}"', style="dim"))
            else:
                lines.append(Text(f"{prior_verb}   missing", style="dim"))
    else:
        lines.append(Text("none", style="dim"))

    if focus_file.exists():
        next_candidates = next_verbs_for(focus_verb, read_last_outcome(focus_file))
        if next_candidates:
            lines.append(Text(""))
            lines.append(Text(f"Next from latest outcome: {', '.join(next_candidates)}", style="bold green"))

    recent_entries = unit_info["recent_files"][:4]
    if recent_entries:
        lines.append(Text(""))
        lines.append(Text("Recent orchestra outputs:", style="bold cyan"))
        for mtime, verb, verb_file in recent_entries:
            outcome = read_last_outcome(verb_file)
            lines.append(Text(f"{verb}   {outcome_display(outcome)}   {format_age(mtime, now)}", style="white"))

    return Panel(Group(*lines), title="Focus", border_style="yellow")


def start_keyboard_thread(key_queue: queue.Queue):
    """Read single keypresses in a background thread and put them on the queue."""

    def _run():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            while True:
                ch = sys.stdin.read(1)
                key_queue.put(ch)
        except Exception:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

    t = threading.Thread(target=_run, daemon=True)
    t.start()


def build_units_panel(units, orch_dir: Path, stuck_threshold: int) -> Panel:
    now = time.time()
    building = is_xcodebuild_running()
    stuck_warnings = []
    projects_dir = orch_dir / "projects"

    table = Table(box=None, show_header=False, padding=(0, 1))
    table.add_column("verb", no_wrap=True)
    table.add_column("status", no_wrap=True)
    table.add_column("outcome", no_wrap=True)

    for feature, unit, status_path in units:
        table.add_row(Text(f"{feature} / {unit}", style="bold white"), "", "")

        verb_statuses = parse_status(status_path)
        task_dir = status_path.parent

        for verb in verbs_for_status(status_path, projects_dir):
            status, outcome = verb_statuses.get(verb, ("?", "?"))

            if status == "in-progress":
                verb_file = task_dir / task_file_name(verb)
                if verb_file.exists() and not building:
                    last_activity = max(verb_file.stat().st_mtime, status_path.stat().st_mtime)
                    elapsed = now - last_activity
                    if elapsed > stuck_threshold:
                        minutes = int(elapsed // 60)
                        stuck_warnings.append(f"{feature}/{unit}/{verb} — {minutes}m since last write")

            table.add_row(
                f"  {verb}",
                Text(status, style=verb_status_style(status)),
                Text(outcome_display(outcome), style="dim"),
            )

        table.add_row("", "", "")

    extras = []
    if building:
        extras.append(Text("  ⚙ xcodebuild running (stuck detection suspended)", style="bold blue"))
    for warning in stuck_warnings:
        extras.append(Text(f"  ⚠ STUCK? {warning}", style="bold red"))
    extras.append(Text("  [r] restart current unit", style="dim"))



    return Panel(Group(table, *extras), title="Work Units", border_style="white")


def build_log_panel(orch_dir: Path) -> Panel:
    log_path = orch_dir / "orchestrator.log"
    return Panel(
        Align(tail_file(log_path, 200), align="left", vertical="bottom"),
        title="orchestrator.log",
        border_style="dim",
    )


def find_active_verb_file(units, projects_dir: Path) -> Path | None:
    for _, _, status_path in units:
        task_dir = status_path.parent
        for verb in verbs_for_status(status_path, projects_dir):
            status, _ = parse_status(status_path).get(verb, ("idle", "none"))
            if status == "in-progress":
                path = task_dir / task_file_name(verb)
                return path if path.exists() else None
    return None


def build_context_panel(units, orch_dir: Path) -> Panel:
    verb_file = find_active_verb_file(units, orch_dir / "projects")
    if verb_file:
        try:
            path_str = str(verb_file.relative_to(orch_dir.parent))
        except ValueError:
            path_str = str(verb_file)
    else:
        path_str = "(no active task)"
    return Panel(Text(path_str, style="dim"), title="path", border_style="dim", height=3)


def build_layout(units, orch_dir: Path, stuck_threshold: int, flash: dict, worker: SummaryWorker) -> Layout:
    layout = Layout()
    layout.split_column(Layout(name="context", size=3), Layout(name="main"))
    layout["main"].split_row(Layout(name="left", ratio=1), Layout(name="right", ratio=1))
    layout["right"].split_column(
        Layout(name="summary", ratio=1),
        Layout(name="task", ratio=2),
        Layout(name="log", ratio=1),
    )
    layout["context"].update(build_context_panel(units, orch_dir))
    layout["left"].update(build_units_panel(units, orch_dir, stuck_threshold))
    layout["summary"].update(build_summary_panel(units, orch_dir, worker, flash))
    layout["task"].update(build_focus_panel(units, orch_dir))
    layout["log"].update(build_log_panel(orch_dir))
    return layout


def main():
    args = parse_args()
    try:
        orchestra_dir = resolve_orchestra_dir()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

    script_path = Path(__file__).resolve()
    worktree = Path(args.worktree).resolve() if args.worktree else find_worktree_root(script_path)
    orch_dir = worktree / "Orchestration"

    key_queue: queue.Queue = queue.Queue()
    start_keyboard_thread(key_queue)
    flash: dict = {}
    summary_worker = SummaryWorker(orch_dir, args.agent, orchestra_dir)

    try:
        with Live(console=Console(), refresh_per_second=0.5, screen=True) as live:
            while True:
                while not key_queue.empty():
                    ch = key_queue.get_nowait()
                    if ch in ("r", "R"):
                        units = find_all_units(orch_dir)
                        msg = restart_current_unit(units, orch_dir / "projects")
                        flash["msg"] = msg
                        flash["until"] = time.time() + FLASH_DURATION
                    elif ch in ("s", "S"):
                        summary_worker.invalidate()
                        flash["msg"] = "Refreshing summary…"
                        flash["until"] = time.time() + FLASH_DURATION
                    elif ch == " ":
                        units = find_all_units(orch_dir)
                        verb_file = find_active_verb_file(units, orch_dir / "projects")
                        if verb_file:
                            if subprocess.run(["which", "pandoc"], capture_output=True).returncode == 0:
                                tmp = Path(f"/tmp/orch-preview-{verb_file.stem}.html")
                                subprocess.run(["pandoc", "-f", "gfm", "-t", "html", str(verb_file), "-o", str(tmp)])
                                subprocess.Popen(["open", str(tmp)])
                            else:
                                subprocess.Popen(["open", "-a", "Console", str(verb_file)])

                units = find_all_units(orch_dir)
                live.update(build_layout(units, orch_dir, args.threshold, flash, summary_worker))
                time.sleep(REFRESH_SECONDS)
    except KeyboardInterrupt:
        return


if __name__ == "__main__":
    main()
