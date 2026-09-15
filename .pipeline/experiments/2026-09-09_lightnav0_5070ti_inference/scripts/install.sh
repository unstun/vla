#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$TASK_ROOT"
mkdir -p work setup
tar -xzf setup/lightnav0_src.tgz -C work
python3 - <<'PY'
from pathlib import Path
paths=list(Path('work').rglob('._*'))
for p in paths:
    if p.is_file(): p.unlink()
print('Removed task-extracted AppleDouble files:',len(paths))
PY
python3 scripts/verify_work_copy.py setup/upstream_file_manifest.json work/LightNav-0 setup/source_verification.json
UV=/home/sun/.local/bin/uv
export UV_CACHE_DIR="$TASK_ROOT/env/uv_cache"
export UV_LINK_MODE=copy
export UV_PYTHON_DOWNLOADS=never
export UV_HTTP_TIMEOUT=120
export UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
"$UV" venv --python /home/sun/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3 env/inference
"$UV" pip install --python env/inference/bin/python -e './work/LightNav-0[vllm,video]'
"$UV" pip freeze --python env/inference/bin/python > setup/pip_freeze.txt
env/inference/bin/python - <<'PY'
import json,platform,importlib.metadata as md,torch
info={'python':platform.python_version(),'torch':torch.__version__,'cuda':torch.version.cuda,
      'gpu':torch.cuda.get_device_name(0),'capability':torch.cuda.get_device_capability(0),
      'arch_list':torch.cuda.get_arch_list(),
      'versions':{p:md.version(p) for p in ['vllm','transformers','nvidia-cutlass-dsl','torchvision']}}
x=torch.randn(64,64,device='cuda',dtype=torch.bfloat16)
y=x@x
torch.cuda.synchronize()
assert torch.isfinite(y).all()
info['bf16_cuda_matmul_finite']=True
print(json.dumps(info,indent=2))
open('setup/environment.json','w').write(json.dumps(info,indent=2)+'\n')
PY
