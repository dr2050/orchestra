#!/usr/bin/env bash
# Propagate the canonical global agent instructions to the per-agent files.
#
# Source of truth: "$ORCHESTRA_DIR"/global-agent-instructions.md
# Targets:
#   ~/.claude/CLAUDE.md   title: "Global Claude Code Instructions"
#   ~/.codex/AGENTS.md    title: "Global Codex Instructions"
#   ~/.gemini/GEMINI.md   title: "Global Gemini Instructions"
#
# Usage:
#   sync-global-agent-instructions.sh             # write changes
#   sync-global-agent-instructions.sh --dry-run   # show what would change, no writes
#   sync-global-agent-instructions.sh --check     # exit 1 if any target is out of sync (for CI/pre-commit)

set -euo pipefail

if [[ -z "${ORCHESTRA_DIR:-}" ]]; then
  echo "error: ORCHESTRA_DIR is not set. export ORCHESTRA_DIR=/path/to/orchestra" >&2
  exit 2
fi
if [[ ! -d "$ORCHESTRA_DIR" ]]; then
  echo "error: ORCHESTRA_DIR=$ORCHESTRA_DIR is not a directory" >&2
  exit 2
fi

SRC="$ORCHESTRA_DIR/global-agent-instructions.md"
if [[ ! -f "$SRC" ]]; then
  echo "error: source file not found: $SRC" >&2
  exit 2
fi

MODE="write"
case "${1:-}" in
  --dry-run) MODE="dry-run" ;;
  --check)   MODE="check" ;;
  "")        MODE="write" ;;
  *) echo "unknown arg: $1 (expected --dry-run | --check)" >&2; exit 2 ;;
esac

# target_path<TAB>title
TARGETS=(
  "$HOME/.claude/CLAUDE.md	Global Claude Code Instructions"
  "$HOME/.codex/AGENTS.md	Global Codex Instructions"
  "$HOME/.gemini/GEMINI.md	Global Gemini Instructions"
)

render() {
  # $1 = title; reads SRC, prints rendered output with {{TITLE}} substituted.
  local title="$1"
  # Substitute the H1 placeholder on line 1 only, so mentions of the
  # `{{TITLE}}` token elsewhere in the file (e.g. the comment block) survive.
  awk -v t="$title" 'NR==1 { gsub(/\{\{TITLE\}\}/, t) } { print }' "$SRC"
}

out_of_sync=0
for entry in "${TARGETS[@]}"; do
  target="${entry%%$'\t'*}"
  title="${entry##*$'\t'}"
  rendered="$(render "$title")"

  if [[ -f "$target" ]] && [[ "$rendered" == "$(cat "$target")" ]]; then
    echo "= $target (up to date)"
    continue
  fi

  case "$MODE" in
    check)
      out_of_sync=1
      echo "≠ $target (out of sync)"
      ;;
    dry-run)
      out_of_sync=1
      echo "~ $target (would update)"
      if [[ -f "$target" ]]; then
        diff -u "$target" <(printf '%s\n' "$rendered") || true
      else
        echo "  (target does not exist; would create)"
      fi
      ;;
    write)
      mkdir -p "$(dirname "$target")"
      printf '%s\n' "$rendered" > "$target"
      echo "✓ $target (updated)"
      ;;
  esac
done

if [[ "$MODE" == "check" && "$out_of_sync" -ne 0 ]]; then
  exit 1
fi
