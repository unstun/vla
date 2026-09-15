# Decision log

## 2026-08-19 — select edge-only Orin smoke

Live preflight found Jetson AGX Orin 64GB, JetPack 5.1.2 / L4T R35.4.1,
CUDA-enabled Jetson PyTorch, approximately 58 GiB available memory, and only
approximately 13 GB free on the system volume. Therefore this run transfers the
approximately 414 MB OmniVLA-edge checkpoint and approximately 338 MB CLIP
checkpoint, not the approximately 15 GB OmniVLA-original checkpoint.

## 2026-08-19 — preserve the JetPack framework stack

The installed Jetson-specific PyTorch and torchvision builds are reused. The
upstream project is not installed because its generic dependency pins could
replace those builds. Missing lightweight dependencies are supplied from a
local, hash-verified wheelhouse.

## 2026-08-19 — use a real archived Lite3 frame

The input is the real 1280x720 Lite3 front-camera JPEG already captured and
validated by the parent receive-only task. This gives a real robot-view input
without opening a live camera stream or adding any control path in the present
task.

## 2026-08-19 — protect prior vehicle work and reclaim only safe storage

The Jetson home contains approximately 183 GB of pre-existing vehicle,
navigation, SLAM, ROS, bag, PCD, and experiment material. Those paths are
protected and were not modified. Cleanup was limited to reviewed regenerable
caches and disabled historical Snap revisions, increasing root-volume free
space from approximately 13 GiB to 17 GiB. The approximately 46 GB desktop
trash was intentionally retained because it contains vehicle-related archives
and experiment files and did not have separate permanent-deletion approval.

All VLA execution files must remain under `/home/nvidia/sun/`; the exact rules
are recorded in `DEVICE_USAGE_POLICY.md` and copied to that isolated remote
namespace before deployment.

## 2026-08-19 — use a task-local dependency directory

The first preparation attempt stopped before source patching or model loading
because this Ubuntu installation does not provide `ensurepip` for `venv`.
Rather than install or alter a system package, lightweight wheels are installed
with `pip --target` into the task-owned `python_deps/` directory and exposed
only through the run's `PYTHONPATH`. Jetson PyTorch and torchvision continue to
load from their pre-existing user site.

## 2026-08-19 — use built-in wall timing

The first run invocation stopped with exit 127 before Python or the model
started because `/usr/bin/time` is absent. No package is installed to add it.
The retained retry uses nanosecond wall-clock timestamps, the runner's own
forward timer, and `tegrastats`; the failed pre-execution directory remains as
failure evidence and is not counted as an accepted forward.

## 2026-08-19 — correct evidence-only self matches

Post-run review found that the first retained-artifact manifest included its
own file and that a broad `pgrep` expression could match the audit shell's
command line. Model output, input hashes, and execution were unaffected. The
manifest is regenerated while excluding itself, and task-process checks now
inspect exact `python3` command lines plus the exact `tegrastats` process name.
No second model forward is run for this evidence-only correction.

## 2026-08-19 — permanently empty desktop trash after explicit approval

Dr Sun subsequently gave separate approval to clear the desktop trash. The
1,827 entries under `/home/nvidia/.local/share/Trash/files` and their matching
metadata under `/home/nvidia/.local/share/Trash/info` were permanently deleted;
both directory roots were retained and verified empty. This reclaimed
approximately 46 GB, changing root-volume availability from 16 GB (93% used)
to 62 GB (73% used). Representative protected vehicle workspaces and the VLA
execution directory remained present, the 125-entry VLA input manifest passed,
and Lite3 SSH remained reachable.
