# PRD: OmniVLA offline reproduction — pinned import + local inference smoke

Task: `08-18-omnivla-offline-smoke`
Stage: experiment + analysis (first reproduction step after the 2026-08-16 survey)
Owner: Dr Sun (decision), primary AI (plan + review), Opus sub-agent (execution)

## 1. Background

The 2026-08-16 survey (`.pipeline/survey/2026-08-16_lite3_vla_open_source_reproduction_survey.md`,
section 7) selected OmniVLA as the first low-cost VLA reproduction candidate for
Lite3 and defined a minimal offline reproduction plan. On 2026-08-18 Dr Sun
confirmed the choice: "We are preparing to reproduce OmniVLA." That closes the
survey gate; this task executes the minimal reproduction.

Upstream facts (verified 2026-08-18 against GitHub / Hugging Face APIs):

| Item | Value |
|---|---|
| Repository | https://github.com/NHirose/OmniVLA (MIT) |
| Pinned commit | `5182600cb4a9ee07684e17cdd2a6cbafc56b8a68` |
| Official entry points | `inference/run_omnivla.py` (8B, OpenVLA-OFT based), `inference/run_omnivla_edge.py` (EfficientNet-b0 + CLIP, light) |
| Sample inputs shipped in repo | `inference/current_img.jpg`, `inference/goal_img.jpg`; sample outputs `inference/1_ex.jpg`, `inference/1_ex_omnivla_edge.jpg` |
| Checkpoint `NHirose/omnivla-edge` | HF revision `b1361b7e24f101edea795a98b00a826b61a97394`, MIT, 1 file `omnivla-edge.pth` 434,276,465 B |
| Checkpoint `NHirose/omnivla-original` | HF revision `e36a84d4923c041149d441f93f3bdb7092bb5f07`, MIT, ~15.9 GB (4 safetensors shards + action/dist/proprio heads + lora_adapter) |
| Official env | conda py3.10, numpy 1.26.4, torch 2.2.0, torchvision 0.17.0, `pip install -e .`, flash-attn 2.5.5 (CUDA); ≥20 GB VRAM recommended for the 8B model |
| Known issues | #28 prompt may not change output; #27 trajectory scale; #26 velocity clipping order |

Execution host for this task: the local Mac (Apple M5, 32 GB unified memory,
~176 GB free disk, no CUDA). No GPU machine is configured in this repository.

## 2. Goal

Move OmniVLA from `surveyed` to:

- `imported`: pinned source snapshot + pinned checkpoint provenance inside this
  repository;
- `reproduced` (with an explicit non-official-environment caveat) for
  **OmniVLA-edge**: the original upstream inference command ran locally with
  recorded evidence;
- a bounded, honest feasibility record for **OmniVLA-original** on this Mac
  (download + integrity manifest required; a time-boxed load/forward probe is
  optional and its failure is acceptable evidence).

The official CUDA-stack reproduction of the 8B model is explicitly **not**
achievable in this task and stays blocked until Dr Sun designates a GPU host.

## 3. In scope

1. Pinned import of the upstream tree at `5182600` as a tracked, byte-identical
   snapshot with provenance and a SHA-256 manifest.
2. Pinned checkpoint acquisition: `omnivla-edge` (required download);
   `omnivla-original` (SHA-256 manifest from the HF API is required; download is
   required only if the optional probe is attempted and disk stays > 60 GB free).
3. An isolated conda environment `omnivla` built from the official SETUP.md,
   adapted to macOS arm64 only where unavoidable, with every deviation recorded.
4. Running the official `inference/run_omnivla_edge.py` on the shipped sample
   inputs (default language-prompt modality) and a small goal-modality /
   prompt-sensitivity sweep, saving raw numeric outputs.
5. Optional, time-boxed: `inference/run_omnivla.py` load + single forward on MPS
   (bf16) or CPU (bf16), never fp32, with a memory guard.
6. Evidence bundle, experiment decision log (pre-run sections written before the
   first run), and an English summary with claim boundary.

## 4. Out of scope (do not do)

- Training, fine-tuning, CAST/BDD/LeLaN data download, benchmark evaluation.
- Any real-robot, ROS, or `machine-dog` / `machine-dog-nav` code or interface.
- Lite3 adapters (camera/goal/trajectory/command bridge) — later task.
- Remote execution, Isaac/Habitat simulation.
- Editing the pristine upstream snapshot in place; committing checkpoints or
  environments; touching the pre-existing uncommitted `AGENTS.md` change.
- `git commit` by the sub-agent (review + commit belong to the primary AI).

## 5. Constraints

- Follow AGENTS.md research discipline: labels are not promoted; a process exit
  code, a successful download, or an environment build is not a reproduction.
- Third-party bytes stay inside the project under dated, purpose-named paths.
  Large local-only bytes get a path-specific `.gitignore` entry plus a tracked
  manifest with provenance, SHA-256, storage path, and regeneration command.
- Every deviation from the official procedure (patch, package substitution,
  device/dtype change) is recorded as a separate patch file or a line in
  `DEVIATIONS.md` with the reason and the observed error that forced it.
- Memory guard: never load the 8B model in fp32; abort the probe if available
  memory < 22 GB; run every model process under a wall-clock `timeout`.
- Time boxes: environment ≤ 60 min; edge inference ≤ 30 min per attempt;
  original probe ≤ 60 min total; whole task ≤ ~5 h. Stop at the budget and
  report, do not loop.

## 6. Acceptance criteria

- AC1 Import: `third_party/2026-08-18_omnivla_5182600/OmniVLA/` exists with no
  nested `.git`; `SOURCE_MANIFEST.sha256` verifies with `shasum -a 256 -c`;
  `PROVENANCE.md` records URL, commit, tree hash, license, date, and method.
- AC2 Edge checkpoint: `omnivla-edge.pth` present locally; its SHA-256 equals
  the HF LFS oid at the pinned revision; a tracked manifest + path-specific
  ignore rule exist.
- AC3 Original checkpoint: a manifest of every file (name, size, sha256 from HF
  API at the pinned revision) is tracked; if downloaded, local hashes verified.
- AC4 Environment: `env/pip_freeze.txt`, `env/hardware.txt`, `env/install_log.txt`,
  `env/DEVIATIONS.md` recorded.
- AC5 Edge run: official script executed from a working copy (pristine +
  documented patches only) with exit 0; artifacts saved: stdout/stderr, output
  image, raw `8×4` trajectory (finite), metric trajectory, `(v, ω)` (finite and
  inside the script's own clip bounds), wall time and peak RSS.
- AC6 Sensitivity sweep: ≥ 3 configurations (default prompt; a different
  prompt; goal-image and/or pose modality); raw arrays saved per run; a
  comparison table of max-abs differences reported as an observation.
- AC7 Decision log written before the runs (`.pipeline/templates/
  experiment_decision_log.md`), results appended after; claim boundary states
  edge = `reproduced` (non-official env), original = `imported` (+ probe
  outcome), official CUDA reproduction = not done.
- AC8 Repo hygiene: `git status` shows only task-owned paths; pristine manifest
  re-verifies after all runs; no checkpoint / env / working-copy bytes staged;
  `AGENTS.md` pre-existing diff untouched.
- AC9 Patches: all local modifications are `patches/NNNN-*.patch` files with
  rationale; working copy == pristine + patches (excluding run outputs).
