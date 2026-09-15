#!/usr/bin/env bash
# Download the two pinned OmniVLA checkpoints on the remote execution host.
# Weights stay remote (prd.md "Out of scope"); identity is verified against the
# tracked CHECKPOINT_MANIFEST.tsv by remote_verify_checkpoints.py.
#
# A dedicated tiny conda env (omnivla_sun_dl) is used so that the 16 GB download
# can run while the main env (omnivla_sun) is still being built; installing into
# an env while one of its interpreters is running is avoided on purpose.
set -euo pipefail
REMOTE=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda
# Envs live inside the task workspace (prefix envs, not named envs) and are
# created from conda-forge with --override-channels: the shared account has not
# accepted the Anaconda defaults-channel Terms of Service and this task must not
# change shared account configuration (guard G4).
export CONDA_PKGS_DIRS=$REMOTE/conda_pkgs
source /home/ubuntu/miniconda3/etc/profile.d/conda.sh
DLENV=$REMOTE/envs/omnivla_sun_dl

if [ ! -x "$DLENV/bin/python" ]; then
  conda create -p "$DLENV" python=3.10 -y -c conda-forge --override-channels
fi
conda activate "$DLENV"
python -m pip install -q "huggingface_hub==0.29.1"
python -c "import huggingface_hub as h; print('huggingface_hub', h.__version__)"

export HF_HUB_DISABLE_TELEMETRY=1
# huggingface.co is not reachable from this host: DNS returns 50.23.209.199 /
# 2001::6ca0:adcf and every connection fails with [Errno 101] Network is
# unreachable (see env/DEVIATIONS.md, verbatim traceback in logs/download.log
# of the first attempt). The mirror serves the same pinned revision; identity is
# not taken on trust - every downloaded file is checked byte-for-byte against
# the SHA-256 values recorded from the official Hugging Face API in
# third_party/2026-08-18_omnivla_5182600/checkpoints/CHECKPOINT_MANIFEST.tsv.
export HF_ENDPOINT=${HF_ENDPOINT:-https://hf-mirror.com}
echo "[download] HF_ENDPOINT=$HF_ENDPOINT"
python - <<'PY'
import time
from huggingface_hub import snapshot_download
REMOTE = "/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda"
jobs = [
    ("NHirose/omnivla-original", "e36a84d4923c041149d441f93f3bdb7092bb5f07", f"{REMOTE}/checkpoints/omnivla-original"),
    ("NHirose/omnivla-edge",     "b1361b7e24f101edea795a98b00a826b61a97394", f"{REMOTE}/checkpoints/omnivla-edge"),
]
for repo, rev, dest in jobs:
    t0 = time.time()
    print(f"[download] {repo} @ {rev} -> {dest}", flush=True)
    p = snapshot_download(repo_id=repo, revision=rev, local_dir=dest, max_workers=4)
    print(f"[download] done in {time.time()-t0:.0f}s: {p}", flush=True)
PY
du -sh "$REMOTE/checkpoints"/* || true
echo "[remote_download] finished"
