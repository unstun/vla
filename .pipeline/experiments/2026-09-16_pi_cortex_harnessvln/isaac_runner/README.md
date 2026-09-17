# P2B Isaac Runner External Episode Patch

This directory owns a reproducible patch over the frozen Building runner:

`references/upstream/2026-09-16_lite3_isaac_harness_backend/source/machine-dog-nav/integration/lite3_sim_bridge/lite3_sim_bridge/run_pct_scan_building.py`

It does not edit the frozen reference in place. `materialize_runner_patch.py`
hash-checks that runner, applies exact source anchors to a copy, writes the
review patch, and records source hashes.

## CLI Contract

Legacy runner behavior is unchanged unless all external mode flags are used:

```bash
python -m lite3_sim_bridge.run_pct_scan_building \
  ...existing native arguments... \
  --external-goal-mode \
  --external-run-id p2b-two-goal-001 \
  --external-control-dir /run-specific/output/external_episode \
  --external-finish-stillness-seconds 1.0
```

`--external-goal-mode` disables only the old fixed-goal automatic
`GOAL_REACHED_AND_STOPPED` terminal condition. Timeouts, contact handling,
trial mutation checks, no-autoreset checks, command watchdog behavior and V12
policy/control paths remain unchanged.

The route artifact remains accepted for spawn and legacy metric metadata. In
external mode it is recorded as non-commanding metadata; the actual target
ownership belongs to the external PCT/SCAN backend.

`--stance-hold {off,auto}` (default `off`) selects the PD stance hold described
in "Stance Hold" below. With `off`, the step path is the runner's own
`previous_actions = actions` and no actuator gain is written.

## Shared Files

The runner atomically replaces:

`current_command.json`

Required fields include `run_id`, `run_epoch_ns`, `sim_step`, `sim_time_s`,
`wall_monotonic_ns`, applied/admitted/raw commands, command
sequence/stale/reason, same-step measured body pose, horizontal speed, yaw
rate, command observation error, state epoch, freshness limits, and
clock-domain provenance.

The backend writes once:

`finish_request.json`

```json
{
  "schema_version": 1,
  "run_id": "p2b-two-goal-001",
  "request_id": "backend-unique-id",
  "observed_run_epoch_ns": 1234567890,
  "requested_at_monotonic_ns": 9876543210,
  "backend_terminal_status": "FINISHED"
}
```

`request_id` is required and non-empty. `backend_terminal_status` may be
`FINISHED` or `FAILED`. The runner accepts and latches one request only when
`run_id` and `observed_run_epoch_ns` match the active runner and the request is
fresh on the same monotonic clock domain. The backend must not refresh the file
for dwell; after latch, freshness is no longer rechecked.

After accepting the request, the runner still waits for zero applied command
and measured stillness for `--external-finish-stillness-seconds` (the frozen
pilot uses 1.0 simulation second). It then exits
with `EXTERNAL_EPISODE_FINISHED` or `EXTERNAL_EPISODE_FAILED`. It does not
pretend the legacy route goal was reached.

## Commands

Materialize patch and hash records:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py --check
```

Write a patched copy for remote execution packaging:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py \
  --output /path/to/execution/copy/lite3_sim_bridge/run_pct_scan_building.py
```

Run local contract tests:

```bash
python3 -m unittest discover \
  -s .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner \
  -p 'test_*.py'
```

## Stand-Only Runner Qualification

Prepare a local-to-gpu5070ti stand-only run package without touching the remote:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/qualify_stand_runner.py \
  --run-id stand_YYYYMMDDTHHMMSSZ
```

This creates:

`isaac_runner/runs/RUN_ID/commands.json`

The parent can inspect the package, then execute the same callable entrypoint:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/qualify_stand_runner.py \
  --run-id stand_YYYYMMDDTHHMMSSZ \
  --execute
```

Defaults:

- remote root:
  `/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/runner_qualification/RUN_ID`
- TCP ports: telemetry `46240`, command `46241`
- `ROS_DOMAIN_ID=94`, `ROS_LOCALHOST_ONLY=1`
- Foxy image identity:
  `e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8`
- Isaac Python:
  `/home/sun/miniconda3/envs/isaaclab/bin/python`
- V12 runtime:
  `/home/sun/machine-dog-nav-runs/2026-09-08_new_building_lite3_dynamics/source/v12`
- runner Python environment: `source /home/sun/miniconda3/etc/profile.d/conda.sh`
  followed by `conda activate isaaclab`; runner `PYTHONPATH` explicitly starts
  with the materialized bridge, `<v12>/source/rsl_rl`, and
  `<v12>/source/robot_lab`.

