#!/usr/bin/env bash
set -euo pipefail
experiment_root=$(cd "$(dirname "$0")/.." && pwd)
base_python=/home/sun/miniconda3/envs/isaaclab/bin/python
"$base_python" -m venv --system-site-packages "$experiment_root/venv"
"$experiment_root/venv/bin/python" -m pip install --disable-pip-version-check \
  'transformers==4.37.2' 'tokenizers==0.15.2' 'accelerate==0.27.2' \
  'bitsandbytes==0.49.2' 'sentencepiece==0.2.0' 'shortuuid==1.0.13' \
  'einops==0.8.1' 'einops-exts==0.0.4' 'timm==0.9.12' \
  'decord==0.6.0' 'loguru==0.7.3' 'hydra-core==1.3.2' 'ftfy==6.3.1'
"$experiment_root/venv/bin/python" -m pip freeze > "$experiment_root/setup/pip_freeze.txt"
"$experiment_root/venv/bin/python" - <<'PY'
import json
import torch
import bitsandbytes as bnb
import transformers
layer = bnb.nn.Linear4bit(128, 64, bias=False, quant_type='nf4',
                         compute_dtype=torch.float16).cuda()
result = layer(torch.randn(2, 128, device='cuda', dtype=torch.float16))
torch.cuda.synchronize()
assert torch.isfinite(result).all()
print(json.dumps({'gpu':torch.cuda.get_device_name(), 'torch':torch.__version__,
 'transformers':transformers.__version__, 'bnb':bnb.__version__,
 'shape':list(result.shape), 'nf4_cuda_smoke':True}))
PY
