#!/usr/bin/env bash

set -euo pipefail

PROBE_DIR="${1:-$HOME/eraseme/kanban-probe}"
AI_BOX_WRAPPER="${AI_BOX_WRAPPER:-$HOME/scripts/ai-box}"

if [ -z "${ORCHESTRA_DIR:-}" ]; then
  echo "ORCHESTRA_DIR is not set." >&2
  exit 1
fi

cat <<EOF
Reference from your ai-box setup:
- host project dir: ${PROBE_DIR}
- container workdir: /work
- container orchestra dir: /orchestra

Commands to run manually:

1. Start or reuse the ai-box container for the probe repo:
cd "$(printf '%s' "${PROBE_DIR}")" && "${AI_BOX_WRAPPER}"

2. Open a shell in that same container:
cd "$(printf '%s' "${PROBE_DIR}")" && ai-box-shell

3. Run the SQLite visibility probe inside the container:
python3 "\$ORCHESTRA_DIR/kanban-orchestra/scripts/probe_sqlite_visibility.py" \\
  --db /work/kanban-orchestra.db \\
  --task-id 1 \\
  --iterations 3 \\
  --mode both

4. Optional control case with one raw sqlite write too:
python3 "\$ORCHESTRA_DIR/kanban-orchestra/scripts/probe_sqlite_visibility.py" \\
  --db /work/kanban-orchestra.db \\
  --task-id 1 \\
  --iterations 3 \\
  --mode both \\
  --include-direct-sqlite

5. If you want to seed a fresh probe repo on the host before entering the container:
mkdir -p "$(printf '%s' "${PROBE_DIR}")"
cd "$(printf '%s' "${PROBE_DIR}")"
"\$ORCHESTRA_DIR/bin/ko-init-test-repo"

Notes:
- ai-box mounts the current host directory at /work, so /work/kanban-orchestra.db is the host file ${PROBE_DIR}/kanban-orchestra.db
- this helper expects ORCHESTRA_DIR to already be defined in your environment
- this helper prints commands only; it does not run Docker
EOF