The launcher refuses to overwrite an existing local run directory. In
`--execute` mode, the generated remote `mkdir` also refuses an existing remote
run directory before sync. The package records and syncs a source/environment
hash manifest. Before launch, the remote worker verifies the materialized
bridge package, frozen inputs, checkpoint hash, Foxy image identity, and all
217 expected files under the pinned V12 runtime path. It uses
`importlib.util.find_spec` to check `robot_lab` and `rsl_rl` top-level origins
without executing their modules before Isaac starts. The patched runner then
records and asserts the actual `sys.modules` origins after `AppLauncher` and
after the normal `robot_lab.tasks` / vendored `rsl_rl` imports. The remote
worker starts only the patched Isaac runner and the real Foxy bridge container;
it does not start SCAN, PCT, a motion publisher, or any hardware device path.
It waits for `current_command.json` to reach `--finish-after-sim-seconds`
(default 2), writes a valid finish request, and lets the runner independently
enforce the stillness exit.

Stand options (added 2026-09-17 for the stance-hold task): `--stance-hold
{off,auto}` (default `off`), `--duration-seconds` (default 8, at most 60) and
`--finish-after-sim-seconds` (default 2; it must leave 1 s of stillness plus
1 s of margin before the duration ends). All three are written to
`run_request.json`. `--execute` refuses a value that differs from the prepared
package, and a package without these keys counts as `off`, 8 s and 2 s. The
worker also checks that the runner summary reports the requested stance-hold
mode. The AC3 stand pair is:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/qualify_stand_runner.py \
  --run-id stand_YYYYMMDDTHHMMSSZ_hold_off --stance-hold off --duration-seconds 60 --finish-after-sim-seconds 58
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/qualify_stand_runner.py \
  --run-id stand_YYYYMMDDTHHMMSSZ_hold_auto --stance-hold auto --duration-seconds 60 --finish-after-sim-seconds 58
```

## Claim Boundary

These files validate source patch applicability, default-mode guardrails and
finish-request schema behavior with fake inputs. They do not run Isaac, ROS,
PCT, SCAN, V12 policy inference, the Foxy bridge, or a simulator episode.

If `qualify_stand_runner.py --execute` passes, the strongest claim is narrower:
the patched runner, V12 physics/policy runtime and real Foxy bridge transport
worked together in a stand-only, zero-command diagnostic simulator run. It is
not navigation, PCT/SCAN execution, goal replacement, or language control.

## Stance Hold

Task: `.trellis/tasks/09-17-isaac-runner-stance-hold` (design.md, implement.md).

- `stance_hold.py`: the state machine (RL, STAND_SETTLING, STAND_TRANSITION,
  FIXED_STAND, REJOIN). It is ported from the stand path of the machine-dog
  MuJoCo preview (`0_trials/2026-08-22/v17a28_mujoco_wasd`, commit `fd751b8b`)
  and uses only NumPy. The text between its body markers is inserted verbatim
  into the patched runner, which records the module SHA-256.
- `materialize_runner_patch.py` applies the external-episode anchors, then
  seven stance-hold anchors:
  - `stance_hold_module`: module body plus runner glue;
  - `cli_stance_hold`: the flag, default `off`;
  - `stand_probe_duration_cap_60s`: `stand_probe` may run 60 s, up from 45; no
    other case changes;
  - `stance_hold_setup`: after the foot ids are resolved;
  - `stance_hold_step`: replaces `previous_actions = actions`;
  - `stance_hold_metrics_row`: additive `metrics.jsonl` fields;
  - `stance_hold_summary`: the `summary.json` `stance_hold` block.

  `--check` verifies that the external-episode anchors alone still reproduce
  the executed runner (`e215a601...`) and that the patch has no duplicate
  top-level definitions.
- Off mode: setup only reads the action term, actuators, limits and PhysX
  gains into `runner_output/stance_hold_setup.json`. The step branch runs the
  original assignment, and rows gain `stance_hold`, `stance_mode: OFF` and the
  torque ratio and clip fields.
- Auto mode:
  - Setup fails closed unless all of these hold: the V12 `joint_pos` action
    term (scale 0.25, default-pose offset, a joint-order permutation); exactly
    the `Hip` and `Knee` `Lite3Actuator` groups at Kp 20 / Kd 0.5; zero PhysX
    drive gains; finite joint limits.
  - The robot joint order differs from the action order and is mapped through
    the term's `_joint_ids`.
  - The applied target goes to `wrapped.step` as `(target - offset) / scale`.
  - Kp/Kd are written to the actuator tensors only when they change, then read
    back, and PhysX gains are rechecked after the first write.
  - Non-finite input stops the case as `NONFINITE`.
- Delayed targets: `Lite3Actuator` delays position targets by 0-4 physics
  substeps. The lags are recorded at setup, while gains act at once. A gain
  change therefore meets the previous target for that many substeps. The row
  field `delayed_target_torque_max_ratio_estimate` bounds that torque.
- `analyze_stance_hold.py stand --on RUN --off RUN` gives the AC3 verdict and
  the hold-off baseline over the same window. `analyze_stance_hold.py run
  RUN...` gives AC5 and hold timing for any run.
  - Thresholds live in `stance_hold_thresholds.json`, frozen at SHA-256
    `fb8f9204c18e0b400ae2b7a2abc22bb052526538ff9713689759f15bff897c66`. A
    different file is refused.
  - Rows without stance fields are reported as "hold off / no stance fields".
  - AC3 also fails when the hold-on run has no `summary.json`, ended with a
    status other than `EXTERNAL_EPISODE_FINISHED` or `DURATION_REACHED`, or
    recorded a stance-hold failure.
- The walk review shows `stance: MODE` in the banner and shades non-RL modes
  on the time strip when `stance_mode` is present. Old runs render the same
  frames as before.
- Claim boundary: the local tests use fake Isaac objects and synthetic rows.
  An Isaac result, even a passing one, is simulation only: V12 in Isaac on one
  flat Building route. It is not a real-robot or deployment fix.

## Two-Goal P2B Pilot Prepared Package

Prepare the full two-goal package without launching physics:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/run_two_goal_pilot.py \
  --run-id two_goal_prelaunch_20260916Tlocal_p2b_r1 \
  --accepted-scan-build-dir .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/builds/scan_03 \
  --remote-scan-workspace /home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_03
```

