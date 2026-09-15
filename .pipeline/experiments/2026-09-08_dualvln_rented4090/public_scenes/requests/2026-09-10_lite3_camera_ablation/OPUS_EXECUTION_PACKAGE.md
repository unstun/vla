---
origin: ai+local_evidence+user_instruction
reviewed: false
date: 2026-09-10
lead: Claude Fable 5.1 (lead)
executor: Opus
status: executed_lead_accepted
round5_dispatched_utc: 2026-09-11T06:33:49Z
round4_dispatched_utc: 2026-09-10T15:33:00Z
executed_rounds: 4 (2026-09-10); all 30 runs returned and accepted; see review/LEAD_REVIEW.md round-4 addendum. Round 5/5b (fused virtual camera, 10 runs) executed and accepted 2026-09-11; 40 runs total
dispatched_utc: 2026-09-10T09:40:26Z
dispatch_route: Opus subagent via Claude Code Agent tool, authorized by Dr Sun on 2026-09-10
trellis_task: .trellis/tasks/09-10-internvla-n1-camera-ablation-sim
---

# Lite3 camera-condition ablation of InternVLA-N1 DualVLN: execution package

Write responses and `OPUS_RETURN.md` in English.

## Goal and scope

- Goal: run the official InternNav evaluator on the two frozen
  skokloster-castle episodes under four camera conditions (five runs each) and
  return raw results, videos, and a per-condition summary that the lead can
  compare with the recorded baseline `public_eval_v1..v5`.
- Lead / executor: Claude Fable 5.1 prepared this package and reviews the
  return; Opus executes.
- Source of Truth: `/Users/sun/tongbu/study/phdproject/vla`. `EXP` =
  `.pipeline/experiments/2026-09-08_dualvln_rented4090`; `REQ` =
  `EXP/public_scenes/requests/2026-09-10_lite3_camera_ablation`.
- Authorization (Dr Sun, 2026-09-10): bounded pretrained simulation only. At
  most 20 supervised evaluator runs of at most 1,800 s each. No training or
  fine-tuning, no robot actuation, no change to model or evaluator logic, no
  new episodes, no stopping of unrelated processes. Repair ordinary
  configuration or runtime failures within scope; return anything that would
  change a condition, the protocol, or the acceptance criteria to the lead.
- Owned paths: `REQ/**`, `EXP/public_scenes/configs/vln_cam_*.yaml`,
  `EXP/public_scenes/configs/habitat_dual_system_cam_cfg.py`,
  `EXP/public_scenes/runs/cam_*`, `EXP/runs/cam_*`, and the task's
  `OPUS_RETURN.md`. Frozen: everything else, in particular the InternNav
  worktree, the checkpoints, the scene and annotation files, the baseline runs
  and the zh chairs request, `.trellis/tasks/09-08-dualvln-rented4090`, and the
  resident `isaac-sim` container.
- Executor runtime: you run as a background subagent of the lead session with
  the repository checked out locally; reach the remote with `ssh rented4090`
  (or `ubuntu@117.50.179.202`) and `rsync`. Per-command tool timeouts are
  short, so start the preflight loop and the matrix on the remote under
  `nohup ... > <log> 2>&1 &` and poll the logs with short ssh calls.
- Remote copy / Sync Gate: `/home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090`
  on `rented4090` (`ubuntu@117.50.179.202`, existing key). Sync in only the
  owned files, verify them against `REQ/authored_files.sha256` before running,
  and return all evidence to the same local relative paths with
  `REQ/manifest.sha256` verified locally.

Read `AGENTS.md`, `EXP/review/PUBLIC_SCENES_LEAD_REVIEW.md`, and the task's
`prd.md`, `design.md`, and `research/camera-geometry-and-evaluator-protocol.md`.
You are not alone in the repository; preserve concurrent edits.

## Verified context

- Baseline: five runs of two frozen episodes, success 3/5 and 2/5, every run
  ended on a learned System-2 STOP; camera 1.25 m, level, 640x480, HFOV 79,
  two 15-degree look-down steps for System 1. Input hashes in
  `EXP/public_scenes/runs/public_eval_v5/inputs.json`; evaluator hash
  `a05268d5e4fac8ab6147d2c828e16ae76d413fe074d2e7f0f99e26ae6fcbf3e7`.
