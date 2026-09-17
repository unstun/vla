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
It waits for `current_command.json` to reach at least two simulation seconds,
writes a valid finish request, and lets the runner independently enforce the
stillness exit.

## Claim Boundary

These files validate source patch applicability, default-mode guardrails and
finish-request schema behavior with fake inputs. They do not run Isaac, ROS,
PCT, SCAN, V12 policy inference, the Foxy bridge, or a simulator episode.

If `qualify_stand_runner.py --execute` passes, the strongest claim is narrower:
the patched runner, V12 physics/policy runtime and real Foxy bridge transport
worked together in a stand-only, zero-command diagnostic simulator run. It is
not navigation, PCT/SCAN execution, goal replacement, or language control.

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

The full pilot worker starts one Foxy bridge, one Isaac runner, reads the
runner epoch from fresh `current_command.json`, then starts the Humble PCT
worker and the Foxy SCAN/controller/backend stack with that epoch. It does not
start a duplicate bridge. The pilot driver then posts goal-a attempt 1, cancels
once after at least 0.4 m measured displacement, requires explicit `cancelled`
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
