#!/usr/bin/env bash
set -euo pipefail

REMOTE_ROOT="${OMNIVLA_REMOTE_ROOT:-/home/nvidia/sun/vla_exec/2026-08-19_omnivla_edge_orin64}"
PRISTINE="$REMOTE_ROOT/pristine/OmniVLA"
WORK="$REMOTE_ROOT/work/OmniVLA"
PY_DEPS="$REMOTE_ROOT/python_deps"
PREP_LOG="$REMOTE_ROOT/runs/prepare"

mkdir -p "$PREP_LOG"

required=(
  "$PRISTINE/inference/run_omnivla_edge.py"
  "$REMOTE_ROOT/checkpoints/omnivla-edge/omnivla-edge.pth"
  "$REMOTE_ROOT/checkpoints/clip/ViT-B-32.pt"
  "$REMOTE_ROOT/inputs/lite3_real_frame.jpg"
  "$REMOTE_ROOT/manifests/input_manifest.sha256"
)
for path in "${required[@]}"; do
  if [[ ! -f "$path" ]]; then
    echo "missing required input: $path" >&2
    exit 20
  fi
done

(
  cd "$REMOTE_ROOT"
  sha256sum --check manifests/input_manifest.sha256
) | tee "$PREP_LOG/input_manifest_check.log"

if [[ -e "$WORK" ]]; then
  echo "refusing to overwrite existing work copy: $WORK" >&2
  exit 21
fi

python3 - <<'PY' | tee "$PREP_LOG/jetpack_python_before_install.log"
import json
import platform
import torch
import torchvision

print(json.dumps({
    "python": platform.python_version(),
    "torch": torch.__version__,
    "torchvision": torchvision.__version__,
    "cuda_available": torch.cuda.is_available(),
    "cuda_device_count": torch.cuda.device_count(),
    "cuda_device_0": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
}, indent=2))
if not torch.cuda.is_available():
    raise SystemExit("CUDA unavailable in task environment")
PY

python3 -m pip install \
  --no-index \
  --no-cache-dir \
  --find-links "$REMOTE_ROOT/wheelhouse" \
  --no-deps \
  --target "$PY_DEPS" \
  utm==0.8.1 \
  openai-clip==1.0.1 \
  efficientnet-pytorch==0.7.1 \
  ftfy==6.1.1 \
  regex==2024.11.6 \
  | tee "$PREP_LOG/pip_install.log"

PYTHONPATH="$PY_DEPS${PYTHONPATH:+:$PYTHONPATH}" python3 - <<'PY' | tee "$PREP_LOG/import_smoke.log"
import json
import clip
import efficientnet_pytorch
import ftfy
import regex
import torch
import torchvision
import utm

print(json.dumps({
    "torch": torch.__version__,
    "torchvision": torchvision.__version__,
    "clip_module": clip.__file__,
    "efficientnet_pytorch": getattr(efficientnet_pytorch, "__version__", "unknown"),
    "ftfy": ftfy.__version__,
    "regex": regex.__version__,
    "utm": getattr(utm, "__version__", "unknown"),
    "cuda_available": torch.cuda.is_available(),
    "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
}, indent=2))
PY

mkdir -p "$(dirname "$WORK")"
cp -a "$PRISTINE" "$WORK"
for patch_file in "$REMOTE_ROOT"/patches/*.patch; do
  echo "applying $(basename "$patch_file")"
  patch --batch --forward --directory "$WORK" -p1 < "$patch_file"
done | tee "$PREP_LOG/patch_apply.log"

mkdir -p "$WORK/omnivla-edge"
ln -s ../../../checkpoints/omnivla-edge/omnivla-edge.pth \
  "$WORK/omnivla-edge/omnivla-edge.pth"

(
  cd "$WORK"
  diff -ruN --exclude=current_img.jpg "$PRISTINE" "$WORK" || true
) > "$PREP_LOG/work_copy.diff"

PYTHONPATH="$PY_DEPS${PYTHONPATH:+:$PYTHONPATH}" python3 -m py_compile \
  "$WORK/inference/run_omnivla_edge.py" \
  "$WORK/inference/model_omnivla_edge.py" \
  "$WORK/inference/utils_policy.py"

df -h "$REMOTE_ROOT" | tee "$PREP_LOG/disk_after_prepare.log"
echo "prepare complete: $REMOTE_ROOT"
