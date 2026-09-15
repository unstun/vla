# InternVLA-N1 Habitat camera-height ablation on public scenes

Parent: `.trellis/tasks/09-10-lite3-camera-height-internvla-n1`.

## Goal

Measure how the official InternVLA-N1 DualVLN pipeline behaves when the Habitat
camera matches the Lite3 sensor rig instead of the default 1.25 m level camera,
using the official InternNav evaluator on the two frozen skokloster-castle
episodes, and return a mount recommendation to the parent task.

## Background (verified 2026-09-10; details in `research/`)

- Recorded baseline: five runs of two frozen episodes, success 3/5 and 2/5,
  every run ended on a learned System-2 STOP. Camera: 1.25 m, level, 640x480,
  HFOV 79, look-down protocol of two 15-degree tilt steps for System 1.
- Lite3 rig (sensor-rig URDF, torso at the 0.345 m default stance): D435i
  optical centre 0.42 m above ground, 0.25 m ahead of the torso origin,
  pitched 20 degrees down; colour vertical FOV 42 degrees.
- System 1 (NavDP) training randomizes camera height 0.25 to 1.25 m and pitch
  0 to -30 degrees; System 2 training views are 1.25 to 1.55 m. The authors
  raised the Go2 camera with a printed stand for real deployment.
- System 1 sampling is unseeded in the pinned evaluator, so repeated runs of
  the same episode differ; five runs per condition is the baseline convention.

## Requirements

R1. Camera conditions. Baseline B0 reuses the recorded runs `public_eval_v1`
    to `public_eval_v5`; it is not rerun. Four new conditions:

| Id | Name | Sensor height | Forward offset | Pitch | HFOV (VFOV) | Tilt step | Purpose |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | `lite3_rig` | 0.42 m | 0.25 m | 20 deg down, fixed | 54 (41.9) | 0 | Faithful to the current Lite3 rig and to the real-world agent path, which has no look-down tilt |
| C2 | `height_only` | 0.42 m | 0.25 m | level | 79 (63.5) | 15 | Isolates camera height under the unchanged Habitat protocol |
| C3 | `fov_only` | 1.25 m | 0 | level | 54 (41.9) | 15 | Isolates the D435i field of view under the unchanged Habitat protocol |
| C4 | `raised_mount` | 0.65 m | 0.25 m | 15 deg down, fixed | 54 (41.9) | 0 | Candidate raised mount matching the authors' 15-degree real-robot setup |

    Resolution stays 640x480 in all conditions. Habitat's structured config
    types `hfov` as an integer, so HFOV 54 is used; at 4:3 it gives VFOV 41.9
    degrees, the closest integer match to the D435i colour stream's 42-degree
    vertical field of view at a 4:3 profile.
R2. Everything else identical to the baseline: model, evaluator source hash
    `a05268d5e4fac8ab6147d2c828e16ae76d413fe074d2e7f0f99e26ae6fcbf3e7`,
    scene and navmesh hashes, annotation SHA-256, `dual_system` mode, 500
    evaluator steps, five runs per condition, unseeded as in the baseline,
    Habitat-Lab 0.2.4 / Habitat-Sim 0.3.3 environment `official_r2r/official_env_024`.
R3. Preflight per condition before any GPU run: the composed Hydra config
    must resolve to the R1 values; the simulator's own sensor state must show
    the configured height above the agent origin, forward offset, and pitch
    (sign included); a start frame at the episode-1 start pose must be
    rendered (RGB PNG and depth), and the floor z-depth at the bottom image
    rows must imply an agent-origin-to-floor gap within -0.05 to 0.30 m.
    Revised 2026-09-10 by the lead after round 1: the original 25 percent
    floor-distance tolerance assumed the agent origin sits on the floor mesh,
    but at this start pose the navmesh is about 0.16 m above the floor in all
    four conditions, so the ratio test failed the two 0.42 m conditions while
    every direct geometry check passed.
R4. Execution: each run under `scripts/run_job.py` with a 1,800-second
    deadline, sequential, at most 20 runs, fresh run ids, refusing to reuse
    existing run directories. Check free GPU memory against the baseline's
    recorded peak before launching; the resident Isaac Sim process is preserved.
    A failed or timed-out run is preserved and the matrix continues.
R5. Outputs: per run `inputs.json` with the resolved camera geometry and input
    hashes, `progress.json`, `result.json`, raw traces, `environment.json`,
    GPU samples, and the first-person and top-down MP4s; a condition summary
    (JSON and Markdown) with success count, navigation error, oracle success,
    SPL, steps, collisions, STOP provenance, and System-2 branch counts per
    condition, including B0 recomputed from the recorded runs.
R6. Return: all artifacts at the same local relative paths with a SHA-256
    manifest verified locally; `OPUS_RETURN.md` in English; no staging or
    commit by the executor.
R7. Documentation: `RESULT.md` with the claim boundary, a lead review with a
    verdict and mount recommendation, terminology entries for the new terms,
    hot zone and experiments index updates.

## Acceptance criteria

