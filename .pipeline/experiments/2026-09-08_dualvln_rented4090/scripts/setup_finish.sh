#!/usr/bin/env bash
# Completes scripts/setup_remote.sh after the FlashAttention wheel was obtained
# out of band: the pinned GitHub release asset served this host at ~25 KiB/s, so
# it was fetched from the same authoritative URL on the local workstation and
# pushed to setup/wheels/. Same pinned filename, same build tag.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
WHEEL="setup/wheels/flash_attn-2.7.3+cu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl"
test -f "$WHEEL"
sha256sum "$WHEEL"
python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).testzip(); print('wheel zip ok')" "$WHEEL"
venv/bin/python -m pip install --disable-pip-version-check --no-deps "$WHEEL"
venv/bin/python -m pip freeze > setup/pip_freeze.txt
venv/bin/python -c 'import torch,flash_attn,transformers,diffusers; print(torch.__version__,torch.version.cuda,flash_attn.__version__,transformers.__version__,diffusers.__version__,torch.cuda.get_device_name(0))'
venv/bin/python - <<'PY'
import torch, flash_attn, subprocess, json
from flash_attn import flash_attn_func
q = torch.randn(1, 8, 4, 32, dtype=torch.bfloat16, device='cuda')
o = flash_attn_func(q, q, q)
info = {'flash_attn': flash_attn.__version__,
        'kernel_out_shape': list(o.shape),
        'kernel_finite': bool(torch.isfinite(o).all()),
        'torch': torch.__version__, 'cuda': torch.version.cuda,
        'device': torch.cuda.get_device_name(0),
        'bf16_supported': torch.cuda.is_bf16_supported()}
print('FLASH_ATTN_KERNEL_CHECK ' + json.dumps(info))
PY
printf '%s\n' SETUP_COMPLETE
