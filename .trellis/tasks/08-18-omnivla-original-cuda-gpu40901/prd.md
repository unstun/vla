# PRD: OmniVLA-original official CUDA reproduction on gpu40901

Follows task `08-18-omnivla-offline-smoke` (read its `prd.md`, `design.md`, and
`.pipeline/experiments/2026-08-18_omnivla_offline_smoke/README.md` first — that
task delivered the pinned snapshot, checkpoint manifests, patch mechanism, and
the CPU `reproduced` result for OmniVLA-edge). Dr Sun authorized this remote run
on 2026-08-18 ("do it") after reviewing the capacity snapshot below.

## 1. Host facts (read-only snapshot, 2026-08-18)

| Item | Value |
|---|---|
| SSH alias | `gpu40901` (from `~/.ssh/config`: ubuntu@177.3.34.125:60024, key auth, `ServerAliveInterval 30`) |
| GPU | RTX 4090 49,140 MiB; at snapshot: used 16,298 MiB, **free 32,202 MiB**, util 55 % |
| Other occupants | `/home/ubuntu/miniconda3/envs/isaaclab/bin/python` (active training, 10.7 GB); CARLA under `/home/ubuntu/ljh/` (5.3 GB) — **shared machine, do not disturb either** |
| Host | 188 GB RAM (173 GB available), 24 CPUs (load ≈ 15), 1.5 TB free, Linux 6.8, driver 580.82.09 / CUDA 13.0 |
| Tools | git yes; git-lfs not on PATH; miniconda3 at `/home/ubuntu/miniconda3` (not on non-interactive PATH); user dirs live under `/home/ubuntu/<name>/` |

## 2. Goal

Execute the original upstream command `python inference/run_omnivla.py` with the
pinned source (`5182600`) and pinned checkpoint `NHirose/omnivla-original` @
`e36a84d4923c041149d441f93f3bdb7092bb5f07` in the official CUDA stack
(SETUP.md: py3.10, torch 2.2.0, `pip install -e .`, flash-attn 2.5.5) on
gpu40901, produce the declared artifacts, sync them back, and state the label:
`reproduced` for OmniVLA-original **only** if a forward pass completes with the
declared artifacts; otherwise record the failure verbatim.

Secondary (cheap, same env): run `run_omnivla_edge.py` default on CUDA and
compare its raw 8×4 trajectory to the local CPU result, closing the open
CPU-vs-CUDA numeric caveat of the previous task.

## 3. Guards (promised to Dr Sun — non-negotiable)

G1 Pre-load VRAM check: sample `nvidia-smi --query-gpu=memory.free` every 5 s
for 60 s immediately before each model process; require min ≥ 24,576 MiB;
otherwise abort, record, and retry at most twice with ≥ 5 min spacing.
G2 Cap our process: `torch.cuda.set_per_process_memory_fraction(0.45)` (≈ 22 GiB)
set right after device selection (patch, default-on only when CUDA present).
G3 One short-lived process per run: load → one forward pass → exit; wall
`timeout 1800`; `nice -n 10`; no daemon, no loops, no concurrent model runs.
G4 Be gentle with shared CPU/disk: `MAX_JOBS=4` for any compile; prefer prebuilt
wheels; download once; never touch `isaaclab`, `ljh/`, base conda, or anything
outside `/home/ubuntu/sun/`.

## 4. In scope

1. Remote workspace `/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda/`
   (create `/home/ubuntu/sun` if absent): work copy = pristine snapshot + patches,
   remote manifest check, conda env `omnivla_sun` in the existing miniconda3
   (or micromamba under `/home/ubuntu/sun/` if env creation there is refused).
2. Checkpoint download at the pinned revision with `huggingface_hub`
   (`snapshot_download(revision=…)`), SHA-256 verified against the tracked
   `CHECKPOINT_MANIFEST.tsv`; edge checkpoint too (434 MB) for the secondary run.
3. Patch series `01xx` for `inference/run_omnivla.py` mirroring the edge series:
   JSON dump of raw/metric trajectory + `(v, ω)` + timings + peak VRAM; env-var
   prompt/modality switches (defaults == upstream literals; README says the
   modality settings are "around line 560"); `save_dir` → run dir; G2 cap.
   Reuse 0001 (pyproject comma) and 0005 (CLIP root) as they are; 0002–0004 are
   edge-only but harmless.
4. Runs: original default (language modality) → then alternate prompt,
   goal-image, pose (one process each, G1 before each); edge default on CUDA.
   Reference-figure comparison against pristine `inference/1_ex.jpg`.
5. Sync back to `.pipeline/experiments/2026-08-19_omnivla_original_cuda_gpu40901/`:
   decision log (pre-run sections written **before** the first remote model
   process), `env/` (pip freeze, nvidia-smi, driver, host), `patches/`,
   `scripts/` (sync-up, remote-run, sync-down, guards), `runs/*` (logs, JSON,
   figures, meta with peak VRAM/RSS/wall), README with claim boundary.

## 5. Out of scope

Training, benchmark, datasets, Lite3, ROS, any change to other users' files or
envs, storing weights locally (remote-only bytes; record path + verification),
`git commit`.

## 6. Acceptance criteria

- AC1 Remote work copy manifest-verified (`sha256sum -c` of the tracked
  SOURCE_MANIFEST on the remote pristine copy → 0 mismatches) before patching.
- AC2 `omnivla-original` files all verified against the manifest on the remote
  (26/26); edge 1/1. Verification log synced back.
- AC3 Environment records synced: pip freeze, `nvidia-smi`, driver/CUDA, torch
  CUDA build, flash-attn status, DEVIATIONS.md (official pin vs installed, error
  excerpts).
- AC4 Guard evidence per run: the 60 s VRAM samples, min free, cap set, `nice`,
  timeout — all in `meta.json`/`stdout.log`.
- AC5 Original default run: exit 0; raw trajectory finite, shape (8,4); metric
  trajectory; `(v, ω)` finite within the script's clip bounds; figure produced;
  peak VRAM (`torch.cuda.max_memory_allocated`) and nvidia-smi peak recorded.
- AC6 Sweep ≥ 3 configurations + comparison table; reference-figure pixel
  comparison numbers.
- AC7 Edge-on-CUDA default vs local CPU run: max|Δ| of raw 8×4 reported.
- AC8 Decision log pre-run/results discipline; README claim boundary; nothing
  labeled beyond what ran; no bytes > 2 MB added locally except figures.
- AC9 Remote hygiene: no leftover processes (`pgrep -u ubuntu -f omnivla` empty),
  everything under `/home/ubuntu/sun/…`; local `git status` limited to the
  new experiment dir, this task dir, and the untouched pre-existing `AGENTS.md`.
