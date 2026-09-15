#!/usr/bin/env bash
# Official LightNav-0 inference environment: python3.11 venv + `pip install -e ".[vllm,video]"`.
# uv performs the install (as upstream's Dockerfile does); the index is the Tsinghua PyPI
# mirror because PyPI direct measured ~0.6 MB/s from this host. Package pins are upstream's.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export UV_PYTHON="$ROOT/env/py311/bin/python"
export UV_PYTHON_DOWNLOADS=never
export UV_DEFAULT_INDEX="${PIP_INDEX:-https://pypi.tuna.tsinghua.edu.cn/simple}"
export UV_CACHE_DIR="$ROOT/env/uv_cache"
export UV_LINK_MODE=copy
UV="$ROOT/env/py311/bin/uv"
cd "$ROOT/work/LightNav-0"
"$UV" --version
"$UV" venv --python "$UV_PYTHON" .venv
"$UV" pip install --python .venv/bin/python -e ".[vllm,video]"
"$UV" pip freeze --python .venv/bin/python > "$ROOT/setup/pip_freeze_lightnav.txt"
.venv/bin/python - <<'PY'
import json, platform, torch, transformers, vllm, importlib.metadata as md
info = {
    "python": platform.python_version(),
    "torch": torch.__version__, "torch_cuda": torch.version.cuda,
    "cuda_available": torch.cuda.is_available(),
    "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    "capability": list(torch.cuda.get_device_capability(0)) if torch.cuda.is_available() else None,
    "transformers": transformers.__version__, "vllm": vllm.__version__,
    "nvidia_cutlass_dsl": md.version("nvidia-cutlass-dsl"),
    "torchvision": md.version("torchvision"), "websockets": md.version("websockets"),
    "opencv": md.version("opencv-python-headless"), "imageio_ffmpeg": md.version("imageio-ffmpeg"),
}
print(json.dumps(info, indent=2))
assert info["cuda_available"], "torch.cuda.is_available() is False; vllm_local cannot start"
PY
.venv/bin/lightnav-serve --help > /dev/null
echo LIGHTNAV_INSTALL_COMPLETE
