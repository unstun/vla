#!/usr/bin/env bash
# Phase A of the official SETUP.md environment: conda env + the four pinned
# packages. Runs before the work copy exists so it can overlap the download.
set -euo pipefail
REMOTE=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda
# See remote_download.sh: prefix env inside the workspace, conda-forge only.
export CONDA_PKGS_DIRS=$REMOTE/conda_pkgs_main   # separate from the download env: two concurrent conda processes sharing one package cache race on *.partial files
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
ENV=$REMOTE/envs/omnivla_sun

if [ ! -x "$ENV/bin/python" ]; then
  conda create -p "$ENV" python=3.10 -y -c conda-forge --override-channels
fi
conda activate "$ENV"
python -V
# Direct pypi.org downloads on this host sustained only about 60-130 KiB/s and
# had not completed the first torch wheel after 100 minutes.  The Tsinghua
# mirror returned the same PEP 503 package index over TLS in the preflight probe
# and is an install-source deviation only; the four version pins remain exact.
export PIP_INDEX_URL=${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}
echo "[remote_env_a] PIP_INDEX_URL=$PIP_INDEX_URL"
# SETUP.md, verbatim pins
pip3 install numpy==1.26.4 torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0
python - <<'PY'
import torch, platform
print("torch", torch.__version__, "cuda_build", torch.version.cuda,
      "available", torch.cuda.is_available())
if torch.cuda.is_available():
    print("device", torch.cuda.get_device_name(0),
          "capability", torch.cuda.get_device_capability(0))
print("python", platform.python_version())
PY
echo "[remote_env_a] finished"
