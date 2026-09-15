#!/usr/bin/env bash
# Stage the Phase A bundle onto an execution host and prove the bytes survived the trip.
#
#   scripts/phase_a_stage.sh SSH_TARGET [REMOTE_ROOT]
#
# Creates REMOTE_ROOT, uploads the archive, compares SHA-256 on the host against the local
# bundle_manifest.json, extracts, and re-verifies the checkpoint. Writes nothing outside REMOTE_ROOT
# and starts no simulator. Safe to re-run: it refuses to extract over an existing tree.
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "usage: $0 SSH_TARGET [REMOTE_ROOT]" >&2
  exit 64
fi
TARGET=$1
REMOTE_ROOT=${2:-'$HOME/vla-runs/2026-09-11_lite3_isaac_v12_vla'}

# Some hosts are only reachable through a jump box (rented4090 needs `-J gpu40901`; the direct
# alias times out during banner exchange). Pass extra ssh/scp options with VLA_SSH_OPTS.
read -r -a SSH_OPTS <<< "${VLA_SSH_OPTS:-}"

EXP_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
ARCHIVE=$EXP_DIR/setup/bundle/phase_a_bundle.tar.gz
MANIFEST=$EXP_DIR/setup/bundle/bundle_manifest.json

for f in "$ARCHIVE" "$MANIFEST"; do
  [[ -f $f ]] || { echo "missing $f; run scripts/build_bundle.py first" >&2; exit 66; }
done

EXPECTED=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['archive_sha256'])" "$MANIFEST")
LOCAL=$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')
if [[ $LOCAL != "$EXPECTED" ]]; then
  echo "local archive does not match its own manifest; rebuild the bundle" >&2
  exit 65
fi
echo "local archive sha256 $LOCAL"

# REMOTE_ROOT may contain $HOME, which the remote LOGIN SHELL expands but scp does not: modern scp
# speaks SFTP, where the path is literal. So resolve it to an absolute path on the host first.
# shellcheck disable=SC2029
RESOLVED_ROOT=$(ssh "${SSH_OPTS[@]}" -o BatchMode=yes -o ConnectTimeout=30 "$TARGET" "
set -euo pipefail
ROOT=$REMOTE_ROOT
mkdir -p \"\$ROOT\"
cd \"\$ROOT\" && pwd
")
echo "remote root $RESOLVED_ROOT"
ssh "${SSH_OPTS[@]}" -o BatchMode=yes -o ConnectTimeout=30 "$TARGET" "df -h '$RESOLVED_ROOT' | tail -1"

echo "uploading $(du -h "$ARCHIVE" | cut -f1) ..."
scp "${SSH_OPTS[@]}" -o BatchMode=yes -o ConnectTimeout=30 "$ARCHIVE" "$TARGET:$RESOLVED_ROOT/phase_a_bundle.tar.gz"

# shellcheck disable=SC2029
ssh "${SSH_OPTS[@]}" -o BatchMode=yes -o ConnectTimeout=30 "$TARGET" "
set -euo pipefail
ROOT=$RESOLVED_ROOT
cd \"\$ROOT\"
REMOTE=\$(sha256sum phase_a_bundle.tar.gz | awk '{print \$1}')
echo \"remote archive sha256 \$REMOTE\"
if [[ \$REMOTE != $EXPECTED ]]; then
  echo 'archive corrupted in transit' >&2
  exit 65
fi
if [[ -e inputs ]]; then
  echo 'inputs/ already exists on the host; not extracting over it'
else
  mkdir inputs
  tar -xzf phase_a_bundle.tar.gz -C inputs
  echo 'extracted'
fi
CK=\$(sha256sum inputs/checkpoint/model_149999.pt | awk '{print \$1}')
echo \"checkpoint sha256 \$CK\"
[[ \$CK == a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450 ]] || { echo 'checkpoint mismatch' >&2; exit 65; }
echo 'file counts:'
printf '  bridge   %s\n' \"\$(find inputs/lite3_sim_bridge -type f | wc -l)\"
printf '  runtime  %s\n' \"\$(find inputs/v12_runtime -type f | wc -l)\"
echo STAGE_OK
"
