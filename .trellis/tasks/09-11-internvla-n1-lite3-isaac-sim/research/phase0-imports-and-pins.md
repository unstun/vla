---
origin: lead, direct verification
date: 2026-09-11
label: surveyed
---

# Phase 0.2 / 0.3 / 0.5: pins, vendoring and the live import

## 0.5 — the two-process split is confirmed (DONE)

`InternVLAN1AsyncAgent` imports and constructs in an ordinary ML environment with **no habitat and no Isaac**:

    class InternVLAN1AsyncAgent -> ['__init__', 'reset', 'step', 'step_s2', 'trajectory_tovw', 'parse_actions']
    step(self, rgb, depth, pose, instruction, intrinsic, look_down=False)
    trajectory_tovw(self, trajectory, kp=1.0)

The runtime says so itself on import: *"Habitat Evaluation is not loaded in this runtime. Ignore this if not using
Habitat."* Upstream explicitly supports this mode.

Correction to the earlier static check: the dependency surface is larger than reading the file suggested, though still
ordinary. `internnav/agent/__init__.py` eagerly imports every agent, and the Habitat ones pull `gym`; other package inits
pull `fastapi`/`uvicorn`. None of it is habitat-lab or habitat-sim. Full chain beyond torch/numpy/scipy/PIL:

    gym, pydantic, diffusers, numpy-quaternion, opencv-python, uvicorn, fastapi, transformers

Verified in an isolated venv; `pip freeze | grep -ci 'habitat|isaac'` returns 0. Two traps for whoever builds the real
environment: the module `quaternion` comes from **numpy-quaternion**, not from the PyPI package called `quaternion`
(which installs `Quaternion` and collides with it on a case-insensitive filesystem); and `depth_camera_filtering` is
absent but only gates the Habitat path.

## 0.2 — the bridge is vendored, not commit-pinned, and this was forced

`machine-dog-nav` HEAD at import time: `06cfd9a34c92e16354caa1a418ef2c0467ab44ad`, branch `codex/scan-foxy-isaac`, with 28
modified files under `integration/lite3_sim_bridge`. The four core files differ between the working tree and HEAD.

The decisive test: the accepted closed-loop run `native_full02` records its executed source in
`.pipeline/experiments/2026-09-11_pct_scan_upstream_baseline/full02_evidence/runs/native_full02/executed_source_manifest.json`.
Its `transport.py` entry is `286f24e40957d0d5...`, which is the **working tree**, not HEAD (`652b74bc...`). So the code that
walked 74 m is uncommitted, and a commit pin would have imported code that never produced a successful run.

Vendored 11 files to `references/upstream/2026-09-11_lite3_sim_bridge/`, each verified equal to that run manifest, plus
`SOURCE.md` and `SHA256SUMS.txt` (11 OK). ROS-side and planner files were deliberately not taken: this task drops Foxy.

## 0.2 — the machine-dog side is commit-pinnable, with a caveat

`machine-dog` HEAD `2b6fe4e7bfde5e879c1de506009ccdbbaf84268b`; the V12 subtree
`2_experiment/baseline_rebuild/go2_rl_robotlab_lite3_v12` is clean apart from two untracked test files we do not need.

The authority is `machine-dog-nav/references/locomotion/2026-08-13_v12_model149999/repository_manifest.yaml`, which pins
machine-dog commit **`8c3fdffa84b85be0704a10ea5b2533817d543822`** (verified to exist) and states the export boundary:
*"Use git archive at the pinned commit; the current dirty sibling worktree is not a runtime source."*

Caveat, recorded by that manifest itself: the git snapshot's 171-entry allow-list **does not contain the complete runtime
dependency tree**. The complete runtime was recovered from the original execution copy into
`source/v12_runtime_20260718_recovered` — 217 files, 86 MB, verified present. So the runtime must be taken from the
recovered tree, and the commit pin serves as identity rather than as the export.

## A finding about the recovered tree that machine-dog should know

`base_manifest.sha256` inside the recovered tree is a **pristine-base** manifest of 131 files (the tree's other 86 files are
generated `outputs/` hydra logs plus the provenance files). Verifying against it gives 129 OK and 2 FAILED:

1. `scripts/rsl_rl/train.py` — **expected**. PROVENANCE.md documents it as the single deliberate base-file edit.
2. `source/rsl_rl/rsl_rl/utils/exporter_cts.py` — **undocumented**, and PROVENANCE.md claims "exactly one" base-file edit.