- Environment: `official_r2r/official_env_024` (Habitat-Lab 0.2.4, Habitat-Sim
  0.3.3) completed the baseline runs; do not reinstall. Launch-directory links
  come from `public_scenes/scripts/link_launch_dir.sh`.
- Conditions: `REQ/conditions.json` is the single source of truth. The YAMLs
  in `EXP/public_scenes/configs/vln_cam_*.yaml` were generated from it by
  `REQ/make_condition_yamls.py`; `REQ/yaml_diffs.json` shows that only sensor
  position, orientation, hfov, and `tilt_angle` differ from the baseline YAML.
  `habitat_dual_system_cam_cfg.py` differs from the baseline config only by
  reading `CAM_YAML` and `CAM_RUN_DIR`.
- Evaluator protocol facts (lead-verified in the worktree source): in
  `dual_system` mode the evaluator uses no camera transform or intrinsic;
  `tilt_angle: 0` makes the two look-down steps no-ops, which mirrors the
  real-world agent path where the camera is fixed.
- Local checks already passed: YAML parse, `py_compile`, `bash -n`, and
  `summarise_conditions.py` reproducing 3/5 and 2/5 for the baseline.
- Open questions: Habitat's orientation sign is verified only by the preflight
  render (stage "start frame renders ..."), which reads the simulator's own
  sensor state and the depth image. If it fails for a pitched condition,
  return the report and PNGs; do not flip signs yourself. The floor-distance
  check compares the 90th percentile of the bottom-row depth with the z-depth a
  flat floor returns for the configured geometry (Habitat depth is measured
  along the optical axis, so for the pitched C1 and C4 it is about 24 and 15
  percent larger than the ground distance h / tan(pitch + VFOV/2) quoted in the
  research note). It may be sensitive to furniture in level conditions; if only
  that sub-check fails while the sensor-state height and pitch checks pass,
  return the numbers and PNGs to the lead before running that condition.

## Remaining work

1. Sync Gate in. From the local repository copy `REQ/` and the five config
   files to the remote `EXP`; on the remote run
   `sha256sum -c public_scenes/requests/2026-09-10_lite3_camera_ablation/authored_files.sha256`
   from the `EXP` root and require every line `OK`. Confirm the worktree
   evaluator hash equals the baseline value above.
2. Resource check: record `nvidia-smi` and the resident processes in
   `REQ/preflight/resources_before.txt`. Stop nothing.
3. Links and preflight, from the launch directory:

   ```bash
   cd /home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
   bash public_scenes/scripts/link_launch_dir.sh
   cd work/InternNav
   mkdir -p public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight
   for c in c1_lite3_rig c2_height_only c3_fov_only c4_raised_mount; do
     CAM_YAML=public_scenes/configs/vln_cam_$c.yaml \
       ../../official_r2r/official_env_024/bin/python \
       public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight_cam.py --cond $c \
       2>&1 | tee public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/${c}_stdout.txt
   done
   ```

   Expected: `ALL_STAGES_PASSED` four times, four `preflight/<cond>.json`
   with `all_stages_passed: true`, and eight PNGs. A condition whose preflight
   fails is not run; report it and continue with the others.
4. Matrix, from the experiment root (each run is supervised at 1,800 s;
   condition-major; existing run ids are skipped):

   ```bash
   cd /home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
   bash public_scenes/requests/2026-09-10_lite3_camera_ablation/run_matrix.sh \
     2>&1 | tee public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_stdout.txt
   ```

   Expected: 20 lines in `REQ/matrix_log.jsonl`, each with `exit_code` 0 and
   `timed_out` false, and 20 directories `public_scenes/runs/cam_<cond>_v<k>`
   each holding `progress.json` with two episodes. A failed or timed-out run is
   preserved as evidence; do not delete or rerun it under the same id. If the
   matrix stops on two consecutive CUDA out-of-memory failures, report the
   shared-GPU state and stop.