This creates `isaac_runner/two_goal_runs/RUN_ID/commands.json` and defaults to
`execute=false`. Actual launch is guarded by both `--execute` and
`--lead-authorized-execute`, and it refuses to execute unless an accepted SCAN
workspace path and captured accepted SCAN build identity are present.

SCAN workspace hash gate (added 2026-09-16 for the scan_04 qualification).
When `--accepted-scan-build-dir` is given, `prepare` requires the build's
`source_sha256.json` and `install_identity.json`. It checks that the local
`src/` matches the manifest and that `--remote-scan-workspace` equals the
identity's `remote_workspace`, and it freezes these expectations in
`source_env_hashes.json` (`accepted_scan_build_identity.workspace_gate`). Every
check runs before a run directory is created. A build without an install
identity is refused unless `--allow-missing-install-identity` is passed; that
flag is recorded in `run_request.json`, and the remote gate then checks only
`src/`. Before any port, container or process is started, the remote worker
hashes the mounted workspace's complete `src/` and `install/` trees and refuses
on a missing, extra or changed file. Bytecode caches are listed, not hashed.
The comparison is returned as `artifacts/scan_workspace_gate.json`, and a
post-cleanup recheck as `scan_workspace_gate_after.json`. `--execute` refuses a
package prepared before this gate existed.

`--cancel-displacement-m` (default `0.40`, the previous fixed value) sets the
measured XY displacement that triggers the goal-a cancel. Values below 0.40 m
are refused because `p2b_execution/review_two_goal.py` checks an absolute
0.4 m. Values are also refused when the straight-line spawn-to-goal-A distance
from `inputs/pilot.json` (1.9998 m) minus the value is under 0.30 m, which caps
the value at 1.6998 m. By the triangle inequality this bound holds for any
route shape. The value and its check are recorded in `run_request.json`, the
remote command, the driver command and the `post_cancel` journal event.
Resource records: `artifacts/gpu_samples.jsonl` holds device-wide `nvidia-smi`
samples every 1 s; `result.json` holds `gpu_memory` (peak and first sample),
`remote_wall_seconds`, `started_utc` and `finished_utc`; and
`return_verdict.json` holds `host_wall_seconds` for each host command. With
default flags, `run_request.json` and `commands.json` match the actual4 package
except for these new fields and the explicit `--cancel-displacement-m 0.4`.
The launcher tests check this.

Package storage (added 2026-09-17, design 5.2). `prepare` hardlinks the frozen
`pct_runtime/` tree and `inputs/{building.usda,new_building.pickle,pilot.json,input_manifest.json}`
(27 files, 15.1 MB) and falls back to a copy when linking fails. Config files and
the bridge tree are still copied because the launcher rewrites them. A linked
file shares its inode with the frozen source, so never edit a package file in
place. The package manifest and remote gates are unchanged. The linked files
are also compared with the PCT runtime and input manifests.
`run_request.json` records the outcome as `package_storage`.

