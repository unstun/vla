# Implementation plan (Opus executor; no git add/commit)

`ROOT=/Users/sun/tongbu/study/phdproject/vla`; `TP=$ROOT/third_party/2026-08-18_omnivla_5182600`;
`EXP0=$ROOT/.pipeline/experiments/2026-08-18_omnivla_offline_smoke`;
`EXP=$ROOT/.pipeline/experiments/2026-08-19_omnivla_original_cuda_gpu40901`;
`REMOTE=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda` on `gpu40901`.
Total budget ≈ 4 h (download ≤ 120 min, env ≤ 60 min, runs ≤ 45 min). Stop and report at budget.

## Step 0 — Pre-flight (10 min)
- [ ] Read prd/design of this task and of `08-18-omnivla-offline-smoke`; read `$EXP0/README.md`, `$EXP0/patches/README.md`, `$EXP0/scripts/run_edge.sh`.
- [ ] `ssh -o BatchMode=yes gpu40901 'hostname; nvidia-smi --query-gpu=memory.free --format=csv; ls -la /home/ubuntu; ls /home/ubuntu/sun 2>/dev/null; df -h /home; source /home/ubuntu/miniconda3/etc/profile.d/conda.sh && conda env list'` → `$EXP/env/remote_preflight.txt`. Do not proceed if free VRAM < 24,576 MiB (record and wait ≥ 5 min, max 3 tries).
- [ ] `mkdir -p $EXP/{env,patches,scripts,runs,verify}`; remote `mkdir -p $REMOTE/{pristine,work,checkpoints,env,verify,runs,logs,scripts}`.

## Step 1 — Sync up + remote manifest check (10 min)  [AC1]
- [ ] `rsync -az $TP/OmniVLA/ gpu40901:$REMOTE/pristine/OmniVLA/`; `rsync` `$TP/SOURCE_MANIFEST.sha256`, `$TP/checkpoints/CHECKPOINT_MANIFEST.tsv`, `$EXP0/patches/`, `$EXP/patches/`, `$EXP/scripts/`.
- [ ] Remote: `cd $REMOTE/pristine/OmniVLA && sha256sum -c ../SOURCE_MANIFEST.sha256 | grep -vc ': OK$'` → must be 0 → `$EXP/verify/remote_source_manifest.txt`.

## Step 2 — Environment (≤ 60 min, background + poll)  [AC3]
- [ ] Write local `$EXP/scripts/remote_env.sh` (conda source, `conda create -n omnivla_sun python=3.10 -y`, official pip lines, `pip install -e $REMOTE/work/OmniVLA` after building the work copy with patches 0001–0005 applied, flash-attn strategy (a)/(b)/(c) from design.md, `pip freeze`, `python -c "import torch;print(torch.__version__, torch.version.cuda, torch.cuda.is_available(), torch.cuda.get_device_name(0))"`, `nvidia-smi -q | head -40`). Sync, run via `nohup`, poll ≤ every 60 s.
- [ ] `$EXP/scripts/remote_make_workcopy.sh` (rm -rf work/OmniVLA; cp -a pristine; apply patches in lexical order; print `patch` results) — run before pip install -e and after new patches are added.
- [ ] Sync `env/` down; write `$EXP/env/DEVIATIONS.md`.

## Step 3 — Checkpoints (≤ 120 min, background + poll)  [AC2]
- [ ] `$EXP/scripts/remote_download.sh`: python (env) `snapshot_download` for `NHirose/omnivla-original` rev `e36a84d4923c041149d441f93f3bdb7092bb5f07` → `$REMOTE/checkpoints/omnivla-original`, and `NHirose/omnivla-edge` rev `b1361b7e24f101edea795a98b00a826b61a97394` → `…/omnivla-edge`; then build a sha256 checkfile from CHECKPOINT_MANIFEST.tsv (lfs rows) and `sha256sum -c` → `$REMOTE/verify/checkpoints.txt`. Non-LFS small files: compare size + git-blob sha where the manifest kind says so (reuse `$EXP0/scripts/verify_checkpoints.py` logic; copy it to remote).
- [ ] CLIP: copy local `$TP/checkpoints/clip/ViT-B-32.pt` up via rsync (354 MB) or let clip download into `$REMOTE/checkpoints/clip` with `OMNIVLA_CLIP_ROOT`; verify sha256 `40d36571…`.
- [ ] Sync `verify/` down.

## Step 4 — Patches + decision log BEFORE running (20 min)  [AC8 gate]
- [ ] Read `work/OmniVLA/inference/run_omnivla.py` (InferenceConfig ~L482: `vla_path`, `resume_step` 120000; modality block ~L560; `save_dir`; velocity clip ~L211). Write patches 0101–0103 locally against the pristine tree (`diff -u`), sync, rebuild work copy, `python -m py_compile`.
- [ ] Write `$EXP/decision_log.md` from the template with pre-run sections (parent = previous task + commit `f615d28`; expected: exit 0, finite (8,4), figure, peak VRAM ≤ 22 GiB; failure: OOM/exception/timeout/guard abort; stop: budgets). Do not edit later.

## Step 5 — Runs (≤ 45 min)  [AC4–AC7]
- [ ] `$EXP/scripts/remote_run_model.sh` per design (G1 sampler → timeout/nice/time -v → nvidia-smi peak sampler → meta.json → copy artifacts). Each run one `nohup` job; poll; sync `runs/` down after each.
- [ ] Order: (1) original default; (2) alternate prompt; (3) goal-image modality; (4) pose modality; (5) edge default on CUDA (`OMNIVLA_CLIP_ROOT` set). If (1) fails: read the traceback, fix by patch (max 3 attempts total, each attempt = new run dir with `_failed_<reason>` suffix), never relax G1/G2.
- [ ] Analysis locally: `check_outputs.py` on each; `compare_runs.py` table; `compare_reference_figure.py` (pristine `inference/1_ex.jpg` vs run figure); edge CUDA vs local CPU max|Δ|.

## Step 6 — Close-out (15 min)  [AC8–AC9]
- [ ] Remote hygiene: `pgrep -u ubuntu -af "run_omnivla|snapshot_download|nvidia-smi --query" ` must be empty except our finished jobs; `du -sh $REMOTE/*` recorded; nothing outside `/home/ubuntu/sun/`.
- [ ] Append Results to the decision log; write `$EXP/README.md` (what ran, host, env, guards evidence, runs table, VRAM/RSS/timings, reference-figure numbers, edge CPU-vs-CUDA delta, deviations, claim boundary, remote paths of weights, next gate); add one bullet to `.pipeline/experiments/README.md`.
- [ ] Update `bigmemory/热区/{状态简报,近期改动,未关闭决策}.md` (Chinese, concise, within budgets) and add one cold-zone 改动记录 (English) for this run; journal entry appended in the existing style.
- [ ] `git status --porcelain` → only `$EXP`, `.pipeline/experiments/README.md`, bigmemory/journal files, this task dir, and the pre-existing ` M AGENTS.md`.
- [ ] Final report: per-AC status with paths; env vs official pins; flash-attn outcome and active attention path; runs table with peak VRAM; guard evidence summary (min free VRAM seen before each run); reference-figure numbers; edge CPU-vs-CUDA delta; deviations; verbatim failures; label per model; remote paths; `git status`.
