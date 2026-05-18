#!/usr/bin/env bash
# Install optional local helper CLI utilities used by the author's workflows.
#
# This is a convenience script, not required Orchestra setup.
#
# Idempotent: skips anything already installed; never triggers an upgrade.
#
# Usage:
#   install-brew-tools.sh             # install missing tools
#   install-brew-tools.sh --dry-run   # print what would be installed, no changes

set -euo pipefail

DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

if ! command -v brew >/dev/null 2>&1; then
  echo "error: Homebrew not installed. See https://brew.sh" >&2
  exit 2
fi

export HOMEBREW_NO_INSTALL_UPGRADE=1
export HOMEBREW_NO_AUTO_UPDATE=1

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '+ %s\n' "$*"
  else
    echo "+ $*"
    "$@"
  fi
}

# Helper CLI utilities. Each entry is the Homebrew formula name.
# Trailing "# binary: <name>" comments map formulae whose binary differs.
FORMULAE=(
  ripgrep        # binary: rg
  fd
  jq
  gron
  yq
  sd
  choose-rust    # binary: choose
  miller         # binary: mlr
  git-delta      # binary: delta
  git-absorb
  bat
  eza
  dust
  duf
  procs
  zoxide         # binary: z (after shell init)
  tokei
  xh
  hyperfine
  entr
  fswatch
  ouch
  tealdeer       # binary: tldr
  ffmpeg
  pandoc
)

missing=()
for f in "${FORMULAE[@]}"; do
  brew list --formula --versions "$f" >/dev/null 2>&1 || missing+=("$f")
done

if [[ ${#missing[@]} -eq 0 ]]; then
  echo "All ${#FORMULAE[@]} agent CLI tools already installed."
  exit 0
fi

echo "Installing ${#missing[@]} missing tool(s): ${missing[*]}"
run brew install "${missing[@]}"
