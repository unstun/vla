#!/usr/bin/env bash
# Isolated environment for the OFFICIAL InternNav Habitat evaluator
# (scripts/eval/eval.py + habitat_vln_evaluator.py).
#
# The official evaluator runs habitat-lab and the BF16 model in ONE process, so
# unlike the earlier two-process trial this env must hold both. The pinned repo
# does not pin habitat-lab / habitat-sim versions anywhere in requirements/, so
# habitat-sim 0.3.3 (already verified in this experiment) is paired with the
# matching habitat-lab v0.3.3 tag; that pairing is a recorded local decision,
# not an upstream pin.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
ENV_DIR="$ROOT/official_r2r/official_env"
export MAMBA_ROOT_PREFIX="$ROOT/mamba"

if [ ! -x tools/bin/micromamba ]; then tar -xjf setup/micromamba.tar.bz2 -C tools bin/micromamba; fi

# Clone the already-verified habitat-sim 0.3.3 environment from the explicit
# spec `sim_setup_v1` produced. An explicit spec installs the exact same package
# URLs with no solver, and the packages are already in mamba/pkgs, so this is
# deterministic and does not re-hit a slow conda-forge mirror.
# `micromamba list --explicit` omits the @EXPLICIT marker, and micromamba 2.1.1
# segfaults on the file without it. Rebuild a conformant explicit spec.
mkdir -p official_r2r/setup
{ echo '@EXPLICIT'; grep '^https://' setup/sim_explicit.txt; } > official_r2r/setup/sim_explicit_conformant.txt
if [ ! -x "$ENV_DIR/bin/python" ]; then
  rm -rf "$ENV_DIR"
  tools/bin/micromamba create -y -p "$ENV_DIR" --file official_r2r/setup/sim_explicit_conformant.txt
fi
PY="$ENV_DIR/bin/python"

"$PY" -m pip install --disable-pip-version-check --upgrade 'pip<25'
"$PY" -m pip install --disable-pip-version-check 'torch==2.6.0' 'torchvision==0.21.0' \
  --index-url https://download.pytorch.org/whl/cu124
"$PY" -m pip install --disable-pip-version-check \
  'transformers==4.51.0' 'diffusers==0.32.2' 'accelerate==1.4.0' 'huggingface-hub==0.33.4' \
  'numpy==1.26.4' 'pillow==10.4.0' 'opencv-python-headless==4.10.0.84' 'scipy==1.13.1' \
  'einops==0.8.1' 'ftfy==6.3.1' 'imageio==2.37.0' 'imageio-ffmpeg==0.6.0' \
  'matplotlib==3.9.4' 'timm==1.0.15' 'pydantic>=2.11,<2.12' 'numpy-quaternion==2023.0.4' \
  'dtw==1.4.0' 'tqdm' 'gym==0.23.1'

# habitat-lab + habitat-baselines from the v0.3.3 source tree (matches habitat-sim
# 0.3.3). GitHub serves this host at ~25 KiB/s, so the tree is cloned on the
# workstation from the v0.3.3 tag and pushed here; .git/res/docs are stripped.
# The upstream commit is recorded in official_r2r/setup/habitat_lab_commit.txt.
if [ ! -d "$ROOT/official_r2r/src/habitat-lab/habitat-lab" ]; then
  echo "ERROR: habitat-lab source tree not staged at official_r2r/src/habitat-lab" >&2
  exit 4
fi
test -s official_r2r/setup/habitat_lab_commit.txt
"$PY" -m pip install --disable-pip-version-check -e "$ROOT/official_r2r/src/habitat-lab/habitat-lab"
"$PY" -m pip install --disable-pip-version-check -e "$ROOT/official_r2r/src/habitat-lab/habitat-baselines"

# depth_camera_filtering is a git dependency of requirements/habitat_requirements.txt
"$PY" -m pip install --disable-pip-version-check \
  'git+https://github.com/naokiyokoyama/depth_camera_filtering.git'

FA="$ROOT/setup/wheels/flash_attn-2.7.3+cu12torch2.6cxx11abiFALSE-cp39-cp39-linux_x86_64.whl"
if [ -f "$FA" ]; then
  "$PY" -m pip install --disable-pip-version-check --no-deps "$FA"
else
  echo "WARNING: cp39 FlashAttention wheel absent at $FA"
fi

"$PY" -m pip freeze > official_r2r/setup/official_env_pip_freeze.txt
"$PY" - <<'PY'
import json
info = {}
for m in ("torch", "transformers", "diffusers", "habitat_sim", "habitat", "habitat_baselines", "flash_attn"):
    try:
        mod = __import__(m)
        info[m] = getattr(mod, "__version__", "imported_no_version")
    except Exception as e:
        info[m] = "IMPORT_FAILED: %s: %s" % (type(e).__name__, e)
print("OFFICIAL_ENV_IMPORTS " + json.dumps(info))
PY
printf '%s\n' OFFICIAL_ENV_SETUP_COMPLETE
