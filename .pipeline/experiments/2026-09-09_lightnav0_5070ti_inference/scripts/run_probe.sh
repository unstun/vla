#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$TASK_ROOT"
MODE="$1"
RUN_NAME="$2"
python3 scripts/verify_work_copy.py setup/upstream_file_manifest.json work/LightNav-0 "runs/$RUN_NAME/source_verification.json"
python3 scripts/download_checkpoint.py setup/model_source.json checkpoints/LightNav-0 "runs/$RUN_NAME/checkpoint_verification.json" --verify-only
python3 - "$RUN_NAME" <<'PY'
import hashlib,json,sys
from pathlib import Path
rows=json.loads(Path('setup/task_manifest.json').read_text())['files']
for r in rows:
    p=Path(r['path'])
    assert p.stat().st_size==r['bytes']
    assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],r['path']
report={'passed':True,'matched_files':len(rows)}
Path('runs',sys.argv[1],'task_verification.json').write_text(json.dumps(report,indent=2)+'\n')
print('TASK_SOURCE_AND_INPUT_HASHES_PASS',len(rows))
PY
export CUDA_VISIBLE_DEVICES=0
export PYTHONUNBUFFERED=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TORCHINDUCTOR_CACHE_DIR="$TASK_ROOT/env/torchinductor"
export TRITON_CACHE_DIR="$TASK_ROOT/env/triton"
exec env/inference/bin/python scripts/probe.py --mode "$MODE" --output "runs/$RUN_NAME/evidence"
