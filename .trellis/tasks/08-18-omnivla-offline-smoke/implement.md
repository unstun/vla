# Implementation plan: OmniVLA offline reproduction

Executor: Opus sub-agent (`trellis-implement` role). No `git commit`, no `git add`.
Work only under the task-owned paths listed in design.md §1 plus one `.gitignore`
block and `.pipeline/experiments/README.md` (one bullet). Report verbatim errors.

Conventions: `ROOT=/Users/sun/tongbu/study/phdproject/vla`;
`TP=$ROOT/third_party/2026-08-18_omnivla_5182600`;
`EXP=$ROOT/.pipeline/experiments/2026-08-18_omnivla_offline_smoke`;
scratch = the session scratchpad dir (never `/tmp` for durable files).
Prefix every shell block you run with `set -euo pipefail` semantics in mind; use
`timeout` on any model process; append `2>&1 | tee` logs into `$EXP`.

## Step 0 — Pre-flight (5 min)  [gate: read before writing]

- [ ] Read `AGENTS.md`, this task's `prd.md`, `design.md`,
      `.trellis/spec/backend/quality-guidelines.md`,
      `.pipeline/experiments/README.md`, `.pipeline/templates/experiment_decision_log.md`.
- [ ] `git status --porcelain` → confirm the only pre-existing change is ` M AGENTS.md`;
      never touch it. Record `git rev-parse HEAD` (parent commit for the log).
- [ ] `df -h /`, `sysctl -n machdep.cpu.brand_string`, `sysctl -n hw.memsize`,
      `sw_vers`, `python3 -V`, `conda --version` → `$EXP/env/hardware.txt`.
- [ ] Create `$EXP/{env,patches,scripts,runs}` and `$TP/checkpoints`.

## Step 1 — Pinned source import (10 min)  [rollback point R1]

- [ ] In scratch: `git clone https://github.com/NHirose/OmniVLA.git`;
      `git checkout 5182600cb4a9ee07684e17cdd2a6cbafc56b8a68`;
      verify `git rev-parse HEAD` == that SHA and `git status --short` is empty;
      record `git rev-parse HEAD^{tree}` and `git log -1 --format='%H %ad %s' --date=iso`.
- [ ] `mkdir -p $TP/OmniVLA && git archive HEAD | tar -x -C $TP/OmniVLA`
      (no `.git`). Confirm `LICENSE` is MIT and `SETUP.md`, `inference/run_omnivla.py`,
      `inference/run_omnivla_edge.py`, `inference/current_img.jpg`, `inference/goal_img.jpg` exist.
- [ ] `cd $TP/OmniVLA && find . -type f | sort | xargs shasum -a 256 > ../SOURCE_MANIFEST.sha256`
      then `shasum -a 256 -c ../SOURCE_MANIFEST.sha256 | grep -v ': OK$'` must print nothing.
- [ ] Write `$TP/PROVENANCE.md` (URL, commit, tree hash, commit date, license,
      import date 2026-08-18, method = git archive snapshot, file count, manifest path,
      note that survey evidence lives in `.pipeline/survey/2026-08-16_…`).
- [ ] Validate: AC1.

## Step 2 — Checkpoint provenance + edge download (10–20 min)  [R2]

- [ ] Query HF API for both repos at the pinned revisions and write
      `$TP/checkpoints/CHECKPOINT_MANIFEST.tsv` (repo, revision, file, size,
      sha256 = LFS oid or blob sha for non-LFS, source=`hf-api`, verified=`no`):
      `https://huggingface.co/api/models/NHirose/omnivla-edge/revision/b1361b7e24f101edea795a98b00a826b61a97394?blobs=true`
      and `…/omnivla-original/revision/e36a84d4923c041149d441f93f3bdb7092bb5f07?blobs=true`.
      (Fields: `siblings[].rfilename`, `.size`, `.lfs.sha256` when present.)
- [ ] Download edge only: in the conda env of Step 3 or via `python3 -m pip install --user huggingface_hub`
      in scratch venv — prefer `huggingface_hub.snapshot_download("NHirose/omnivla-edge",
      revision="b1361b7e…", local_dir="$TP/checkpoints/omnivla-edge")`. Fallback:
      `git lfs install && git clone … && git checkout b1361b7e…`, then remove `.git`.
- [ ] `shasum -a 256 $TP/checkpoints/omnivla-edge/omnivla-edge.pth` must equal the
      manifest value; flip `verified=yes` for that row; note local path + `du -sh`.
- [ ] Add the dated `.gitignore` block from design.md §1 (three paths + comment).
      `git status --porcelain` must NOT list any file under the ignored dirs.
- [ ] Write `$TP/checkpoints/README.md` (commands, revisions, license MIT, size, regeneration).
- [ ] Validate: AC2, AC3 (manifest part).

## Step 3 — Environment (≤ 60 min)  [R3]

- [ ] `bash $EXP/scripts/make_workcopy.sh` (write it first: rm -rf work/OmniVLA;
      cp -R pristine → work; apply every `patches/*.patch` in order; print result).
      Initially there are no patches.
- [ ] `conda create -n omnivla python=3.10 -y`
- [ ] `conda run -n omnivla pip install numpy==1.26.4 torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0`
      (`| tee -a $EXP/env/install_log.txt`). If the exact torch 2.2.0 arm64 wheel is
      unavailable for py3.10, record the pip error verbatim and STOP to report —
      do not silently pick another torch.
- [ ] `conda run -n omnivla pip install -e $EXP/work/OmniVLA 2>&1 | tee -a $EXP/env/install_log.txt`
      (`timeout 2400`). On failure: retry `--no-deps`, then install only what the
      inference scripts import (iterate on `ImportError`, max 8 iterations). Skip
      `flash-attn` (CUDA-only) and record it. Every substitution → `DEVIATIONS.md`.
