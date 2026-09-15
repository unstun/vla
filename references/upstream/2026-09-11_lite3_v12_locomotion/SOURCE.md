# Lite3 V12 locomotion runtime and checkpoint

Local-only bytes with tracked provenance, per AGENTS.md rule 9. Dr Sun approved duplicating them into this repository
(2026-09-11) so that this task's dependency does not live solely inside a sibling repository's ignored directory.

## What this is

The V12 Lite3 velocity policy and the complete runtime tree it needs. It is the only locomotion policy qualified for
navigation control: it produced the accepted closed-loop run `native_full02` (98.08 s, 74.063 m, final XY error 3.77 cm,
zero non-foot contact) in `machine-dog-nav`. The V17 line is not navigation-ready — V17.74 drifts +4.31 m laterally and
+36.2 degrees in heading over 12.5 m of straight commanded walking, and a V17 E3 candidate was rejected by the closed
loop's own command-response gate.

## Identity

| Item | Value |
| --- | --- |
| Upstream project | `machine-dog` (locomotion), via `machine-dog-nav` (qualification) |
| Pinned source commit | `8c3fdffa84b85be0704a10ea5b2533817d543822` ("experiment: prepare model149999 flat diagnosis", 2026-07-18) |
| Implementation subtree | `2_experiment/baseline_rebuild/go2_rl_robotlab_lite3_v12` |
| Gym task id | `Wave-C-Stairs-V12-Lite3-v0` |
| Checkpoint | `model_149999.pt`, 26,367,345 bytes, sha256 `a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450` |
| Upstream authority | `machine-dog-nav/references/locomotion/2026-08-13_v12_model149999/repository_manifest.yaml` |

## Why the bytes are vendored rather than exported from the commit

The upstream manifest records that the commit's source allow-list has 171 entries and **is not a complete runtime tree**:
"The archived manifest is an allow-list, not a complete runtime tree; it omits inherited Go2 environment and base RSL-RL
modules." The complete runtime was recovered from the original 2026-07-18 execution copy. The checkpoint is separately
unreachable from git: it is gitignored upstream at `references/locomotion/.gitignore:1:**/source/`.

So `git archive` at the pinned commit reproduces neither the runtime nor the weights. The commit is identity; these bytes
are the artifact.

## Contents and verification

`source/v12_runtime/` — 217 files, the recovered runtime tree (`__pycache__` and `*.pyc` excluded).
`source/checkpoint/model_149999.pt` — the policy weights.

    cd references/upstream/2026-09-11_lite3_v12_locomotion && shasum -a 256 -c SHA256SUMS.txt

218 entries, all OK at import (2026-09-11).

## Regeneration

    NAV=../machine-dog-nav/references/locomotion/2026-08-13_v12_model149999
    rsync -a --exclude='__pycache__/' --exclude='*.pyc' \
      "$NAV/source/v12_runtime_20260718_recovered/" source/v12_runtime/
    cp "$NAV/source/checkpoint/model_149999.pt" source/checkpoint/
    shasum -a 256 -c SHA256SUMS.txt

If that sibling copy is ever lost, the upstream manifest names the original execution copy
`/home/sun/gpufree-data/2026-07-18_v12_model149999_flat_standstill_diagnosis/runtime/go2_rl_robotlab_lite3_v12` and the
checkpoint's tracked path `artifacts/2026-07-18_v12_model149999_flat_standstill_diagnosis/tracked_checkpoints/model_149999.pt`
in `machine-dog`.

## Known deviation in these bytes

`source/v12_runtime/source/rsl_rl/rsl_rl/utils/exporter_cts.py` does not match the tree's own pristine-base manifest, and
upstream `PROVENANCE.md` claims "exactly one" base-file edit while there are two. The deviation adds a
`history_initialized` buffer so the observation history is filled with the current observation at reset instead of
shifting into zeros.

It does not affect this task's inference path: the changed class `_TorchPolicyExporter` is reached only through
`export_cts_policy_as_jit`, used at training-time export (`on_policy_runner_cts.py:196`, `scripts/rsl_rl/play.py:230`), not
by `run_isaac_v12_fallback.py`. It is recorded here because it documents the intended history-at-reset semantics and
therefore bears on the command-history lag discussed in the task's `design.md`, Decision 4. Reported to Dr Sun; this
repository must not edit `machine-dog`.

## License

Inherits `machine-dog`'s licensing. The runtime vendors `wertyuilife2/go2_rl_robotlab` @ `28b4516`; the Lite3 URDF and
meshes originate from DeepRoboticsLab.