5. Summary and media checks:

   ```bash
   official_r2r/official_env_024/bin/python \
     public_scenes/requests/2026-09-10_lite3_camera_ablation/summarise_conditions.py
   python3 - <<'PY'
   import glob, json, subprocess
   out = {}
   for f in sorted(glob.glob('public_scenes/runs/cam_*/vis_debug/epoch_0/*.mp4') +
                   glob.glob('public_scenes/runs/cam_*/vis_0/*/*.mp4')):
       r = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0',
                           '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', f],
                          capture_output=True, text=True)
       out[f] = {'frames': r.stdout.strip(), 'error': r.stderr.strip() or None}
   json.dump(out, open('public_scenes/requests/2026-09-10_lite3_camera_ablation/ffprobe_frame_counts.json', 'w'), indent=2)
   print(len(out), 'videos probed')
   PY
   ```

   Expected: every MP4 decodes without error and its `vis_debug` frame count
   equals the traced episode length (`final_step_id` in the trace footer, equal
   to `steps` in `progress.json`), as in the baseline: `public_eval_v5` has 81
   and 116 frames for 81 and 116 steps.
6. Manifest and Sync Gate out, after the last file edit:

   ```bash
   cd /home/ubuntu/sun/vla_exec/2026-09-08_dualvln_rented4090
   find public_scenes/runs/cam_* runs/cam_* public_scenes/requests/2026-09-10_lite3_camera_ablation -type f \
     ! -name manifest.sha256 ! -name OPUS_RETURN.md -print0 | sort -z | xargs -0 sha256sum \
     > public_scenes/requests/2026-09-10_lite3_camera_ablation/manifest.sha256
   ```

   `OPUS_RETURN.md` is written in step 7, after the manifest, and is the only
   returned file deliberately outside it. Return `public_scenes/runs/cam_*`,
   `runs/cam_*`, and `REQ/` to the same local relative paths; the lead verifies
   with `shasum -a 256 -c` from the local `EXP` root.
7. Write `REQ/OPUS_RETURN.md`: exact commands, per-condition preflight
   outcome, per-run id/exit/deadline/wall time, the `condition_summary.md`
   table, deviations, resource notes, sync status, and remaining issues. Keep
   the Trellis task at `review`; do not stage or commit.

## Return

Provide the owned diff, actual commands and outcomes, raw logs and results,
local media paths, source and sync status, deviations, and remaining issues.
State commit status (expected: nothing committed).

The lead verifies the manifest, every run's `inputs.json` hashes against the
baseline, the four preflight PNGs, a recomputed condition summary from
`progress.json` and traces, and decoded videos before accepting the result.
Acceptance is recorded in `REQ/review/LEAD_REVIEW.md`; the result label is
"official evaluator on custom public-scene tasks" plus the condition name.

## Round 2 (2026-09-10): C1 and C2 after the criterion revision

Round 1 (returned 2026-09-10) ran C3 and C4 (10 runs, all exit 0, no
timeouts) and held C1 and C2: their preflights failed only the floor
z-depth ratio sub-check while the sensor-state height, forward offset, and
pitch (sign included) matched exactly. The four measurements imply a constant
agent-origin-to-floor gap of 0.158 to 0.163 m at this start pose, a navmesh
property that applies to the baseline alike. The lead therefore replaced the
ratio test by an implied-gap bound (-0.05 to 0.30 m, `conditions.json`
`preflight.floor_gap_bounds_m`), made the preflight persist its numbers on
failure, and made `run_matrix.sh` gate on the preflight verdict rather than on
file existence. The round-1 C1/C2 reports are archived under
`REQ/preflight/round1_failed_ratio_criterion/`. C3 and C4 are not re-run;
their round-1 reports remain valid (implied gaps 0.163 m and 0.159 m).

Round-2 steps, same authorization and limits (10 of the 20 authorized runs
remain: `cam_c1_lite3_rig_v1..v5`, `cam_c2_height_only_v1..v5`):

1. Sync Gate in again for `REQ/` and the five config files; require
   `sha256sum -c public_scenes/requests/2026-09-10_lite3_camera_ablation/authored_files.sha256`
   to report 15 OK on the remote. Do not delete the round-1 evidence on
   either side.
2. Resource check into `REQ/preflight/resources_before_round2.txt`.
3. Preflight only `c1_lite3_rig` and `c2_height_only` with the same command
   as step 3 above (the round-1 stdout files are overwritten; their copies are
   archived). Expected: `ALL_STAGES_PASSED` for both, with
   `implied_agent_origin_to_floor_gap_m` close to 0.16 m in the stage-5 detail.
   If either still fails, return the report and PNGs and do not run it.