`--remote-only-bulk` (default off; requires Dr Sun's approval) leaves
`runner_output/clouds.jsonl` and `runner_output/third_person_master.mp4` on the
execution host. After the worker ends, `commands.json` `collect_sequence` runs:

1. `collect`: rsync that excludes those two files.
2. `remote_only_record`: hashes both files on the host and compares them with
   `artifact_hashes.json`, writing `remote_only_artifacts.json`.
3. `walk_review`: a guard first requires the worker's final `result.json`
   write, no cleanup errors and no live process group started by the worker
   (Isaac runner, bridge, PCT, backend), and records this in
   `walk_review/render_guard.json`. Only then does it render
   `walk_review/walk_review.mp4` with the packaged `make_walk_review.py`,
   using `h264_nvenc` with a `libx264` fallback. A local ssh timeout that
   leaves the worker running therefore never shares the GPU with Isaac.
4. `collect_extras`: returns the record and the walk review.

Local verification accepts exactly those two files as absent and still fails
on any other missing, extra or changed file. A missing walk review, or one
without a passing render guard, fails `--execute` after all evidence has been
collected; it is not a navigation result.

Review rule (task decision D9, Dr Sun 2026-09-17): `p2b_execution/review_two_goal.py`
accepts exactly those two files as absent when the returned
`remote_only_artifacts.json` has `all_match` true and hashes equal to
`artifact_hashes.json`. The other 40 checks are unchanged, and the full actual4
package still reviews 41/41. `review_two_goal.py` does not read the SCAN gate
records, so AC7 also needs `returned_artifacts/scan_workspace_gate.json` and
`scan_workspace_gate_after.json` with `passed` true. The worker exits nonzero
when the post-run recheck fails.

`--execute` on an existing package refuses a `--remote-only-bulk`,
`--cancel-displacement-m` or `--stance-hold` value that differs from the
prepared package. `--stance-hold` (default `off`) is passed to the runner and
recorded in `run_request.json`. A package without the key counts as `off`.

## Walk Review Video

`make_walk_review.py RUN --output OUT.mp4` builds one synchronized 1280x720
review video for a two-goal run (design 5.1). The layout is:

- the runner camera, 853x480, with a banner showing run ID, simulation time,
  phase and recent events;
- a top-down map with an equal-scale zoom on the cancel and stop points;
- a strip plotting measured speed, admitted command and non-foot force against
  simulation time.

Video frame i is paired with `camera_frames.jsonl` row i, and the robot state
comes from the `metrics.jsonl` row with the same step. Events come from the
`pilot_journal.json` driver events and backend `terminal_results`. They are
mapped to simulation time with the `review_two_goal.py` rule. Events more than
0.25 s after the last state row are listed, not drawn. Missing expected events
are shown as "event not recorded".

A frame-count difference of one is tolerated, and the sidecar names the rule
applied; a larger difference is refused. Encoders are `libx264` (CRF 30,
`-preset slow`), `h264_nvenc` or `h264_videotoolbox`; `--fallback-encoder`
names a second choice. Use `--video` for a remote-only original and
`--artifacts-dir RUN/artifacts` on the execution host. The JSON sidecar next
to the video records input hashes, frame alignment, events, encoder attempts
and output hash. The tool refuses to overwrite an existing output, and it is a
review aid, not an acceptance check. The actual4 prototype is 207 frames and
16.56 s long, 164 kB with libx264, and rendered in about 8 s on the Mac.

The full pilot worker starts one Foxy bridge, one Isaac runner, reads the
runner epoch from fresh `current_command.json`, then starts the Humble PCT
worker and the Foxy SCAN/controller/backend stack with that epoch. It does not
start a duplicate bridge. The pilot driver then posts goal-a attempt 1, cancels
once after at least the configured displacement (default 0.4 m), requires explicit `cancelled`
and post-cancel stop proof, posts goal-a attempt 2 and goal-b, and writes the
finish request only after two explicit `arrived` terminal records. Owner `None`
alone is logged but never treated as success.

Claim boundary if a later lead-authorized execution passes: known-map +
truth-pose diagnostic integration of patched Isaac runner, native V12 policy,
real Foxy bridge, real Humble PCT worker, real Foxy SCAN/controller,
backend_adapter and backend_ros. It is not actual LLM, Cortex, SLAM, formal
navigation benchmark evidence, or physical robot evidence.

Review note: `two_goal_prelaunch_20260916Tlocal_p2b_r1` is preserved as an old
prepare-only candidate. After lead review, the launcher source has been fixed
for native baseline caps, actual snapshot schema, stricter readiness, atomic
finish writes and backend shell/mount issues. Generate a new revision only after
the backend_ros async stop gate settles.
