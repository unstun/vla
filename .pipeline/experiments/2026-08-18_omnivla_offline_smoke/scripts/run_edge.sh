#!/usr/bin/env bash
# run_edge.sh <tag>
#
# Runs the official upstream entry point `python inference/run_omnivla_edge.py`
# from the working copy and collects the evidence bundle for one run.
#
# Modality / prompt are passed through the environment (patch 0003); leaving all
# of them unset reproduces the upstream defaults (language only, "blue trash bin").
#   OMNIVLA_PROMPT, OMNIVLA_POSE_GOAL, OMNIVLA_SATELLITE,
#   OMNIVLA_IMAGE_GOAL, OMNIVLA_LAN_PROMPT
set -eo pipefail

ROOT=/Users/sun/tongbu/study/phdproject/vla
TP="$ROOT/third_party/2026-08-18_omnivla_5182600"
EXP="$ROOT/.pipeline/experiments/2026-08-18_omnivla_offline_smoke"
WORK="$EXP/work/OmniVLA"
PY=/opt/homebrew/Caskroom/miniforge/base/envs/omnivla/bin/python
TIMEOUT_S=${TIMEOUT_S:-1800}

tag="${1:-default}"
RUN="$EXP/runs/$(date -u +%Y%m%dT%H%M%SZ)_edge_${tag}"
mkdir -p "$RUN"
export OMNIVLA_RUN_DIR="$RUN"
# Keep the CLIP text encoder inside the project (patch 0005). The weights are
# already present and hash-checked by CLIP's own loader, so this performs no
# network access; unset, the upstream ~/.cache/clip default would be used.
export OMNIVLA_CLIP_ROOT="$TP/checkpoints/clip"

echo "[run_edge] tag=$tag"
echo "[run_edge] run dir: $RUN"
echo "[run_edge] clip root: $OMNIVLA_CLIP_ROOT"

start_epoch=$(date +%s)
set +e
( cd "$WORK" && "$EXP/scripts/portable_timeout.pl" "$TIMEOUT_S" \
    /usr/bin/time -l "$PY" inference/run_omnivla_edge.py ) \
    > "$RUN/stdout.log" 2> "$RUN/stderr.log"
rc=$?
set -e
end_epoch=$(date +%s)
wall=$(( end_epoch - start_epoch ))

# /usr/bin/time -l reports "maximum resident set size" in bytes on macOS
peak_rss=$(grep "maximum resident set size" "$RUN/stderr.log" | awk '{print $1}' | tail -1)
peak_rss=${peak_rss:-unknown}

"$PY" - "$RUN" "$rc" "$wall" "$peak_rss" "$tag" <<'PY'
import hashlib, json, os, platform, subprocess, sys, glob
run, rc, wall, peak_rss, tag = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
root = "/Users/sun/tongbu/study/phdproject/vla"
tp   = f"{root}/third_party/2026-08-18_omnivla_5182600"
exp  = f"{root}/.pipeline/experiments/2026-08-18_omnivla_offline_smoke"
import torch
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()
patches = sorted(glob.glob(f"{exp}/patches/[0-9][0-9][0-9][0-9]-*.patch"))
meta = {
    "tag": tag,
    "run_dir": run,
    "exit_code": rc,
    "wall_seconds": wall,
    "peak_rss_bytes": None if peak_rss == "unknown" else int(peak_rss),
    "peak_rss_mib": None if peak_rss == "unknown" else round(int(peak_rss) / 2**20, 1),
    "timeout_seconds": int(os.environ.get("TIMEOUT_S", "1800")),
    "entry_point": "python inference/run_omnivla_edge.py",
    "cwd": f"{exp}/work/OmniVLA",
    "upstream_repo": "https://github.com/NHirose/OmniVLA",
    "upstream_commit": "5182600cb4a9ee07684e17cdd2a6cbafc56b8a68",
    "upstream_tree": "c2cdba2b3ca036684007fe4ab1c12ada73623cc5",
    "checkpoint_repo": "NHirose/omnivla-edge",
    "checkpoint_revision": "b1361b7e24f101edea795a98b00a826b61a97394",
    "checkpoint_file": "omnivla-edge.pth",
    "checkpoint_sha256": sha(f"{tp}/checkpoints/omnivla-edge/omnivla-edge.pth"),
    "patches_applied": [{"file": os.path.basename(p), "sha256": sha(p)} for p in patches],
    "env_overrides": {k: v for k, v in os.environ.items() if k.startswith("OMNIVLA_")},
    "python": platform.python_version(),
    "torch": torch.__version__,
    "torch_cuda_available": torch.cuda.is_available(),
    "torch_mps_available": bool(torch.backends.mps.is_available()),
    "host": {"machine": platform.machine(), "platform": platform.platform(),
             "cpu": subprocess.run(["sysctl","-n","machdep.cpu.brand_string"],
                                   capture_output=True, text=True).stdout.strip()},
}
json.dump(meta, open(f"{run}/meta.json", "w"), indent=2)
print(f"[run_edge] exit={rc} wall={wall}s peak_rss={meta['peak_rss_mib']} MiB")
PY

ls -la "$RUN"
exit $rc
