#!/usr/bin/env bash
# Resolve the import chain for the realworld agent. setup_remote.sh installed the
# model runtime pins but not InternNav's own core_requirements.txt; install only
# the modules the inference import path actually needs, never touching the pinned
# torch / transformers / diffusers / numpy versions.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PROTECTED='torch|torchvision|transformers|diffusers|numpy|flash-attn|flash_attn|pillow|opencv'
for i in $(seq 1 15); do
  ERR=$(venv/bin/python -c "
import sys
sys.path.insert(0,'work/InternNav'); sys.path.insert(0,'work/InternNav/src/diffusion-policy')
from internnav.agent.internvla_n1_agent_realworld import InternVLAN1AsyncAgent
from internnav.model.basemodel.internvla_n1.internvla_n1 import InternVLAN1ForCausalLM
# build_depthanythingv2 / build_navdp import these lazily during construction
import internnav.configs
import internnav.model.encoder
from internnav.model.encoder.depth_anything.depth_anything_v2.dpt import DepthAnythingV2
from internnav.model.utils.vln_utils import traj_to_actions
print('IMPORT_OK')
" 2>&1)
  if echo "$ERR" | grep -q IMPORT_OK; then echo "IMPORT_CHAIN_RESOLVED after $((i-1)) installs"; exit 0; fi
  MOD=$(echo "$ERR" | grep -oP "No module named '\K[^']+" | head -1)
  if [ -z "$MOD" ]; then echo "NON_IMPORT_ERROR"; echo "$ERR" | tail -25; exit 1; fi
  MOD="${MOD%%.*}"
  case "$MOD" in
    yaml) PKG=PyYAML ;; cv2) PKG=opencv-python-headless ;; PIL) PKG=pillow ;;
    sklearn) PKG=scikit-learn ;; skimage) PKG=scikit-image ;;
    google) PKG=protobuf ;; lmdb) PKG=lmdb ;; *) PKG="$MOD" ;;
  esac
  if echo "$PKG" | grep -qiE "^($PROTECTED)$"; then
    echo "REFUSING to reinstall pinned package: $PKG"; echo "$ERR" | tail -20; exit 1
  fi
  echo ">>> installing missing module '$MOD' as package '$PKG'"
  venv/bin/python -m pip install --disable-pip-version-check "$PKG" 2>&1 | tail -2
done
echo "GAVE_UP_AFTER_15"; exit 1
