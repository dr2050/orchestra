# Optional zsh helpers for running Orchestra from a work repository.
#
# Source this file from ~/.zshrc after ORCHESTRA_DIR is set:
#
#   source "$ORCHESTRA_DIR/shell/orchestra.zsh"
#
# The commands below intentionally require the current directory to be the root
# of a git repository. Orchestra uses the launch directory as the work repo, so
# refusing nested directories avoids accidentally supervising the wrong project.

_orchestra_physical_path() {
  emulate -L zsh
  (builtin cd -P -- "$1" 2>/dev/null && pwd -P)
}

_orchestra_require_git_root() {
  emulate -L zsh

  local git_root physical_root physical_pwd

  git_root="$(command git rev-parse --show-toplevel 2>/dev/null)" || {
    print -u2 "orchestra: run this from the root of a git work repository"
    return 2
  }

  physical_root="$(_orchestra_physical_path "$git_root")" || {
    print -u2 "orchestra: could not resolve git repository root: $git_root"
    return 2
  }
  physical_pwd="$(pwd -P)"

  if [[ "$physical_pwd" != "$physical_root" ]]; then
    print -u2 "orchestra: run this from the git repository root:"
    print -u2 "  $physical_root"
    return 2
  fi
}

_orchestra_run_from_git_root() {
  emulate -L zsh

  local command_name="$1"
  shift

  _orchestra_require_git_root || return

  if [[ -z "${ORCHESTRA_DIR:-}" ]]; then
    print -u2 "orchestra: ORCHESTRA_DIR is not set"
    return 2
  fi

  if [[ ! -x "$ORCHESTRA_DIR/bin/$command_name" ]]; then
    print -u2 "orchestra: expected executable not found: $ORCHESTRA_DIR/bin/$command_name"
    return 2
  fi

  "$ORCHESTRA_DIR/bin/$command_name" "$@"
}

orchestra-ui() {
  _orchestra_run_from_git_root ko-ui "$@"
}

orchestra-dashboard() {
  _orchestra_run_from_git_root ko-dashboard "$@"
}

orchestra-status() {
  # Forward additional arguments so options such as --control-timeout still work.
  _orchestra_run_from_git_root ko-ui --orchestrator-control status "$@"
}

orchestra-start() {
  # Forward additional arguments so options such as --control-timeout still work.
  _orchestra_run_from_git_root ko-ui --orchestrator-control start "$@"
}

orchestra-stop() {
  # Forward additional arguments so options such as --control-timeout still work.
  _orchestra_run_from_git_root ko-ui --orchestrator-control stop "$@"
}

orchestra-break() {
  # Forward additional arguments so options such as --control-timeout still work.
  _orchestra_run_from_git_root ko-ui --orchestrator-control break "$@"
}

alias orchestra='orchestra-ui'
alias odash='orchestra-dashboard'
alias ostatus='orchestra-status'
alias ostart='orchestra-start'
alias ostop='orchestra-stop'
alias obreak='orchestra-break'