4. `bash public_scenes/requests/2026-09-10_lite3_camera_ablation/run_matrix.sh c1_lite3_rig c2_height_only`
   under nohup from the remote EXP root; ten supervised runs; existing
   run ids are skipped; failures are preserved.
5. Re-run the summariser (it now covers all 20 runs) and the ffprobe loop over
   all `cam_*` MP4s, regenerating `ffprobe_frame_counts.json`.
6. Regenerate `manifest.sha256` for all `cam_*` runs and `REQ/` as in step 6
   above, return the round-2 run directories, supervisor records, and `REQ/`
   to the same local relative paths, and verify the manifest locally.
7. Append a "Round 2" section to `REQ/OPUS_RETURN.md` (do not rewrite the
   round-1 text) with the same content requirements as step 7 above.

## Round 3 (2026-09-10): C1 after the tilt no-op criterion revision

Round 2 ran C2 (5 runs, all exit 0) and held C1: it passed the revised
floor check (implied gap 0.158 m) and every sensor-state check, but stage 6
required a bit-identical frame after a zero-amount look_down, and the
executor's read-only diagnostic (`REQ/preflight/diag_round2_tilt_noop_c1_lite3_rig.json`)
showed a 1-2 ULP quaternion re-normalisation that changes the pitch by
5.5e-7 degrees and flips 0.31 percent of edge pixels with the sensor position
unchanged. The lead replaced the bit-identical test by bounds on the pitch
delta (0.01 degrees) and the changed-pixel fraction (1 percent) for
`tilt_angle: 0`, and a minimum changed fraction (5 percent) for non-zero
tilt (`conditions.json` `preflight.tilt_noop_*`). Round-2 C1 artefacts are
archived under `REQ/preflight/round2_c1_stage6_blocked/`.

Round-3 steps, same authorization and limits (5 authorized runs remain:
`cam_c1_lite3_rig_v1..v5`):

1. Sync Gate in again for `REQ/` and the five config files; require 15 OK
   from `authored_files.sha256` on the remote. Keep all earlier evidence.
2. Resource check into `REQ/preflight/resources_before_round3.txt`.
3. Preflight only `c1_lite3_rig` with the step-3 command. Expected:
   `ALL_STAGES_PASSED`, stage-6 detail with `changed_pixel_fraction_after_look_down`
   about 0.003 and `pitch_delta_deg_after_look_down` about 0. If it fails,
   return the report and do not run.
4. `bash public_scenes/requests/2026-09-10_lite3_camera_ablation/run_matrix.sh c1_lite3_rig`
   under nohup from the remote EXP root; five supervised runs.
5. Re-run the summariser over all runs and the ffprobe loop over all `cam_*`
   MP4s, regenerating `ffprobe_frame_counts.json`.
6. Regenerate `manifest.sha256` over all `cam_*` runs and `REQ/`, return the
   round-3 run directories, supervisor records, and `REQ/` to the same local
   relative paths, and verify the manifest locally.
7. Append a "Round 3" section to `REQ/OPUS_RETURN.md` (keep rounds 1 and 2
   intact) with the same content requirements as step 7 of round 1.

## Round 4 (2026-09-10): head-camera proxy pair C5 and C6

Dr Sun decided on 2026-09-10 to keep the Lite3 built-in wide-angle head camera
as the deployment camera and to test it in simulation first. The head camera's
lens is wider than the evaluation camera in both axes, so the deployment
adapter will centre-crop the 1280x720 stream to the evaluation camera's
geometry (HFOV 79 at 4:3); the simulation therefore keeps the evaluation
camera and varies only height, forward offset, pitch, and tilt. Geometry basis
(all labelled in `conditions.json` and the child task's research note,
sections 6b-6d): height 0.40 m and offset 0.27 m from the vendor torso mesh
bracket and a third-party calibration; pitch 15 deg down from the same third
party (their alternative figure is 11 deg). These are estimates until the
on-robot measurement replaces them.

