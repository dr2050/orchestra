"""
Shared runtime config for the AI orchestration pipeline.
"""

import sys
from pathlib import Path

# Allow importing from repo root (shared_scripts/).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from shared_scripts.shared_config import AGENT_CMD, AGENT_DISPLAY_LABELS  # noqa: E402  (after sys.path insert)

FEATURE_VERBS = [
    "plan-feature-make",
    "plan-feature-review",
]

FEATURE_PHASE_VERBS = [
    "plan-feature-phase-make",
    "plan-feature-phase-review",
    "commits-make",
    "commits-review",
    "pull-request-make",
    "pull-request-review",
]

VERBS = FEATURE_VERBS + FEATURE_PHASE_VERBS


def task_file_name(verb: str) -> str:
    return {
        "plan-feature-make": "01-plan-feature-make.md",
        "plan-feature-review": "02-plan-feature-review.md",
        "plan-feature-phase-make": "03-plan-feature-phase-make.md",
        "plan-feature-phase-review": "04-plan-feature-phase-review.md",
        "commits-make": "05-commits-make.md",
        "commits-review": "06-commits-review.md",
        "pull-request-make": "07-pull-request-make.md",
        "pull-request-review": "08-pull-request-review.md",
    }[verb]


def prompt_file_name(verb: str) -> str:
    return {
        "plan-feature-make": "01-plan-feature-make-prompt.md",
        "plan-feature-review": "02-plan-feature-review-prompt.md",
        "plan-feature-phase-make": "03-plan-feature-phase-make-prompt.md",
        "plan-feature-phase-review": "04-plan-feature-phase-review-prompt.md",
        "commits-make": "05-commits-make-prompt.md",
        "commits-review": "06-commits-review-prompt.md",
        "pull-request-make": "07-pull-request-make-prompt.md",
        "pull-request-review": "08-pull-request-review-prompt.md",
    }[verb]

# Which prior verb files each verb reads for context (in order).
VERB_READS_FROM = {
    "plan-feature-make": ["plan-feature-review"],
    "plan-feature-review": ["plan-feature-make"],
    "plan-feature-phase-make": ["plan-feature-phase-review"],
    "plan-feature-phase-review": ["plan-feature-phase-make"],
    "commits-make": ["plan-feature-phase-make", "commits-review", "pull-request-review"],
    "commits-review": ["commits-make"],
    "pull-request-make": ["plan-feature-phase-make"],
    "pull-request-review": ["pull-request-make"],
}

# Which agent runs each verb. Edit these to switch agents.
VERB_AGENT = {
    "plan-feature-make":         "codex",
    "plan-feature-review":       "claude",
    "plan-feature-phase-make":   "codex",
    "plan-feature-phase-review": "claude",
    "commits-make":              "claude",
    "commits-review":            "codex",
    "pull-request-make":         "codex",
    "pull-request-review":       "claude",
}

# Agent used by the dashboard live summary panel.
DASHBOARD_AGENT = "claude"
