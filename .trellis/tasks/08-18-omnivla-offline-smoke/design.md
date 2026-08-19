# Design: OmniVLA offline reproduction

## 1. Layout

```
third_party/2026-08-18_omnivla_5182600/
  PROVENANCE.md                 # URL, commit, tree hash, license, date, import method
  SOURCE_MANIFEST.sha256        # sha256 of every file in OmniVLA/ (tracked)
  OmniVLA/                      # pristine upstream tree @5182600, no .git (tracked, ~1 MB)
  checkpoints/
    CHECKPOINT_MANIFEST.tsv     # repo  revision  file  size  sha256  source(hf-api|local)  verified
    README.md                   # download commands, revisions, license, storage note
    omnivla-edge/               # IGNORED (path-specific rule)
    omnivla-original/           # IGNORED (path-specific rule)

.pipeline/experiments/2026-08-18_omnivla_offline_smoke/
  decision_log.md               # from template; pre-run first, results appended
  README.md                     # evidence summary + claim boundary (English)
  env/  install_log.txt  pip_freeze.txt  conda_env.yml  hardware.txt  DEVIATIONS.md
  patches/  README.md  0001-*.patch ...   # unified diffs vs pristine tree
  scripts/  make_workcopy.sh  run_edge.sh  run_original_probe.sh  dump_outputs.py
  runs/<UTC yyyymmddThhmmssZ>_<tag>/  stdout.log stderr.log meta.json *.jpg *.json
  work/                         # IGNORED: OmniVLA working copy = pristine + patches
```

`.gitignore` gains one dated block with exactly:
`/third_party/2026-08-18_omnivla_5182600/checkpoints/omnivla-edge/`,
`/third_party/2026-08-18_omnivla_5182600/checkpoints/omnivla-original/`,
`/.pipeline/experiments/2026-08-18_omnivla_offline_smoke/work/`, plus a comment
pointing at the tracked manifests. Nothing else is ignored.

## 2. Import method (pristine snapshot)

`git clone` into the scratchpad → `git checkout 5182600…` → verify
`git rev-parse HEAD` and `git status --short` empty → `git rev-parse HEAD^{tree}`
recorded → `git archive HEAD | tar -x -C third_party/…/OmniVLA` (no `.git`) →
`find … -type f | sort | xargs shasum -a 256 > SOURCE_MANIFEST.sha256`.
Snapshot rather than submodule: the evidence stays self-contained and local
patches remain visible in the parent `git diff`.

## 3. Working copy and patches

The upstream scripts write outputs (`1_ex*.jpg`) into their own tree and
`pip install -e .` writes `*.egg-info`; therefore all execution happens in
`work/OmniVLA/` = `cp -R` of the pristine tree + `git apply`/`patch -p1` of every
`patches/*.patch`. `make_workcopy.sh` recreates it idempotently. Patches are
produced with `diff -u pristine work` and are minimal. Anticipated (confirm
against the code, do not assume):

- 0001 device: guard `torch.cuda.set_device` / `torch.cuda.empty_cache`; select
  `mps` if available (edge) else `cpu`; keep CUDA behaviour unchanged when CUDA exists.
- 0002 dtype (edge, only if needed): bf16 EfficientNet/CLIP ops unsupported on
  MPS/CPU → fp32 for the edge model (434 MB, cheap).
- 0003 dump: write raw `8×4` trajectory, metric trajectory, `(v, ω)`, timings
  to JSON in an `OMNIVLA_RUN_DIR` directory. Prefer a wrapper module
  (`dump_outputs.py` importing the upstream functions) over patching; patch only
  if the `__main__` block cannot be reused.
- 0004 (original probe only): `attn_implementation` flash_attention_2 →
  `eager`/`sdpa`; device/dtype as above.

## 4. Environment

`conda create -n omnivla python=3.10 -y`; `pip install numpy==1.26.4 torch==2.2.0
torchvision==0.17.0 torchaudio==2.2.0` (macOS arm64 wheels); `pip install -e
work/OmniVLA` exactly as SETUP.md. Expected macOS failures: `flash-attn`
(CUDA-only — skip, record), possibly `tensorflow==2.15.0` /
`tensorflow_graphics` / `dlimp` (training-only deps). If the full editable
install fails, fall back to `pip install -e work/OmniVLA --no-deps` plus the
minimal runtime set discovered by running the inference script and resolving
`ImportError`s (bounded to what the two inference scripts import). Each
substitution → `DEVIATIONS.md` (package, official pin, what was installed, error
excerpt). Never install into `base` or any existing env.

## 5. Runs

Edge (required): cwd + relative paths exactly as the upstream script expects
(inspect `run_omnivla_edge.py` for how it locates `inference/*.jpg` and the
checkpoint path/`InferenceConfig`; point the checkpoint path at
`third_party/…/checkpoints/omnivla-edge` via a symlink or the config, recorded
in the patch). Wrap with `/usr/bin/time -l` and `timeout 1800`. Save
stdout/stderr, the generated image, JSON dumps, `meta.json` (git commit, HF
revision, host, device, dtype, wall time, peak RSS, python/torch versions).

Sweep: repeat with (a) an alternate language prompt, (b) goal-image modality,
(c) pose modality if selectable near README's "line 425"; each in its own
`runs/` dir; then a small table: run, modality, prompt, finite?, shape,
max|Δ| vs default, `(v, ω)`.

Original probe (optional): download `omnivla-original` at the pinned revision
with `huggingface_hub.snapshot_download(revision=…)`; verify sha256 against the
manifest; check `psutil.virtual_memory().available ≥ 22 GB`; attempt (1) MPS
bf16 (`PYTORCH_ENABLE_MPS_FALLBACK=1`), then (2) CPU bf16; each `timeout 1800`;
never fp32; at most two attempts; record outcome verbatim.

## 6. Verification

`shasum -a 256 -c SOURCE_MANIFEST.sha256` before and after all runs;
checkpoint sha256 vs HF LFS oid; JSON outputs checked with a tiny script
(finite, shape (8,4), `0 ≤ v ≤ 0.5`, `-1 ≤ ω ≤ 1`); `git status --porcelain`
limited to task-owned paths; `du -sh` of ignored dirs recorded in the README.

## 7. Claim boundary

edge: `reproduced` — original upstream command executed on macOS arm64
(CPU/MPS) with the recorded patches; not the official CUDA environment.
original: `imported` (pinned manifest) plus probe outcome; `reproduced` only if
the official script actually completed a forward pass, with the same caveat.
Nothing here is `integrated` or `validated`; no Lite3 statement is made.

## 8. Rollback

Every step is additive under task-owned paths; rollback = delete those paths
and revert the `.gitignore` block; the conda env is removed with
`conda env remove -n omnivla`. No shared state is modified.