| Condition | Height | Offset | Pitch | HFOV | tilt_angle | Runs |
| --- | --- | --- | --- | --- | --- | --- |
| c5_head_level | 0.40 m | 0.27 m | 0 | 79 | 0 | cam_c5_head_level_v1..v5 |
| c6_head_down15 | 0.40 m | 0.27 m | 15 deg down | 79 | 0 | cam_c6_head_down15_v1..v5 |

Authorization: Dr Sun, 2026-09-10, "Go ahead and implement it in simulation
first. Keep the cam"; same limits as rounds 1-3 (supervised runs of at most
1,800 s each, no training, no robot actuation, no model or evaluator changes,
no new episodes, nothing unrelated stopped). Ten authorized runs.

Round-4 steps:

1. Sync Gate in for `REQ/` and the seven config files
   (`habitat_dual_system_cam_cfg.py`, `vln_cam_c1..c6_*.yaml`); require 17 OK
   from `authored_files.sha256` on the remote. Keep all earlier evidence; do
   not touch `cam_c1..c4` run directories.
2. Resource check into `REQ/preflight/resources_before_round4.txt` (nvidia-smi,
   resident processes; stop nothing).
3. Preflight `c5_head_level` and `c6_head_down15` with the step-3 command of
   round 1 (the official env's python, `preflight_cam.py --cond <cond>` from
   the launch directory after `link_launch_dir.sh`). Expected: `ALL_STAGES_PASSED`
   for both; stage 5 implied floor gap about 0.16 m (within bounds); stage 6
   `pitch_delta_deg_after_look_down` about 0 and
   `changed_pixel_fraction_after_look_down` about 0.003 (tilt_angle 0 for both).
   If either fails, return the report and PNGs and do not run that condition.
4. `nohup bash public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round4.sh c5_head_level c6_head_down15 > public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round4_stdout.txt 2>&1 &`
   from the remote EXP root; ten supervised runs, condition-major; poll the
   log with short ssh calls. Never rerun or delete a failed run id.
5. Re-run `summarise_conditions.py` over all runs (30 plus B0) and the ffprobe
   loop over all `cam_*` MP4s, regenerating `ffprobe_frame_counts.json`.
6. Regenerate `manifest.sha256` over all `cam_*` runs and `REQ/` (excluding
   itself and `OPUS_RETURN.md`), return the round-4 run directories
   (`EXP/public_scenes/runs/cam_c5_*`, `cam_c6_*`), supervisor records
   (`EXP/runs/cam_c5_*`, `cam_c6_*`), and `REQ/` to the same local relative
   paths, and verify the manifest locally.
7. Append a "Round 4" section to `REQ/OPUS_RETURN.md` (keep rounds 1-3
   intact): commands, run ids, exit codes, wall times, per-condition table,
   deviations, remaining issues, sync status; no commit.

## Round 5 (2026-09-11): fused virtual camera C7 and C8

Background. The Lite3 head camera was measured on the robot on 2026-09-11
(checkerboard, 36 poses, RMS 0.29 px): fx 490 / fy 487 at 1280x720 (HFOV 105,
VFOV 73) and an optical axis pitched +16.7 deg UP relative to gravity with the
torso level. It therefore sees only ~21 deg below horizontal and no crop of its
stream can emulate the evaluation camera, even level. The only fixed
downward-looking mount is the D435i carrier (0.42 m, 0.25 m forward, 20 deg
down). Dr Sun's instruction (2026-09-11): "Simulate the fused camera first".

Condition design. A LEVEL virtual pinhole camera with the evaluation camera's
geometry (640x480, HFOV 79) at the head camera's optical centre is composed
every step from two rendered real mounts: the head camera by pure rotation
(fixed lookup table) and the D435i colour by depth-based reprojection (its own
colour-aligned z-depth). Head pixels where the head sees (about the top 78 % of
the image), an 8-row feather into the D435i image, D435i below, black where
neither sees (bottom corners). tilt_angle 0. The evaluator's `depth` input is
an ideal depth sensor at the virtual pose; the shipped System 1 never reads it.

| Condition | Head sensor | D435i colour + depth | Virtual `rgb` | Expected uncovered | Runs |
| --- | --- | --- | --- | --- | --- |
| c7_fused_level | 1280x720, HFOV 105, +16.7 deg, (0, 0.40, -0.27) | 640x480, HFOV 55 (datasheet 54.6 rounded: hfov is an integer field), -20 deg, (0, 0.42, -0.25) | 640x480, HFOV 79, level, head centre | ~6 % | cam_c7_fused_level_v1..v5 |
| c8_fused_level_720 | same | 1280x720, HFOV 69, -20 deg, same pose | same | ~1.3 % | cam_c8_fused_level_720_v1..v5 |

