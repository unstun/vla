#!/usr/bin/env bash
# Run the full camera-condition matrix, condition-major, each run under the
# task-owned supervisor with a 1,800 s deadline. Never stops on a failed run;
# stops only after two consecutive CUDA out-of-memory failures. Skips run ids
# that already exist so the matrix can be resumed.
#
#   bash public_scenes/requests/2026-09-10_lite3_camera_ablation/run_matrix.sh [conditions...]
# Environment: RUNS_PER_CONDITION (default 5), DEADLINE_SECONDS (default 1800).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
REQ_REL="public_scenes/requests/2026-09-10_lite3_camera_ablation"
LOG="$ROOT/$REQ_REL/matrix_log.jsonl"
RUNS_PER_CONDITION="${RUNS_PER_CONDITION:-5}"
DEADLINE_SECONDS="${DEADLINE_SECONDS:-1800}"
if [ "$#" -gt 0 ]; then
  CONDS=("$@")
else
  CONDS=(c1_lite3_rig c2_height_only c3_fov_only c4_raised_mount c5_head_level c6_head_down15)
fi

cd "$ROOT" || exit 1
oom_streak=0
for cond in "${CONDS[@]}"; do
  if [ ! -f "$REQ_REL/preflight/${cond}.json" ]; then
    echo "SKIP condition $cond: no preflight report" | tee -a "$LOG.txt"
    continue
  fi
  if ! python3 -c "import json,sys; r=json.load(open('$REQ_REL/preflight/${cond}.json')); sys.exit(0 if r.get('all_stages_passed') and r.get('condition')=='$cond' else 1)"; then
    echo "SKIP condition $cond: preflight report did not pass all stages" | tee -a "$LOG.txt"
    continue
  fi
  for k in $(seq 1 "$RUNS_PER_CONDITION"); do
    run_id="cam_${cond}_v${k}"
    if [ -e "runs/$run_id" ] || [ -e "public_scenes/runs/$run_id" ]; then
      echo "SKIP $run_id: already exists" | tee -a "$LOG.txt"
      continue
    fi
    echo "== $(date -u +%Y-%m-%dT%H:%M:%SZ) START $run_id ==" | tee -a "$LOG.txt"
    python3 scripts/run_job.py --seconds "$DEADLINE_SECONDS" "$run_id" -- \
      bash "$REQ_REL/run_cam_eval.sh" "$cond" "$run_id"
    meta="runs/$run_id/meta.json"
    if [ -f "$meta" ]; then
      python3 - "$meta" "$run_id" "$cond" "$LOG" <<'PYEOF'
import json, sys
meta, run_id, cond, log = sys.argv[1:]
m = json.load(open(meta))
rec = {'run_id': run_id, 'condition': cond, 'exit_code': m['exit_code'], 'timed_out': m['timed_out'],
       'wall_seconds': round(m['wall_seconds'], 1)}
open(log, 'a').write(json.dumps(rec) + '\n')
print('MATRIX', json.dumps(rec))
PYEOF
    else
      echo "{\"run_id\": \"$run_id\", \"condition\": \"$cond\", \"exit_code\": null, \"note\": \"no supervisor meta\"}" >> "$LOG"
    fi
    if grep -q "CUDA out of memory" "runs/$run_id/stderr.log" 2>/dev/null; then
      oom_streak=$((oom_streak + 1))
    else
      oom_streak=0
    fi
    if [ "$oom_streak" -ge 2 ]; then
      echo "STOP: two consecutive CUDA out-of-memory failures; check the shared GPU before resuming" | tee -a "$LOG.txt"
      exit 7
    fi
  done
done
echo "MATRIX_DONE" | tee -a "$LOG.txt"
