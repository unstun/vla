#!/usr/bin/env bash
# Sync v34's frozen files to gpu5070ti's execution copy, then run v34's pre-physics gates there (PHYSICAL_RUN_PLAN.md).
# Run on the MacBook after versions/v34/freeze.py:  bash sync_v34.sh <attempt number>
# - Every file in versions/v34/manifest.json's source_files, plus the manifest itself, is copied to the same relative
#   path under ~/vla_exec/vla (the launcher's version gate re-hashes every one of them before physics).
# - runtime/scan65_evidence_floor_v34 is copied whole (source, build, install and its records), as scan64 was.
# - checks/p1_gates_v34.py then runs on the execution copy; its output returns to checks_out/.
set -euo pipefail
ATTEMPT=$(printf '%02d' "${1:?attempt number}")
R=/Users/sun/tongbu/study/phdproject/vla
E=.pipeline/experiments/2026-09-26_newton_stair_reproduction
G=$R/$E/hosts/2026-09-29_gpu5070ti
LIST=$G/checks_out/sync_v34_files_attempt$ATTEMPT.txt
[ -e "$LIST" ] && { echo "attempt $ATTEMPT already used" >&2; exit 1; }
python3 - "$R/$E/versions/v34/manifest.json" "$E/versions/v34/manifest.json" > "$LIST" <<'EOF'
import json, sys
manifest = json.load(open(sys.argv[1]))
assert manifest["version"] == "v34" and manifest["status"] == "frozen_unvalidated"
print("\n".join(sorted(manifest["source_files"]) + [sys.argv[2]]))
EOF
echo "files listed: $(wc -l < "$LIST")"
rsync -a --files-from="$LIST" "$R/" gpu5070ti:vla_exec/vla/
rsync -a "$R/$E/runtime/scan65_evidence_floor_v34/" "gpu5070ti:vla_exec/vla/$E/runtime/scan65_evidence_floor_v34/"
ssh -o BatchMode=yes gpu5070ti "cd ~/vla_exec/vla/$E && python3 hosts/2026-09-29_gpu5070ti/checks/p1_gates_v34.py" \
  > "$G/checks_out/p1_gates_v34_attempt$ATTEMPT.json"
python3 -c "import json,sys; r=json.load(open(sys.argv[1])); print({k: v.get('passed') for k, v in r.items() if isinstance(v, dict)}, 'passed', r['passed'])" \
  "$G/checks_out/p1_gates_v34_attempt$ATTEMPT.json"