The second is not cosmetic. Diffed against the pristine clone at
`machine-dog/1_survey/2026-07-09_go2-rl-gym-reference/go2_rl_robotlab`, it adds a `history_initialized` buffer and changes
observation-history initialisation: on the first step after reset it fills the whole history with the current observation
(`single_term.repeat(1, self.history_len)`) instead of shifting into a zero history.

Impact on this task: **none directly.** The changed class `_TorchPolicyExporter` is used only by
`export_cts_policy_as_jit`, called from `on_policy_runner_cts.py:196` and `scripts/rsl_rl/play.py:230` — training-time
export, not the inference path that `run_isaac_v12_fallback.py` takes.

But it is a useful hint for Phase C. It shows the intended semantics for history at reset, and it implies the exported JIT
policy gets that fix while an in-process runner may not. Whether the loop we run fills history at reset or shifts into
zeros is something Phase A should measure rather than assume, because it interacts directly with the command-history lag
in `design.md` Decision 4. This is a finding about `machine-dog`'s provenance record; this task must not edit that
repository, so it is reported to Dr Sun only.

## 0.3 — the checkpoint is identified and verified

    model_149999.pt   26,367,345 bytes
    sha256 a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450

Matches `repository_manifest.yaml` exactly. It is gitignored upstream
(`references/locomotion/.gitignore:1:**/source/`), so no commit pin reproduces it.

**Storage: resolved (Dr Sun, 2026-09-11) — option (a), duplicate into `vla` with a path-specific ignore.**

Done: `references/upstream/2026-09-11_lite3_v12_locomotion/` holds `source/v12_runtime/` (217 files) and
`source/checkpoint/model_149999.pt`, 111 MB total, with tracked `SOURCE.md` and a 218-entry `SHA256SUMS.txt` that verifies
218 OK. The checkpoint entry equals the upstream manifest's `a9d31dce...3d5450`.

Two notes on how the ignore actually landed:

1. The bytes were already covered by a pre-existing blanket rule, `references/upstream/.gitignore:1:**/source/`, which is
   the established convention for every upstream snapshot in this repository. The entry added to the root `.gitignore` is
   therefore deliberately redundant, and says so: its purpose is to document a 111 MB local-only artifact alongside the
   repository's other large-byte exceptions instead of leaving it invisible there.
2. That same blanket rule also ignored the vendored bridge source (477 KB after the Phase A correction below) in
   `references/upstream/2026-09-11_lite3_sim_bridge/source/`. For every other entry under `references/upstream/` that is
   harmless, because the bytes are re-fetchable from a pinned public commit or a Hugging Face revision. The bridge is
   different: it was vendored from an **uncommitted working tree** in `machine-dog-nav`, which is actively moving (HEAD
   changed between the survey and the import). `SHA256SUMS.txt` lets us detect drift but cannot regenerate the bytes if
   that worktree changes or is cleaned.

   **Resolved (Dr Sun, 2026-09-11): track them.** `references/upstream/.gitignore` now negates the directory
   (`!2026-09-11_lite3_sim_bridge/source/`) with the reason written beside it; the negation has to name the DIRECTORY,
   because `**/source/` excludes the directory itself and git does not descend into an excluded directory to reach a
   file-level negation. Verified: `git check-ignore -v` no longer matches any bridge file, still matches
   `.../2026-09-11_lite3_v12_locomotion/source/checkpoint/model_149999.pt`, all 15 checksums verified OK before
   staging, and the files carry no CRLF with `text`/`eol` unspecified in `.gitattributes`, so nothing normalises the
   bytes away from their recorded hashes. 17 new paths plus the modified `references/upstream/.gitignore` are staged
   (11,391 added lines) awaiting Dr Sun's commit review. The root `.gitignore` was deliberately NOT staged: it carries
   uncommitted blocks belonging to four earlier tasks.

   **Defect found and fixed while staging (2026-09-11).** The 11-file selection recorded in 0.2 was not importable:
   `run_isaac_v12_fallback.py` imports `.run_isaac_lite3`, `.mid360_pattern`, `.official_human_contract` and
   `.office_crowd_contract` at MODULE level, and all four were cut as scene-study code. The first Phase A run would
   have died on `ModuleNotFoundError` before Isaac Sim started. All four are now vendored and each was verified
   against the same `native_full02` executed-source manifest; all 15 files were then re-checked file by file against
   that manifest and matched. Closure is now verified by walking each file's AST, not by reading imports. The single
   remaining unvendored `from .` target, `office_review_presentation.py` (124 KB), is excluded on purpose: all six of
   its import sites are inside functions and gated by `--office-review-*` flags a flat-course run never passes.
   Lesson: a vendored package's import closure must be checked mechanically at import time, not inferred from
   file names.