Mechanism (config-level; no model or evaluator source edits). The run config
`public_scenes/configs/habitat_dual_system_fused_cfg.py` imports
`REQ/fused_camera_plugin.py`, which registers three extra habitat-sim sensors
(uuids head_rgb, d435_rgb, d435_depth) and a habitat-lab task sensor
`fused_rgb_sensor` with uuid `rgb`; habitat-lab merges task-sensor
observations over simulator observations in EmbodiedTask.reset/step, so every
`observations["rgb"]` the evaluator, the model and the video writer read is the
fused image. The ordinary sim `rgb_sensor` stays (the evaluator reads its
position) and doubles as the ideal reference that the preflight compares
against. The fusion core `REQ/fused_camera.py` passed a local synthetic
self-test (`REQ/test_fused_camera.py`: PSNR 32-36 dB against an exact render) and a
static review against the habitat-lab v0.2.4 sources (four defects fixed before dispatch,
see `REQ/local_validation.txt`).
`run_cam_eval.sh` now takes the eval config per condition from
`conditions.json` (rounds 1-4 conditions still resolve to the camera config).

Authorization: Dr Sun, 2026-09-11, "Simulate the fused camera first"; same
limits as rounds 1-4 (supervised runs of at most 1,800 s each, no training, no
robot actuation, no model or evaluator source changes, no new episodes,
nothing unrelated stopped). Ten authorized runs.

Connectivity for round 5 (2026-09-11): from the lead's Mac the direct `ssh rented4090`
times out during the SSH banner exchange although the instance is running (Dr Sun
confirmed and rebooted it at about 06:30 UTC); the route through the lab machine works:
`ssh -J gpu40901 rented4090` and `rsync -e 'ssh -J gpu40901' ...`. Use the jump for every
ssh/rsync in this round. The instance was rebooted before dispatch, so re-record resident
processes in step 2 (an isaac-sim container may be back; stop nothing).

Round-5 steps:

1. Sync Gate in for `REQ/` and the ten config files (`habitat_dual_system_cam_cfg.py`,
   `habitat_dual_system_fused_cfg.py`, `vln_cam_c1..c8_*.yaml`); require 26 OK
   from `authored_files.sha256` on the remote. Keep all earlier evidence; do not
   touch `cam_c1..c6` run directories.
2. Resource check into `REQ/preflight/resources_before_round5.txt` (nvidia-smi,
   resident processes; stop nothing).
