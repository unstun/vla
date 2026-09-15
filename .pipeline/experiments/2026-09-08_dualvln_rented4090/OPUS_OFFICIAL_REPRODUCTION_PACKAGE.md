---
origin: ai+local_source_review
date: 2026-09-09
status: prepared_not_dispatched
lead: Codex
executor: Opus
---

# DualVLN: run the official Habitat evaluation on a small R2R subset

Write all responses and `OPUS_OFFICIAL_REPRODUCTION_RETURN.md` in English.

## Objective and authorization

Dr Sun selected the official evaluation route after reviewing the custom-scene
trial. Run the released DualVLN checkpoint through the pinned repository's
official Habitat evaluator on three fixed R2R `val_unseen` episodes, retaining
the original instructions, starts, goals, observation processing, and control
logic. Return actual local videos and per-episode results, including failures.

This package supersedes `OPUS_CORRECTION_PACKAGE.md` as the next execution
priority. Read `review/LEAD_REVIEW.md` to avoid repeating its evidence errors;
repairing the old custom runner is not a prerequisite for this task. Preserve
the previous runs and keep their outstanding archival/review gaps explicit.

- Source of Truth: `/Users/sun/tongbu/study/phdproject/vla`.
- Own only `.pipeline/experiments/2026-09-08_dualvln_rented4090` (`EXP`) and
  `.trellis/tasks/09-08-dualvln-rented4090`.
- Remote execution copy: `/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090`.
  SSH: `ubuntu@117.50.179.202`, alias `rented4090`; existing key auth works.
- Read `AGENTS.md`. You are not alone in the repository; preserve concurrent
  edits, pristine upstream sources, unrelated remote projects, and the existing
  `isaac-sim` workload. Refresh process identities before execution.
- Isolated environment setup, necessary asset acquisition, ordinary compatibility
  fixes, and this bounded pretrained evaluation are authorized. No training,
  robot actuation, full benchmark sweep, precision change, driver replacement,
  unrelated process termination, staging, or commit.

## Fixed inputs and official entry

- Pristine InternNav: `references/upstream/2026-09-08_dualvln/source/InternNav`,
  commit `7a5c62400ac45b313d9b709c740b64191556a242`.
- Execution source: `EXP/work/InternNav`. The two existing lazy-import shims
  are in `setup/compatibility.patch`; inspect and retain only required changes.
- Checkpoint: `InternRobotics/InternVLA-N1-DualVLN`, revision
  `a698a9e898b4001621a319e1bc89f02ec715cc86`, original BF16, 8.38B parameters.
- Encoder revision: `3bc65d4e14a6786a61acec16453c50e12bf5f338`; reuse the
  verified assets and manifests. Do not download another model.
- Previous inference used Torch 2.6.0+cu124, Transformers 4.51.0,
  FlashAttention 2.7.3, and diffusers 0.32.2. Habitat-Sim alone in a separate
  environment is not proof that the official Habitat-Lab evaluator is ready.

Official command, from the InternNav execution worktree:

```sh
python scripts/eval/eval.py --config scripts/eval/configs/habitat_dual_system_cfg.py
```

Inspect these pinned files before execution:

- `scripts/eval/configs/habitat_dual_system_cfg.py`
- `scripts/eval/configs/vln_r2r.yaml`
- `internnav/habitat_extensions/vln/habitat_vln_evaluator.py`
- `internnav/env/habitat_env.py`

The official YAML selects `val_unseen`, scenes under `data/scene_data/mp3d_ce`,
and annotations under `data/vln_ce/raw_data/r2r/{split}/{split}.json.gz`.
Official single-GPU instructions:
https://internrobotics.github.io/user_guide/internnav/quick_start/evaluation.html
Paper protocol: https://arxiv.org/html/2512.08186#S5.SS1
Use current documentation as guidance; the pinned code defines this run.

## Execution

1. **Check official data and environment availability first.** Locate existing
   authorized Matterport3D assets and original R2R-CE validation annotations.
   Obtain only the selected scene and necessary files through official or
   verifiable authorized distribution. Record URLs, versions, sizes, and hashes.
   Do not download the entire scene collection. If access requires an unavailable
   credential or user-completed dataset request, report the exact missing input
   and official access step; do not substitute `apartment_1`, another dataset,
   invented instructions, or ground-truth actions as policy outputs. Continue
   independent environment/config preparation where possible.

