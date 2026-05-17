#!/usr/bin/env python3
"""repo_policy.py — Parse repo-local policy markers from AGENTS.md."""

from pathlib import Path


def read_skip_build_until_approved(repo_root) -> bool:
    """Return True if AGENTS.md in repo_root contains the SKIP_BUILD_UNTIL_APPROVED marker.

    The marker must appear as a standalone line (after stripping whitespace):
        SKIP_BUILD_UNTIL_APPROVED
    Freeform prose mentioning the marker name does not count.
    """
    agents_md = Path(repo_root) / "AGENTS.md"
    if not agents_md.exists():
        return False
    try:
        text = agents_md.read_text(encoding="utf-8")
    except OSError:
        return False
    for line in text.splitlines():
        if line.strip() == "SKIP_BUILD_UNTIL_APPROVED":
            return True
    return False
