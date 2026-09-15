#!/usr/bin/env bash
# Bring one run's evidence back from an execution host to this repository, then hash everything.
# A remote-only success is not reproducible evidence (AGENTS.md), so nothing counts until it lands here.
#
#   VLA_SSH_OPTS="-J gpu40901" scripts/collect_run.sh rented4090 RUN_ID [REMOTE_ROOT]
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "usage: $0 SSH_TARGET RUN_ID [REMOTE_ROOT]" >&2
  exit 64
fi
TARGET=$1
RUN_ID=$2
REMOTE_ROOT=${3:-/home/ubuntu/vla-runs/2026-09-11_lite3_isaac_v12_vla}

read -r -a SSH_OPTS <<< "${VLA_SSH_OPTS:-}"
EXP_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DEST=$EXP_DIR/runs/$RUN_ID

[[ -e $DEST ]] && { echo "local evidence already exists; refusing to overwrite: $DEST" >&2; exit 73; }
mkdir -p "$DEST"

# One tar stream, not scp -r: through the jump host scp managed ~0.4 files/s on a 4,500-file run, and tar keeps
# symlinks as links instead of following them into whatever they point at.
ssh "${SSH_OPTS[@]}" -o BatchMode=yes -o ConnectTimeout=30 "$TARGET" \
  "tar -C '$REMOTE_ROOT/runs/$RUN_ID' -cf - ." | tar -C "$DEST" -xf -
if [[ -n $(find "$DEST" -type l) ]]; then
  echo "  WARNING: symlinks in collected run (not hashed):" >&2
  find "$DEST" -type l -exec ls -l {} \; >&2
fi
scp "${SSH_OPTS[@]}" -o BatchMode=yes -o ConnectTimeout=30 \
  "$TARGET:$REMOTE_ROOT/driver_$RUN_ID.log" "$DEST/driver.log" 2>/dev/null || \
  echo "  (no driver log for $RUN_ID)"

# NUL-separated: InternNav's agent names debug images "debug_raw_ 000.jpg" (format spec ' 04d').
( cd "$DEST" && find . -type f ! -name manifest.sha256 -print0 | sort -z | xargs -0 shasum -a 256 > manifest.sha256 )
echo "collected $(find "$DEST" -type f | wc -l | tr -d ' ') files into runs/$RUN_ID"
( cd "$DEST" && shasum -a 256 -c manifest.sha256 | grep -cv ': OK' || true ) | \
  xargs -I{} echo "  non-OK entries: {}"