- [ ] AC1 Four condition YAMLs, one derived eval config, launcher, matrix
      runner, preflight, and summariser are authored locally with recorded
      hashes; the execution package is complete per the lead-execute-review
      template.
- [ ] AC2 Four preflight reports pass with resolved geometry equal to R1,
      sensor-state height, offset, and pitch equal to the specification, and a
      rendered start frame whose implied floor gap is within bounds; the lead
      has inspected the four PNGs.
- [ ] AC3 Twenty supervisor records exist; each is exit 0 without timeout, or
      a preserved failure with logs; every run's evaluator, model, scene, and
      annotation hashes equal the baseline's.
- [ ] AC4 The condition summary reports B0 and C1 to C4 on the same metrics,
      recomputed by the lead from `progress.json` and traces, not copied from
      the executor's text.
- [ ] AC5 Every returned MP4 decodes locally and its frame count matches the
      traced episode length; the local manifest verifies 100 percent.
- [ ] AC6 `RESULT.md` and the lead review state the claim boundary and give a
      mount recommendation with effect sizes; the parent PRD acceptance row for
      child 1 can be ticked.

## Claim boundary

This is a functional test on two custom episodes in a public scene, five
unseeded runs each. It reports effect sizes between camera conditions on the
same protocol; it is not a benchmark, not an R2R reproduction, and cannot
attribute failures to System 1 or System 2 conclusively. Trace fields (pixel
goals, System-2 branches, STOP text) give indications only.

## Out of scope

Real-robot work, new episodes, Matterport3D, model or evaluator logic changes,
seeding changes, Habitat agent body or navmesh changes.

## Lead defaults (state objections before activation)

- D435i field of view is modelled as VFOV 41.9 degrees at 4:3 (HFOV 54); the
  16:9 alternative (640x360, HFOV 69) is documented but not run.
- The 0.25 m forward sensor offset is included; the walking height dip to
  about 0.36 m is not modelled.
- Heights are nominal Habitat sensor heights above the agent origin, as in
  every Habitat evaluation including B0; at the episode-1 start pose the
  visible floor is about 0.16 m lower than the agent origin, so effective
  floor clearance is nominal plus about 0.16 m for every condition alike.
- Files live under the DualVLN experiment as a dated request directory, the
  same pattern as the Chinese chairs request, so the existing environment,
  launch-directory links, and scene data are reused.

## Round 4 extension (2026-09-10): head-camera proxy pair

Dr Sun decided to keep the Lite3 built-in wide-angle head camera as the
deployment camera and to test it in simulation first. R1 is extended by two
conditions rendered with the evaluation camera (HFOV 79, 640x480), since the
deployment adapter will centre-crop the wider head-camera stream to that
geometry: C5 `c5_head_level` (0.40 m, 0.27 m ahead, level, tilt 0) and C6
`c6_head_down15` (same, 15 deg down). Height, offset, and pitch are estimates
(vendor torso mesh bracket; third-party calibration of one Lite3 Venture) and
are labelled so in `conditions.json`; they are replaced when measured on the
robot. R2 to R7 apply unchanged; ten more supervised runs under the same limits.

- [x] AC7 Two preflight reports (C5, C6) pass with resolved geometry equal to
      the extension above and tilt_angle 0 behaving as a no-op.
- [x] AC8 Ten supervisor records exist for C5/C6; each is exit 0 without
      timeout, or the failure is preserved and explained; no run rerun.
- [x] AC9 The condition summary reports B0, C1 to C6 on the same metrics; the
      lead review addendum gives the effect of pitch (C5 vs C6) and of the
      fixed-camera protocol (C5 vs C2), and restates the claim boundary and the
      estimated-geometry caveat.

## Round 5 extension (2026-09-11): fused virtual camera

Trigger: the on-robot measurement (research/head_camera_live_2026-09-11) showed the stock head camera points +16.7 deg UP
(HFOV 105 / VFOV 73), so neither C5 nor C6 describes the real mount and no crop of the head stream can emulate the evaluation
camera. Dr Sun: "Simulate the fused camera first" (authorization for about ten more supervised runs).

Requirement: evaluate InternVLA-N1 on the frozen castle episodes when its `rgb` input is a LEVEL virtual evaluation camera
(640x480, HFOV 79) synthesised from the two real mounts as they are (head camera +16.7 deg up, 1280x720 HFOV 105; D435i colour +
colour-aligned depth 20 deg down on the carrier), with black wherever neither mount sees. Two conditions differ only in the D435i
colour resolution (640x480 HFOV 54.6 vs 1280x720 HFOV 69). Reference conditions: C5 (ideal level camera at the same pose, 2/10) and
B0/C2.

Acceptance criteria:
- AC10 The fusion core reproduces an exact synthetic render inside covered regions (PSNR > 25 dB) and reports coverage; the test is
  in the request directory and passes locally. [x]
