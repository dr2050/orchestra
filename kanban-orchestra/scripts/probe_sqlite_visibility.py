#!/usr/bin/env python3
"""
probe_sqlite_visibility.py — diagnose cross-process SQLite visibility for Kanban Orchestra.

This script uses the real Kanban Orchestra filenames and code paths:
- opens the database through db.connect()
- performs writes through the real task.py CLI in a subprocess
- compares what a long-lived connection sees vs a brand-new connection

Typical usage:
  python3 kanban-orchestra/scripts/probe_sqlite_visibility.py --db /path/to/kanban-orchestra.db --task-id 7
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import db  # noqa: E402


TASK_CLI = SCRIPT_DIR / "task.py"


def _main_db_path(conn):
    row = conn.execute("PRAGMA database_list").fetchone()
    return row["file"] if row else None


def _task_snapshot(conn, task_id):
    task = db.get_task(conn, task_id)
    comments = db.get_comments(conn, task_id)
    return {
        "task_exists": bool(task),
        "commit_plan": task.get("commit_plan") if task else None,
        "status": task.get("status") if task else None,
        "next_step": task.get("next_step") if task else None,
        "review_round": task.get("review_round") if task else None,
        "comment_count": len(comments),
        "last_comment_id": comments[-1]["id"] if comments else None,
        "last_comment_kind": comments[-1]["kind"] if comments else None,
        "last_comment_message": comments[-1]["message"] if comments else None,
    }


def _fresh_snapshot(db_path, task_id):
    with closing(db.connect(db_path)) as conn:
        return _task_snapshot(conn, task_id)


def _print_json(label, obj):
    print(f"\n## {label}")
    print(json.dumps(obj, indent=2, sort_keys=True, default=str))


def _run_task_cli(db_path, *args):
    env = dict(os.environ)
    env["KANBAN_DB"] = str(db_path)
    cmd = ["python3", str(TASK_CLI), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return {
        "cmd": cmd,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _sleep_if_requested(seconds):
    if seconds > 0:
        time.sleep(seconds)


def _probe_comment(main_conn, db_path, task_id, iteration, pause):
    marker = f"sqlite-probe-comment-{os.getpid()}-{iteration}"
    before_main = _task_snapshot(main_conn, task_id)
    before_fresh = _fresh_snapshot(db_path, task_id)
    cli = _run_task_cli(db_path, "comment", str(task_id), marker, "--comment")
    _sleep_if_requested(pause)
    after_main = _task_snapshot(main_conn, task_id)
    after_fresh = _fresh_snapshot(db_path, task_id)
    return {
        "probe": "comment",
        "marker": marker,
        "before_main": before_main,
        "before_fresh": before_fresh,
        "cli": cli,
        "after_main": after_main,
        "after_fresh": after_fresh,
        "main_saw_new_comment": after_main["comment_count"] > before_main["comment_count"],
        "fresh_saw_new_comment": after_fresh["comment_count"] > before_fresh["comment_count"],
        "main_last_comment_matches": after_main["last_comment_message"] == marker,
        "fresh_last_comment_matches": after_fresh["last_comment_message"] == marker,
    }


def _probe_commit_plan(main_conn, db_path, task_id, iteration, pause):
    marker = f"sqlite-probe-plan-{os.getpid()}-{iteration}"
    before_main = _task_snapshot(main_conn, task_id)
    before_fresh = _fresh_snapshot(db_path, task_id)
    cli = _run_task_cli(db_path, "set", str(task_id), "--commit-plan", marker)
    _sleep_if_requested(pause)
    after_main = _task_snapshot(main_conn, task_id)
    after_fresh = _fresh_snapshot(db_path, task_id)
    return {
        "probe": "commit_plan",
        "marker": marker,
        "before_main": before_main,
        "before_fresh": before_fresh,
        "cli": cli,
        "after_main": after_main,
        "after_fresh": after_fresh,
        "main_saw_new_plan": after_main["commit_plan"] == marker,
        "fresh_saw_new_plan": after_fresh["commit_plan"] == marker,
    }


def _probe_direct_sqlite(db_path, task_id, iteration, pause):
    marker = f"sqlite-probe-direct-{os.getpid()}-{iteration}"
    raw = sqlite3.connect(db_path)
    try:
        raw.execute(
            "INSERT INTO comments (task_id, review_round, verb, author, message, kind) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (task_id, 0, None, "sqlite-probe", marker, "comment"),
        )
        raw.commit()
    finally:
        raw.close()
    _sleep_if_requested(pause)
    with closing(db.connect(db_path)) as conn:
        snap = _task_snapshot(conn, task_id)
    return {
        "probe": "direct_sqlite",
        "marker": marker,
        "fresh_snapshot_after_direct_write": snap,
        "fresh_last_comment_matches": snap["last_comment_message"] == marker,
    }


def build_parser():
    parser = argparse.ArgumentParser(description="Probe Kanban Orchestra SQLite visibility.")
    parser.add_argument("--db", required=True, help="Path to kanban-orchestra.db")
    parser.add_argument("--task-id", required=True, type=int, help="Task ID to mutate during probing")
    parser.add_argument(
        "--mode",
        choices=["comment", "commit-plan", "both"],
        default="both",
        help="Which real task.py writes to exercise",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="How many times to repeat each probe",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.0,
        help="Seconds to sleep after each subprocess write before reading",
    )
    parser.add_argument(
        "--include-direct-sqlite",
        action="store_true",
        help="Also perform one raw sqlite3 write as a control case",
    )
    return parser


def main():
    args = build_parser().parse_args()
    db_path = str(Path(args.db).expanduser().resolve())

    main_conn = db.connect(db_path)
    try:
        if not db.get_task(main_conn, args.task_id):
            print(f"Task {args.task_id} not found in {db_path}", file=sys.stderr)
            return 2

        journal_mode = main_conn.execute("PRAGMA journal_mode").fetchone()[0]
        header = {
            "db_path": db_path,
            "main_db_path": _main_db_path(main_conn),
            "task_id": args.task_id,
            "cwd": os.getcwd(),
            "python": sys.version.split()[0],
            "journal_mode": journal_mode,
            "task_cli": str(TASK_CLI),
            "pid": os.getpid(),
        }
        _print_json("Environment", header)
        _print_json("Initial Main Snapshot", _task_snapshot(main_conn, args.task_id))
        _print_json("Initial Fresh Snapshot", _fresh_snapshot(db_path, args.task_id))

        results = []
        for iteration in range(1, args.iterations + 1):
            if args.mode in ("comment", "both"):
                results.append(_probe_comment(main_conn, db_path, args.task_id, iteration, args.pause))
            if args.mode in ("commit-plan", "both"):
                results.append(_probe_commit_plan(main_conn, db_path, args.task_id, iteration, args.pause))

        if args.include_direct_sqlite:
            results.append(_probe_direct_sqlite(db_path, args.task_id, 1, args.pause))

        for idx, result in enumerate(results, start=1):
            _print_json(f"Probe {idx}", result)

        summary = {
            "comment_probes": [
                {
                    "main_saw_new_comment": r["main_saw_new_comment"],
                    "fresh_saw_new_comment": r["fresh_saw_new_comment"],
                    "main_last_comment_matches": r["main_last_comment_matches"],
                    "fresh_last_comment_matches": r["fresh_last_comment_matches"],
                    "cli_returncode": r["cli"]["returncode"],
                }
                for r in results
                if r["probe"] == "comment"
            ],
            "commit_plan_probes": [
                {
                    "main_saw_new_plan": r["main_saw_new_plan"],
                    "fresh_saw_new_plan": r["fresh_saw_new_plan"],
                    "cli_returncode": r["cli"]["returncode"],
                }
                for r in results
                if r["probe"] == "commit_plan"
            ],
            "direct_sqlite_probes": [
                {
                    "fresh_last_comment_matches": r["fresh_last_comment_matches"],
                }
                for r in results
                if r["probe"] == "direct_sqlite"
            ],
        }
        _print_json("Summary", summary)
        return 0
    finally:
        main_conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