- [ ] `conda run -n omnivla python -c "import torch;print(torch.__version__, torch.backends.mps.is_available())"`
      `conda run -n omnivla pip freeze > $EXP/env/pip_freeze.txt`;
      `conda env export -n omnivla > $EXP/env/conda_env.yml`.
- [ ] Validate: AC4 (files exist; DEVIATIONS.md lists flash-attn at minimum).

## Step 4 — Decision log BEFORE running (5 min)  [gate]

- [ ] Copy `.pipeline/templates/experiment_decision_log.md` →
      `$EXP/decision_log.md`; fill Parent (pinned commit, HF revisions, local repo
      HEAD), Evidence/Motivation (survey §7), Exact Scope (edge run + sweep + optional
      probe), Expected/Failure/Stop signals (finite 8×4, image produced, exit 0 vs
      NaN/exception/timeout; stop at time boxes), Execution (commands, env,
      `$EXP/runs`), Claim Boundary (design.md §7). Leave Results empty.

## Step 5 — Edge inference, default modality (≤ 30 min/attempt, max 3 attempts)  [R4]

- [ ] Read `inference/run_omnivla_edge.py` + `model_omnivla_edge.py` in the work
      copy: how `InferenceConfig` locates the checkpoint, how sample images are
      referenced (cwd-relative?), where `1_ex_omnivla_edge.jpg` is written, what the
      "line ~425" modality switch is, and what the `__main__` block computes
      (raw waypoints, metric scaling, `(v, ω)`).
- [ ] Write patches (design.md §3) against the pristine tree with
      `diff -u` and apply via `make_workcopy.sh`; write `patches/README.md`
      (one line per patch: purpose, upstream lines touched, why unavoidable).
- [ ] Write `scripts/run_edge.sh`: creates `RUN=$EXP/runs/$(date -u +%Y%m%dT%H%M%SZ)_edge_<tag>`,
      exports `OMNIVLA_RUN_DIR=$RUN`, runs
      `timeout 1800 /usr/bin/time -l conda run -n omnivla python inference/run_omnivla_edge.py`
      from the directory the script expects, tees stdout/stderr, copies the generated
      image + JSON dumps into `$RUN`, writes `meta.json` (commit, HF revision, patches
      applied, device, dtype, wall time, peak RSS from `time -l`, torch/python versions).
- [ ] Run once (default language prompt). If it fails: fix by patch/deviation, note
      the attempt in `stderr.log`/DEVIATIONS.md, rerun (max 3 attempts total).
- [ ] Validate AC5 with `scripts/check_outputs.py` (finite, shape (8,4),
      `0≤v≤0.5`, `-1≤ω≤1`, image exists > 10 KB).

## Step 6 — Sensitivity sweep (≤ 30 min)

- [ ] Parameterise prompt/modality through env vars or a config patch (keep it in
      the same patch series). Run: (a) alternate prompt e.g. "turn left and go to the
      door" (or any semantically different instruction), (b) goal-image modality,
      (c) pose modality if available. One `runs/` dir each.
- [ ] `scripts/compare_runs.py` → markdown table (run, modality, prompt, finite,
      shape, max|Δ| raw traj vs default, v, ω) into `$EXP/README.md`.
      Report the observation neutrally (issue #28 context); no pass/fail.
- [ ] Validate AC6.

## Step 7 — Optional: original (8B) probe (≤ 60 min total incl. download decision)  [R5]

- [ ] Only if Steps 1–6 are complete and `df` shows > 60 GB free. Download
      `omnivla-original` at revision `e36a84d…` with `snapshot_download` into
      `$TP/checkpoints/omnivla-original`; verify every sha256 against the manifest
      (mark `verified=yes`). If download would exceed the time box, stop and record.
- [ ] Guard: `python -c "import psutil;print(psutil.virtual_memory().available)"` ≥ 22e9,
      else record and skip. Patch (0004) device + `attn_implementation`; attempt 1:
      MPS bf16 with `PYTORCH_ENABLE_MPS_FALLBACK=1`; attempt 2: CPU bf16. Each
      `timeout 1800`; never fp32; save the same artifact set under `runs/…_original_probe`.
- [ ] Record the outcome (success with artifacts, or the exact failure) in the
      decision log; label accordingly (design.md §7).

## Step 8 — Close-out (15 min)  [gate before report]

- [ ] Re-verify pristine tree: `shasum -a 256 -c $TP/SOURCE_MANIFEST.sha256 | grep -v ': OK$'` → empty.
- [ ] Append Results to `decision_log.md` (do not edit pre-run sections).
- [ ] Write `$EXP/README.md`: what ran, evidence paths, deviations, patches, sweep
      table, resource numbers, claim boundary, blocked items (GPU), next gate.
- [ ] Replace the placeholder sentence in `.pipeline/experiments/README.md` with one
      bullet linking `$EXP/README.md` (keep the pre-run rule paragraph).
- [ ] `git status --porcelain` → only: `.gitignore`, `third_party/…`, `.pipeline/experiments/…`,
      the task dir, and the pre-existing ` M AGENTS.md`. Nothing under ignored dirs.
- [ ] Final report to the primary AI: per-AC status (met / not met + why),
      exact artifact paths, every deviation, verbatim errors, timings, and the
      strongest justified label per model. Do not claim `reproduced` for anything
      that did not complete a forward pass and produce the declared artifacts.

## Rollback points

R1 remove `$TP`; R2 remove `$TP/checkpoints` + `.gitignore` block; R3
`conda env remove -n omnivla`, remove `$EXP/env`; R4/R5 remove the failed
`runs/*` dir only (keep failed logs if they carry evidence — rename `_failed`).