- AC11 The executor preflight proves, in the official environment, that env.reset()/step() return the fused image under `rgb`
  (bit-identical to an offline recompute, different from the ideal sim render), that every rendered sensor sits at its configured
  height/pitch/offset (Habitat pitch sign for +16.7 deg verified), that coverage and error bounds hold, and that look_down is a no-op. [~] c7 passed all nine stages 2026-09-11 06:38 UTC (head pitch_down -16.7 measured in Habitat: pitch sign for a positive orientation confirmed); c8 passed the same checks but exceeded the provisional fusion-cost bound (226 ms vs 200); bound raised to 300 ms, re-preflight passed in round 5b at 244 ms (bound 300) [x]
- AC12 Ten supervised runs (5 per condition) return with the same evidence set as rounds 1-4 (progress, videos, GPU samples,
  manifests) and a lead review compares C7/C8 against C5 and B0 with oracle success reported beside success. [x] c7 0/10, c8 2/10; LEAD_REVIEW round-5/5b addenda
- AC13 No model or evaluator source is edited: the mechanism is a run-config import of a plugin plus condition YAMLs; the pinned
  evaluator hashes in inputs.json stay equal to the baseline. [x] verified for all ten runs

## Route decision (2026-09-11) and the corrected reading

Dr Sun: "Let's go with the algorithm fusion route (c8 dual-camera fusion with D435i at 1280x720) so we can achieve
deployment purely through software without any hardware modifications." The camera-geometry question this task was opened
to answer is therefore closed: the deployment camera is a fused virtual camera, not a re-mounted physical one.

Re-reading `condition_summary.json` before recording the decision corrected two statements made in the round-5b close-out.
By oracle success (runs entering the goal radius) C8 is 10/10, tied with C6 and above the baseline's 8/10, while C5 is 6/10;
C8's failures are late stops only. And the fused virtual camera is not restricted to level: the covered band allows about
9 deg of downward pitch, measured at 3.05 pct uncovered against 1.28 pct level and 14.56 pct at 15 deg. Both are written up
with their evidence in `research/camera-geometry-and-evaluator-protocol.md`, section 6k.

Consequences for this task: AC1-AC13 stand as recorded; no result changes, only their interpretation. The remaining work is
the commit gate (staged path review by Dr Sun) and archival. Two follow-ons belong to new tasks, not this one:

- C9 `c9_fused_down9`, five supervised runs with the virtual camera 9 deg down, which needs a new run authorization since
  all 40 are used, and one guard relaxation in `fused_camera_plugin.py`.
- Real-robot fusion deployment, whose first blocker is the unmeasured D435i-to-head rigid transform.

## Round 6 extension (2026-09-11): fused virtual camera pitched 9 degrees down

Trigger: the corrected reading above. C8 enters the success radius in 10 of 10 runs, tying C6 and beating the
baseline's 8, and fails only by stopping late; and the fused virtual camera's pitch is free inside the band the two
real mounts cover, up to 9.4 deg down. Dr Sun, 2026-09-11: "Run C9 with the virtual camera 9° down" (five supervised
runs beyond the 40 of rounds 1-5; task total 45).

Requirement: evaluate InternVLA-N1 on the frozen castle episodes with the c8 sensor set unchanged and only the
virtual evaluation camera pitched 9 deg down, to test whether the software-only fusion route recovers C6's stopping
behaviour without any hardware change. Reference conditions: C8 (same fusion, level, 2/10 with oracle 10/10), C6
(ideal render 15 deg down, 5/10) and B0.

- [x] AC14 The fusion core reproduces an exact synthetic render for a PITCHED virtual camera (PSNR > 25 dB inside
      covered regions) and reports coverage; the case is in `test_fused_camera.py` and passes locally.
      SELF_TEST PASSED: head-region 31.0 dB, d435-region 34.6 dB, uncovered 3.05 pct, `virt_pitch_down_deg` 9.0.
- [x] AC15 The executor preflight proves in the official environment that the pitched fused image is what the model
      receives (bit-identical offline recompute, differing from the ideal render), that every sensor sits at its
      configured pose with the pitch sign verified in Habitat, that coverage and error bounds hold, and that
      look_down is a no-op. A materially different uncovered fraction or floor gap is reported, not bounded away.
      All nine stages passed 2026-09-11 12:37 UTC: bit-identical recompute, 71.8 pct of pixels differing from the ideal
      render, uncovered 3.30 pct, head 63.6 pct, poses exact (virtual 9.0 deg down), fusion 256 ms, floor gap 0.1576 m.
- [x] AC16 Five supervised runs return with the same evidence set as rounds 1-5, and a lead review compares C9
      against C8, C6 and B0 with oracle success reported beside success. c9 1/10, oracle 5/10; round-6 addendum in
      review/LEAD_REVIEW.md.
- [x] AC17 No model or evaluator source is edited, and `fused_camera.py` stays byte-identical to rounds 5/5b so that
      C7, C8 and C9 differ only in configuration. Pinned evaluator hashes stay equal to the baseline. Verified:
      fused_camera.py hashes 382eee6d... in all fifteen c7/c8/c9 runs; evaluator and checkpoint hashes equal
      public_eval_v5 in all five c9 runs.
