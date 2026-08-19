#!/usr/bin/env bash
# run_original_probe.sh — guarded probe of the 8B `omnivla-original` model.
#
# Order: guards first, then download, then a single forward pass. The guards are
# the ones declared in decision_log.md BEFORE any run, and they are not to be
# relaxed to make the probe happen:
#   G1  > 60 GB free disk (the pinned revision is 14.90 GiB)
#   G2  >= 22 GB available memory (8B bf16 weights ~15 GB + activations)
#   G3  never float32 for this model
#   G4  wall-clock timeout on every model process; at most 2 attempts
#
# Exit codes: 0 probe ran; 3 stopped at a guard; 4 stopped because the required
# device patch does not exist yet.
set -eo pipefail

ROOT=/Users/sun/tongbu/study/phdproject/vla
TP="$ROOT/third_party/2026-08-18_omnivla_5182600"
EXP="$ROOT/.pipeline/experiments/2026-08-18_omnivla_offline_smoke"
PY=/opt/homebrew/Caskroom/miniforge/base/envs/omnivla/bin/python
REV=e36a84d4923c041149d441f93f3bdb7092bb5f07

echo "[probe] G1 disk"
free_gb=$(df -g / | tail -1 | awk '{print $4}')
echo "[probe]     free: ${free_gb} GB (need > 60)"
if [ "$free_gb" -le 60 ]; then
  echo "[probe] STOP at G1: insufficient disk"; exit 3
fi

echo "[probe] G2 memory"
avail=$("$PY" -c "import psutil;print(psutil.virtual_memory().available)")
avail_gb=$("$PY" -c "print(round($avail/1e9,2))")
echo "[probe]     available: ${avail_gb} GB (need >= 22)"
if [ "$("$PY" -c "print(1 if $avail >= 22e9 else 0)")" -eq 0 ]; then
  echo "[probe] STOP at G2: insufficient available memory for an 8B bf16 model."
  echo "[probe] Recorded outcome: probe SKIPPED, omnivla-original stays at 'imported'"
  echo "[probe] (manifest only; weights not downloaded because no probe follows)."
  exit 3
fi

echo "[probe] device patch check"
if ! ls "$EXP"/patches/[0-9][0-9][0-9][0-9]-original-*.patch >/dev/null 2>&1; then
  echo "[probe] STOP: inference/run_omnivla.py calls torch.cuda.set_device(device_id)"
  echo "[probe] at upstream line 502, which raises on a CPU/MPS host:"
  echo "[probe]     ValueError: Expected a cuda device, but got: cpu"
  echo "[probe] A patches/NNNN-original-*.patch guarding that call must be authored"
  echo "[probe] and reviewed before the probe runs. Not authored speculatively."
  exit 4
fi

echo "[probe] downloading NHirose/omnivla-original @ $REV"
"$EXP/scripts/portable_timeout.pl" 3600 "$PY" - "$TP" "$REV" <<'PY'
import sys
from huggingface_hub import snapshot_download
tp, rev = sys.argv[1], sys.argv[2]
snapshot_download("NHirose/omnivla-original", revision=rev,
                  local_dir=f"{tp}/checkpoints/omnivla-original")
PY

echo "[probe] verifying every file against CHECKPOINT_MANIFEST.tsv"
"$PY" "$EXP/scripts/verify_checkpoints.py" || { echo "[probe] STOP: hash mismatch"; exit 3; }

echo "[probe] attempt 1: MPS bf16"
( cd "$EXP/work/OmniVLA" && PYTORCH_ENABLE_MPS_FALLBACK=1 OMNIVLA_DEVICE=mps \
  "$EXP/scripts/portable_timeout.pl" 1800 "$PY" inference/run_omnivla.py ) && exit 0

echo "[probe] attempt 2: CPU bf16"
( cd "$EXP/work/OmniVLA" && OMNIVLA_DEVICE=cpu \
  "$EXP/scripts/portable_timeout.pl" 1800 "$PY" inference/run_omnivla.py ) && exit 0

echo "[probe] both attempts failed; see logs"
exit 1