2. **Freeze three episodes before any model trial.** Select one eligible scene
   with at least three `val_unseen` episodes by a recorded deterministic rule
   independent of model outcomes, then take its first three numeric episode IDs.
   Preserve their complete original records, including instructions, starts,
   rotations, goals, and reference paths. Save a selection manifest, source
   annotation hash, and subset hash under `EXP/official_r2r/setup/`. If the
   evaluator has no subset option, create a derived annotation file retaining
   the dataset metadata and unchanged selected episode objects. Do not edit the
   original dataset or choose replacement episodes after failures.

3. **Prepare the official evaluator.** Align Habitat-Lab, Habitat-Sim, and model
   dependencies with the pinned upstream requirements in an isolated environment.
   Reuse verified downloads. Fix import/build/version issues locally and retain
   the patch and environment lock. Create a derived official config changing
   only asset paths, the fixed subset, single-GPU launch settings, output paths,
   and observability. Preserve official camera geometry, history, resizing,
   look-down behavior, trajectory conversion, queues, replanning, and STOP logic.
   Preserve the configured `max_steps_per_episode=500` and Habitat's own step
   limit; record their different counters. Do not reuse `scripts/sim_runner.py`
   or `InternVLAN1AsyncAgent` as a substitute evaluator. Do not add brightness
   normalization, translate instructions, or tune prompts/controller settings.

4. **Run the fixed subset with a deadline.** Use the official `scripts/eval/eval.py`
   entry and derived config. Save the exact command, executed source/config
   hashes, environment, exit code, stdout/stderr, and per-episode output in a
   fresh `EXP/official_r2r/runs/<run_id>/` directory. Limit total GPU evaluation
   time to 1,800 seconds for this pass. Proceed through all three fixed episodes
   regardless of navigation success; stop for a hard runtime failure or deadline.
   Count a deadline interruption as incomplete, not a completed navigation failure.
   Do not reuse stale `progress.json` or silently skip completed episodes from a
   different run. Investigate ordinary runtime errors without expanding the test.

5. **Retain faithful results and videos.** Report official per-episode success,
   navigation error, oracle success, and SPL unchanged. Separately retain raw
   model output/action provenance and termination reason so a timeout or fallback
   STOP cannot be described as an explicit learned STOP. Record actual model
   execution, not just successful loading. Retain RGB/depth observations needed
   to inspect inference, pose/action traces, original instructions, and result
   files. Measure whole-run CUDA peaks without resetting them per step; label
   sampled device memory with its sampling interval and shared-workload scope.
   Distinguish whole-call latency from isolated S1/S2 measurements.

   Enable official `vis_debug` and inspect its coverage. The ordinary `save_video`
   branch in the pinned evaluator saves only successful episodes: failed cases
   must also have video. Prefer existing debug video; if needed, apply a minimal
   output-only patch to save failures without changing policy or environment
   behavior. Deliver first-person video and a top-down route video or synchronized
   map panel from actual simulator poses. Decode locally and inspect start,
   look-down/pixel-goal, movement, and terminal frames. No website is needed.

## Sync Gate and return

Author changes locally. Before every remote run, verify the synced source,
derived config, checkpoint identity, and selected data against local manifests.
Return scripts, patches, configs, raw logs, unique observations/traces, official
results, and actual MP4 bytes to the same local relative paths and verify hashes.
Public reproducible model caches may remain remote with revision/hash records;
any remaining unique remote-only outputs leave the archival gate open. Resume
the previous 864-PNG archive if practical, but report it separately from this run.

Write `EXP/OPUS_OFFICIAL_REPRODUCTION_RETURN.md` with the exact protocol and
deviations, three episode IDs/instructions, per-episode outcomes, commands and
exit codes, environment/patches, measurement scopes, local evidence/video paths,
sync status, and remaining blockers. Mark unexecuted episodes explicitly. Keep
the task at `review` pending lead acceptance and record the actual execution ID.

Acceptance is execution of this fixed subset through the official evaluator,
verifiable results including failures, and complete local evidence. Three
episodes are a bounded reproduction check, not reproduction of the paper's
aggregate success rate. Navigation success is reported separately. If all fail,
preserve them and identify the next evidence-based diagnostic step; do not
silently create a different experiment or label infrastructure readiness as
reproduction.
