#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 setup/virtualenv.pyz venv --python python3
venv/bin/python -m pip install --disable-pip-version-check 'torch==2.6.0' 'torchvision==0.21.0' --index-url https://download.pytorch.org/whl/cu124
venv/bin/python -m pip install --disable-pip-version-check 'transformers==4.51.0' 'diffusers==0.33.1' 'accelerate==1.4.0' 'huggingface-hub==0.33.4' 'numpy==1.26.4' 'pillow==10.4.0' 'opencv-python-headless==4.10.0.84' 'scipy==1.14.1' 'einops==0.8.1' 'ftfy==6.3.1' 'imageio==2.37.0' 'imageio-ffmpeg==0.6.0' 'matplotlib==3.9.4' 'flask==3.1.0' 'psutil==5.9.8' 'timm==1.0.15'
venv/bin/python -m pip install --disable-pip-version-check --no-deps 'https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.3/flash_attn-2.7.3%2Bcu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl'
venv/bin/python -m pip freeze > setup/pip_freeze.txt
venv/bin/python -c 'import torch,flash_attn,transformers; print(torch.__version__,torch.version.cuda,flash_attn.__version__,transformers.__version__,torch.cuda.get_device_name(0))'
printf '%s\n' SETUP_COMPLETE