3. Run `bash REQ/preflight/run_preflight_round5.sh` from the remote EXP root
   (it links the launch directory, then runs `preflight_fused.py` for both
   conditions with the official env's python). Expected: `ALL_STAGES_PASSED`
   for both, with stage 6 reporting `fused_equals_offline_recompute: true`,
   `fraction_of_pixels_differing_from_ideal` well above 0.01, coverage `none`
   about 0.06 (c7) and 0.013 (c8), head-region mean error below 10, and every
   sensor state at its configured height/pitch/offset (head pitch_down -16.7,
   d435 +20, rgb 0). If a stage fails, return the JSON, stdout and PNGs and do
   not run that condition; do not edit the plugin or the preflight.
4. `nohup bash public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round5.sh c7_fused_level c8_fused_level_720 > public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round5_stdout.txt 2>&1 &`
   from the remote EXP root; ten supervised runs, condition-major; poll the
   log with short ssh calls. Never rerun or delete a failed run id. If the
   first run of c7 exits non-zero, read its stderr, return it, and stop the
   matrix (kill only the driver and that run's process group via
   `scripts/run_job.py`'s records) before starting c8.
5. Re-run `summarise_conditions.py` over all runs (40 plus B0) and the ffprobe
   loop over all `cam_*` MP4s, regenerating `ffprobe_frame_counts.json`.
6. Regenerate `manifest.sha256` over all `cam_*` runs and `REQ/` (excluding
   itself and `OPUS_RETURN.md`), return the round-5 run directories
   (`EXP/public_scenes/runs/cam_c7_*`, `cam_c8_*`), supervisor records
   (`EXP/runs/cam_c7_*`, `cam_c8_*`), and `REQ/` to the same local relative
   paths, and verify the manifest locally.
7. Append a "Round 5" section to `REQ/OPUS_RETURN.md` (keep rounds 1-4
   intact): commands, run ids, exit codes, wall times, per-condition table,
   preflight coverage/error numbers, deviations, remaining issues, sync
   status; no commit.

### Round 5b (2026-09-11, after the c7 runs): c8 re-preflight and runs

The 06:38 UTC preflight passed all nine stages for c7 and eight of nine for c8: c8
failed only stage 8, "fusion cost per frame", at 226.5 ms against the lead's
pre-measurement bound of 200 ms (c7: 135.7 ms). Every geometric and override check
passed for both. The lead raised the bound to 300 ms in `conditions.json`
(recorded there with the measured numbers). The five c7 runs (round 5, returned
and accepted by the lead on 2026-09-11) all recorded the earlier conditions.json
hash 21bab3bf...; c8 runs will record the new one, which is expected.

5b-1. The c7 matrix is finished (MATRIX_DRIVER_DONE rc=0, five run ids). Do not
      touch cam_c1..c7 run directories.
5b-2. Sync Gate in again for `REQ/` (this package, conditions.json, provenance.json,
      authored_files.sha256, review/); require 26 OK from `authored_files.sha256`
      on the remote from `work/InternNav`.
5b-3. From the remote EXP root:
      `nohup bash public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/run_preflight_round5.sh c8_fused_level_720 > public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/run_preflight_round5b_stdout.txt 2>&1 &`
      Expected `ALL_STAGES_PASSED` (nine stages; stage 8 now bounded at 300 ms).
      If it fails again, stop and report.
5b-4. `nohup bash public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round5.sh c8_fused_level_720 > public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round5b_stdout.txt 2>&1 &`
      Five supervised runs cam_c8_fused_level_720_v1..v5.
5b-5. Then steps 5-7 of round 5 over all runs (40 plus B0): summaries, ffprobe,
      manifest (exclude `__pycache__` as in R5-D4), return `cam_c8_*` run and
      supervisor directories and `REQ/` (do NOT overwrite `REQ/review/`,
      `REQ/RESULT.md` or `REQ/OPUS_EXECUTION_PACKAGE.md` on the way back: rsync
      with `--exclude review/ --exclude RESULT.md --exclude OPUS_EXECUTION_PACKAGE.md`),
      append a "Round 5b" section to `OPUS_RETURN.md`.


## Round 6 (2026-09-11): fused virtual camera pitched 9 degrees down (C9)

Authorization: Dr Sun, 2026-09-11, "Run C9 with the virtual camera 9° down." Five
supervised runs, same per-run limits as rounds 1-5 (1,800 s deadline each, no
training, no robot actuation, no model or evaluator source edits, no reruns of a
failed run id, never stop the unrelated isaac-sim process that shares the GPU).
This is a separate authorization beyond the 40 of rounds 1-5; the task total
becomes 45.

Why. Round 5b showed c8 enters the success radius in 10 of 10 runs, tying c6
(ideal camera 15 deg down) and beating the 1.25 m baseline's 8 of 10, and fails
only by stopping late. The one condition that stops correctly, c6, owes its
advantage to seeing the near floor. The virtual camera's pitch is a free
parameter of the fusion inside the band the two real mounts cover
(-41.1 to +52.9 deg): a 63.5 deg VFOV virtual camera can be pitched to 9.4 deg
down before its bottom edge leaves the D435i band. At 9 deg the floor first
appears 0.46 m ahead, against 0.65 m level and 0.38 m for c6. C9 asks whether
that recovers c6's stopping behaviour with no hardware change.

Lead-side changes already made and statically reviewed (no fusion maths changed):

- `fused_camera_plugin.py`: the guard forcing a level virtual camera now forbids
  yaw and roll only. `Cam`, `head_lut`, `warp_d435` and `fuse` were already
  pose-general; whether the pitched frustum stays inside the covered band is
  gated empirically by the preflight bounds, not asserted in the plugin.
  `PLUGIN_VERSION` moves from `2026-09-11.1` to `2026-09-11.2` so the round-6
  preflight report and `OPUS_RETURN.md` cannot read as the rounds 5/5b plugin.
  A bytecode comparison against the round-5 `__pycache__` copy shows the guard
  condition, its message and the class docstring are the only changes, so the
  c7/c8 results remain reproducible under this plugin.
- `preflight_fused.py`: the flat-floor z-depth expectation now uses the general
  `h / (sin p + tan(theta_r) cos p)` form that `preflight_cam.py` has carried
  since round 1 for the pitched conditions C1/C4/C6. It is bit-identical at
  pitch 0, so the c7/c8 reports stay comparable. The level-only form it replaced
  would have reported C9's implied floor gap as 0.046 m instead of the 0.160 m
  every earlier condition measured: an error of 0.114 m that still falls inside
  the accepted [-0.05, 0.30] band, so it would have passed silently with a wrong
  number rather than failing loudly.
  `min_fraction_from_head` is now per condition (c7/c8 keep 0.7, c9 uses 0.55),
  because a downward virtual camera takes more of its image from the D435i.
- `conditions.json`: condition `c9_fused_down9`, identical to c8 except the
  `rgb_sensor` and `depth_sensor` orientation `[-0.15707963267948966, 0, 0]`
  (Habitat radians, positive up, so 9 deg down); `max_uncovered_fraction` 0.05;
  `execution.round6`; `max_runs` 45.
- `make_fused_yamls.py`: takes an optional condition filter and writes a
  pitch-aware header that stays byte-identical for level conditions. Verified:
  regenerating all three leaves the c7 and c8 YAML SHA-256 unchanged
  (`0cd67b9c...`, `8f9b6563...`), so no recorded `inputs.json` hash is orphaned.
- `test_fused_camera.py`: a third case with the virtual camera 9 deg down.
  Local run: SELF_TEST PASSED; c9 gives 3.05 pct uncovered, head 63.6 pct,
  d435 32.0 pct, head-region PSNR 31.0 dB, d435-region 34.6 dB,
  `virt_pitch_down_deg` 9.0.

Expected preflight numbers for c9: uncovered about 3 pct (the same harness gives
1.28 pct at 0 deg against the 1.2272 pct the c8 preflight measured in Habitat),
head fraction about 0.64, fusion cost close to c8's 226-244 ms (identical sensor
resolutions), implied floor gap near the 0.16 m every earlier condition reported.
A materially different uncovered fraction or floor gap is a finding: stop and
report rather than adjusting a bound.

R6-1. Sync Gate in for `REQ/` and `public_scenes/configs/vln_cam_c9_fused_down9.yaml`.
      From `work/InternNav`, `sha256sum -c ../../public_scenes/requests/2026-09-10_lite3_camera_ablation/authored_files.sha256`
      must report 27 OK.
R6-2. From the remote EXP root:
      `nohup bash public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/run_preflight_round6.sh c9_fused_down9 > public_scenes/requests/2026-09-10_lite3_camera_ablation/preflight/run_preflight_round6_stdout.txt 2>&1 &`
      Expected `ALL_STAGES_PASSED` over nine stages. If any stage fails, stop and
      report; do not relax a bound to get past it.
R6-3. `nohup bash public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round6.sh c9_fused_down9 > public_scenes/requests/2026-09-10_lite3_camera_ablation/matrix_driver_round6_stdout.txt 2>&1 &`
      Five supervised runs `cam_c9_fused_down9_v1..v5`. Do not touch
      `cam_c1..c8` run directories.
R6-4. Then steps 5-7 of round 5 over all runs (45 plus B0): `summarise_conditions.py`
      on the remote, `ffprobe_round3.py` LOCALLY after the return (the remote has
      no ffprobe), regenerate `manifest.sha256` on the remote excluding
      `__pycache__`, and return `cam_c9_*` run and supervisor directories plus
      `REQ/`. The return rsync must exclude lead-owned files:
      `--exclude review/ --exclude RESULT.md --exclude OPUS_EXECUTION_PACKAGE.md`
      (round 5 overwrote lead edits made while the executor was running; the rule
      is now in `.trellis/spec/backend/simulator-inference-evidence.md`).
      Append a "Round 6" section to `OPUS_RETURN.md`.
