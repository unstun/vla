# Design: remote official CUDA reproduction (gpu40901)

## Sync gate (AGENTS.md rule 7)
- Local source of truth: `third_party/2026-08-18_omnivla_5182600/OmniVLA/`
  (pristine, tracked, SOURCE_MANIFEST.sha256) + patches under
  `.pipeline/experiments/2026-08-18_omnivla_offline_smoke/patches/` (existing
  0001–0005) + this task's new patches under
  `.pipeline/experiments/2026-08-19_omnivla_original_cuda_gpu40901/patches/`.
- Sync up: `rsync -az` pristine tree, both patch dirs, SOURCE_MANIFEST,
  CHECKPOINT_MANIFEST.tsv, and this task's `scripts/` to
  `REMOTE=/home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda/`.
  Remote: `pristine/` (verify manifest) → `work/OmniVLA` = copy + `patch -p1`
  of every patch in order (0001…0005 then 01xx). Any remote-only edit must be
  turned into a patch file locally before it is used for a claimed run.
- Sync down: `rsync -az remote:$REMOTE/{runs,env,verify}/ local EXP/` after
  each phase; weights never come back.
- Claim boundary: `reproduced` (official CUDA stack, remote execution copy,
  patches listed) — never `integrated`/`validated`; no Lite3 statement.

## Remote layout
```
$REMOTE/pristine/OmniVLA  work/OmniVLA  checkpoints/{omnivla-original,omnivla-edge,clip}
$REMOTE/env  verify  runs/<UTC>_<tag>  logs (nohup outputs)
```
Conda: `source /home/ubuntu/miniconda3/etc/profile.d/conda.sh; conda create -n omnivla_sun python=3.10 -y`
(never `base`, never `isaaclab`). If miniconda3 refuses env creation (perms),
install micromamba into `/home/ubuntu/sun/micromamba` and record the deviation.

## Environment (official order, record deviations)
`pip install numpy==1.26.4 torch==2.2.0 torchvision==0.17.0 torchaudio==2.2.0`
(Linux PyPI wheels = cu121; the 580 driver runs them) → `pip install -e work/OmniVLA`
(needs patch 0001) → `pip install packaging ninja` → flash-attn 2.5.5: (a) prebuilt
wheel from https://github.com/Dao-AILab/flash-attention/releases/tag/v2.5.5
matching `cp310`, `torch2.2`, cu12x, cxx11abiFALSE; (b) else source build with
`MAX_JOBS=4 nice -n 10`, timebox 25 min; (c) else skip — the pinned `config.json`
sets no `_attn_implementation` (previous task's finding), so record whether the
model loads/forwards without it and which attention path was active
(`vla.config._attn_implementation`, and whether `flash_attn` imported).

## Long commands
Every remote command that may exceed a minute runs as
`ssh gpu40901 "cd $REMOTE && nohup nice -n 10 bash scripts/<step>.sh > logs/<step>.log 2>&1 &"`
then poll `tail -n 20 logs/<step>.log` (sleep ≥ 30 s between polls; do not
spin). Download: `snapshot_download("NHirose/omnivla-original", revision="e36a84d4…", local_dir=…)`
with `huggingface_hub==0.29.1` from the env; timebox 120 min; then `sha256sum -c`
against a checkfile generated from CHECKPOINT_MANIFEST.tsv.

## Patches (new, minimal, defaults == upstream)
- 0101-original-dump-and-run-dir: JSON sink (same schema as 0002 + `peak_vram_bytes`
  from `torch.cuda.max_memory_allocated()`, `attn_implementation`, dtype), `save_dir`
  from `OMNIVLA_RUN_DIR`, checkpoint path from `OMNIVLA_ORIGINAL_PATH` (default
  = upstream literal).
- 0102-original-env-modality-and-prompt: env-var switches for the block near
  line 560 (defaults = upstream literals; print the resolved values).
- 0103-original-cuda-memory-fraction: after `device_id` selection, if CUDA:
  `torch.cuda.set_per_process_memory_fraction(float(os.environ.get("OMNIVLA_CUDA_MEM_FRACTION", "0.45")))`.
  (Guard G2; document that upstream has no cap.)
- Reuse 0005 for CLIP root if `run_omnivla.py` calls `clip.load` (check; if not,
  note it does not apply).

## Run wrapper (remote `scripts/run_model.sh <script> <tag>`)
G1 sampler (60 s / 5 s, abort < 24576 MiB min) → `meta.json` pre-block →
`timeout 1800 nice -n 10 /usr/bin/time -v python inference/<script>` with cwd =
`work/OmniVLA`, env vars for run dir/modality/prompt/checkpoints → nvidia-smi
peak sampler in background (1 s) killed at exit → post-block (exit code, wall,
peak RSS, nvidia-smi peak) → copy figure + JSON into `runs/<UTC>_<tag>/`.

## Verification
`scripts/check_outputs.py` (reuse previous: finite, shape, clip bounds; original
clip bounds are `np.clip(v,0,0.5)`, `np.clip(ω,-1,1)` at run_omnivla.py:211-212 —
confirm and use the script's own constants); `compare_runs.py`;
`compare_reference_figure.py` against pristine `inference/1_ex.jpg`;
edge CUDA vs local CPU: max|Δ| of `waypoints_raw` vs
`.pipeline/experiments/2026-08-18_omnivla_offline_smoke/runs/20260819T061614Z_edge_default_lan_bluetrashbin/outputs.json`.

## Rollback
Remote: `rm -rf /home/ubuntu/sun/vla_exec/2026-08-19_omnivla_original_cuda` and
`conda env remove -n omnivla_sun` (only on Dr Sun's instruction — weights are
expensive; default is to leave them and record the path). Local: delete the new
experiment dir + task dir.
