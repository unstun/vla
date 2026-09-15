#!/usr/bin/env bash
# Phase B of the official SETUP.md environment: the editable install of the
# (patched) upstream package and Flash Attention 2. Requires the work copy.
set -uo pipefail
REMOTE=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda
export CONDA_PKGS_DIRS=$REMOTE/conda_pkgs_main
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
conda activate "$REMOTE/envs/omnivla_sun"
export PIP_CACHE_DIR=$REMOTE/pip_cache
mkdir -p "$PIP_CACHE_DIR"
export PIP_INDEX_URL=${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}
echo "[remote_env_b] PIP_INDEX_URL=$PIP_INDEX_URL"
echo "[remote_env_b] PIP_CACHE_DIR=$PIP_CACHE_DIR"
set -x

# SETUP.md: `cd OmniVLA && pip install -e .`. gpu40901's direct GitHub clone
# stalled without receiving bytes. The exact two Git dependencies are pinned,
# manifest-verified local snapshots; all other dependency declarations remain
# verbatim in remote_requirements.txt.
if pip install -e "$REMOTE/work/OmniVLA" --no-deps \
   && pip install -r "$REMOTE/scripts/remote_requirements.txt"; then
  rc_editable=0
else
  rc_editable=$?
  echo "[remote_env_b] editable install failed rc=$rc_editable" >&2
  exit "$rc_editable"
fi

# SETUP.md: flash-attn is documented for training. Strategy (design.md):
#   (a) official prebuilt wheel for cp310 / torch2.2 / cu12x / cxx11abiFALSE
#   (b) source build with MAX_JOBS=4 (shared host), timeboxed
#   (c) skip and record
pip install packaging ninja
ninja --version; echo "ninja rc=$?"
WHL=flash_attn-2.5.5+cu122torch2.2cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
URL=https://github.com/Dao-AILab/flash-attention/releases/download/v2.5.5/$WHL
flash_status=unknown
if wget -q --tries=3 --timeout=60 -O "$REMOTE/env/$WHL" "$URL"; then   # curl is not installed on this host
  if pip install "$REMOTE/env/$WHL"; then flash_status="prebuilt-wheel"; else flash_status="prebuilt-wheel-install-failed"; fi
else
  flash_status="prebuilt-wheel-download-failed"
fi
if [ "$flash_status" != "prebuilt-wheel" ]; then
  echo "[env_b] falling back to source build (MAX_JOBS=4, 25 min timebox)"
  if MAX_JOBS=4 timeout 1500 nice -n 10 pip install "flash-attn==2.5.5" --no-build-isolation; then
    flash_status="source-build"
  else
    flash_status="not-installed"
  fi
fi
set +x
echo "[env_b] flash_attn status: $flash_status" | tee "$REMOTE/env/flash_attn_status.txt"
python -c "import flash_attn, sys; print('flash_attn', flash_attn.__version__)" 2>&1 | tee -a "$REMOTE/env/flash_attn_status.txt"

pip freeze > "$REMOTE/env/pip_freeze.txt"
python - <<'PY' | tee "$REMOTE/env/torch_probe.txt"
import platform, torch, sys
print("python", platform.python_version())
print("torch", torch.__version__, "cuda_build", torch.version.cuda,
      "cudnn", torch.backends.cudnn.version())
print("cuda_available", torch.cuda.is_available())
if torch.cuda.is_available():
    p = torch.cuda.get_device_properties(0)
    print("device", p.name, "total_memory_bytes", p.total_memory,
          "capability", f"{p.major}.{p.minor}")
try:
    import flash_attn
    print("flash_attn", flash_attn.__version__)
except Exception as e:
    print("flash_attn import failed:", type(e).__name__, e)
try:
    import transformers
    print("transformers", transformers.__version__)
except Exception as e:
    print("transformers import failed:", e)
try:
    import prismatic
    print("prismatic", prismatic.__file__)
except Exception as e:
    print("prismatic import failed:", type(e).__name__, e)
    raise
PY
nvidia-smi > "$REMOTE/env/nvidia_smi.txt" 2>&1
nvidia-smi -q > "$REMOTE/env/nvidia_smi_full.txt" 2>&1
{ echo "== uname =="; uname -a; echo "== lsb =="; cat /etc/os-release; echo "== cpu =="; lscpu | head -20;
  echo "== mem =="; free -g; echo "== disk =="; df -h /home; } > "$REMOTE/env/hardware.txt" 2>&1
python -m py_compile "$REMOTE/work/OmniVLA/inference/run_omnivla.py" && echo "[env_b] py_compile run_omnivla.py OK"
python -m py_compile "$REMOTE/work/OmniVLA/inference/run_omnivla_edge.py" && echo "[env_b] py_compile run_omnivla_edge.py OK"
echo "[remote_env_b] finished (editable install rc=$rc_editable, flash=$flash_status)"
