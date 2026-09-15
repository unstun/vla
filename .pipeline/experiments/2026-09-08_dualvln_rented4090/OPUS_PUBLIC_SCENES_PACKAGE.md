---
origin: ai+local
date: 2026-09-09
status: prepared_not_dispatched
executor: Opus
---

# DualVLN: official navigation loop on public Habitat scenes

Write all responses and `OPUS_PUBLIC_SCENES_RETURN.md` in English.

## Goal and scope

Use the publicly available castle and Van Gogh room assets to test DualVLN
through the official InternNav Habitat evaluator. Deliver actual navigation
results and local first-person/top-down videos. MP3D access is not a prerequisite
for this task. This supersedes the previous package's MP3D-only restriction;
preserve the frozen R2R subset and its blocked status as a separate experiment.

- Source of Truth: `/Users/sun/tongbu/study/phdproject/vla`.
- Own `.pipeline/experiments/2026-09-08_dualvln_rented4090` (`EXP`) and
  `.trellis/tasks/09-08-dualvln-rented4090`. Put new artifacts in `EXP/public_scenes/`.
- Remote copy: `/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090`;
  SSH `ubuntu@117.50.179.202`, alias `rented4090`, existing key authentication.
- Read `AGENTS.md` and `review/OFFICIAL_REPRODUCTION_LEAD_REVIEW.md`.
  You are not alone in the repository. Preserve concurrent edits, previous
  evidence, pristine upstream source, and the running `isaac-sim` workload.
- Bounded pretrained simulation and ordinary isolated setup/compatibility fixes
  remain in scope. No training, physical robot actuation, infrastructure changes,
  unrelated process termination, staging, or commit.

## Reuse and fixed inputs

- InternNav commit `7a5c62400ac45b313d9b709c740b64191556a242`; edit only
  `EXP/work/InternNav`, preserving a diff against the pristine snapshot.
- Checkpoint `InternRobotics/InternVLA-N1-DualVLN`, revision
  `a698a9e898b4001621a319e1bc89f02ec715cc86`, original BF16. Reuse verified
  weights and the auxiliary encoder; do not redownload or quantize the model.
- Scene repository: [ai-habitat/habitat_test_scenes](https://huggingface.co/datasets/ai-habitat/habitat_test_scenes),
  revision `910c783fb954da8497ea5f811b843a76590ddddc`, CC BY-NC 4.0.
  Acquire `skokloster-castle.glb` + `.navmesh` and `van-gogh-room.glb` + `.navmesh`.
  Expected sizes and available LFS hashes are in `EXP/setup/habitat_scene_source.json`.
  Verify downloaded bytes and record SHA-256 for every asset. The existing
  `scripts/download_scene.py` selects only the apartment; extend acquisition
  locally for these explicitly named assets instead of assuming they are cached.

## Execute

1. **Finish environment and path preparation.** Habitat-Lab 0.3.3 failed the
   pinned evaluator; 0.2.4 is a candidate, not a verified solution. Build a
   compatible isolated environment and prove evaluator imports/config loading.
   Resolve configuration, annotation, scene, and auxiliary encoder paths from
   the actual launch directory (`work/InternNav`). Existing preflight runs from
   a different directory and missed these path failures. Preserve the official
   policy, camera geometry, preprocessing, look-down behavior, trajectory
   conversion, queues, replanning, and STOP logic.

2. **Preview before model inference.** Check actual RGB/depth renders, camera
   placement, scene geometry, and navmesh reachability in both public scenes.
   Prepare two fixed short navigation episodes, preferably one per scene, using
   clearly visible landmarks and newly written scene-specific instructions.
   Require a finite route and an initial goal distance greater than the official
   3 m success radius. If one scene cannot support a valid case, document why
   before inference and use a second distinct route in the other scene. Preserve
   previews and freeze instructions, start poses, goals, sensor settings, seeds,
   and episode JSON hashes before the first model query. Do not transplant the
   old R2R instructions or coordinates into these scenes.

3. **Use the official evaluator.** Start with `scripts/eval/eval.py` and derive
   a config from `scripts/eval/configs/habitat_dual_system_cfg.py` and
   `vln_r2r.yaml`. Adapt only data paths, the custom episode records, launch
   settings, and observability. Keep official model/control fields and the
   configured 500-step evaluator limit. Do not use the previous custom
   `scripts/sim_runner.py`, add brightness normalization, or invent a replacement
   controller. Scene/task adaptation must be explicit and separate from policy.

4. **Run both fixed cases, including failures.** Use `scripts/run_job.py` or an
   equivalent process-group supervisor with a total 1,800-second GPU evaluation
   deadline. Save exact commands, executed source/config hashes, stdout/stderr,
   exit codes, original model outputs, applied actions, poses, and observations.
   Keep timeouts and parse/fallback termination distinct from learned STOP.
   Report official metrics unchanged, with separate STOP provenance. Record
   whole-run memory peaks and clearly scoped latency; do not reset peak counters
   per step or omit look-down inference from timing/counts.

5. **Deliver video from the actual runs.** Enable official `vis_debug` and
   `save_video`; reuse the existing output-only patch that retains failed cases.
   Include first-person video and a synchronized top-down map or top-down video
   from actual poses. Show pixel goals on the matching camera view. Decode and
   inspect representative start, movement, look-down, and terminal frames.
   Preserve unsuccessful cases; do not replace them after observing outcomes.
   No website or live-streaming interface is needed.

## Sync Gate and return

Author changes locally, sync only owned paths, and verify source/config/asset
identity before each remote run. Return code patches, environment locks, frozen
episode records, raw logs/observations/traces, metrics, and actual MP4 bytes to
the same local relative paths; compare hashes. Remote-only unique outputs leave
the archive incomplete.

Write `EXP/OPUS_PUBLIC_SCENES_RETURN.md` with what actually executed, both episode
outcomes, failures and repairs, exact deviations from upstream, measurements,
local video/evidence paths, sync status, and remaining blockers. Keep the task
at `review` pending lead acceptance. Label the result **official evaluator on
custom public-scene tasks**, not R2R benchmark or paper-score reproduction.
Successful execution and successful navigation are separate conclusions.
