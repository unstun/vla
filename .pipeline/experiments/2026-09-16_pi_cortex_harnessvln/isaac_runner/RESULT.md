# P2B Isaac Runner Result

Status: implementation package prepared locally and one authorized gpu5070ti
stand-only qualification passed.

Owned directory:

`.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/`

Artifacts:

- `materialize_runner_patch.py` - Python 3.8+ hash-gated materializer.
- `runner_external_episode.patch` - generated explicit patch over the frozen
  Building runner.
- `source_hashes.json` - source, patch and materializer SHA-256 records.
- `test_materialize_runner_patch.py` - local contract tests.
- `README.md` - CLI, file schema and claim boundary.
- `SNAPSHOT_SCHEMA.md` - current command and finish request schema for the
  backend-side stop confirmation.
- `qualify_stand_runner.py` - callable local-to-gpu5070ti stand-only
  launcher/collector; default mode prepares a package and `--execute` performs
  ssh/rsync/remote run/collection with pre-launch source/input/runtime hash
  gates, no-exec import-origin precheck, and failure-path artifact collection.
- `test_qualify_stand_runner.py` - dry-run package tests for the stand-only
  launcher.

The patch adds explicit external-goal mode with `current_command.json` evidence
and strict one-shot `finish_request.json` validation. Legacy mode remains the
default, and the fixed-goal automatic terminal condition is guarded so it is
disabled only in external-goal mode. A valid finish request is latched once;
the runner then waits on local zero-command and measured-stillness evidence
without requiring the backend to refresh the request during dwell. Safety
failure checks still run before external finish exit.

Validation commands:

```bash
python3 .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py --check
python3 -m unittest discover -s .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner -p 'test_*.py'
python3 -m py_compile .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_materialize_runner_patch.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/qualify_stand_runner.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_qualify_stand_runner.py
```

Observed local results:

- materializer source gate passed for runner SHA-256
  `1490dc85146ce7ea71f05c4f5520639da1a342a13e9dfcd8ce0ba04f21c8a76b`.
- generated patch SHA-256:
  `8a77868492614a332e49c5714be648f308e36602bb4453523a2e2b474bcb19ad`.
- patched runner SHA-256:
  `e215a6014bf15dc22a3261cb97c3435252b83ce2bde2f042375ae313493470f3`.
- materializer SHA-256:
  `849d5eccb20aea844be719582f819d7b62e66573cade77b36014acab86b67c08`.
- stand-only launcher SHA-256:
  `fa5e4a317b7f93a378cb52ab74d8bd8d079050cad3bf2ce4a48a95c8ac44f058`.
- stand-only launcher tests SHA-256:
  `4292e6ca0cec48c82fadb93d9dd1db80ceae1218b7a16a4b3d4c1e1850d31eaa`.
- unittest: 16 tests passed.
- py_compile: passed.
- stand-only launcher source hash gate: remote package verifies synced bridge
  files, frozen inputs, checkpoint hash, Foxy image identity, and 217 expected
  V12 runtime files before launching Isaac/Foxy. Prelaunch import-origin checks
  use no-exec `find_spec`; actual module origins are asserted and recorded by
  the patched runner after `AppLauncher` and normal imports.

Stand-only launcher claim if parent runs `--execute` and it passes:

- actual Isaac/V12 stand physics plus real Foxy/rclpy bridge transport;
- patched runner external finish/stillness path exercised with zero applied
  command after at least two simulation seconds;
- no SCAN, no PCT route execution, no motion publisher and no hardware devices;
- not evidence of navigation, cancellation/replacement, or full P2B goal pilot.

Limitations:

- No Isaac, ROS, PCT, SCAN, V12 policy, Foxy bridge or GPU runtime was executed
  by this package.
- Tests use fake finish requests and import the materialized runner only up to
  pure helper functions.
- The parent still needs to run the generated package on gpu5070ti, inspect
  returned logs/artifacts, and perform independent acceptance. Full P2B
  two-goal navigation remains outside this stand-only launcher.

Authorized stand-only gpu5070ti execution:

- run id: `stand_20260916T152235Z_p2b_fix1`
- local run directory:
  `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/runs/stand_20260916T152235Z_p2b_fix1`
- remote run directory:
  `/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/runner_qualification/stand_20260916T152235Z_p2b_fix1`
- return verdict: `returned_hashes_match=true`, `actual_count=24`,
  `expected_count=24`
- result: `passed=true`, runner exit code `0`, summary status
  `EXTERNAL_EPISODE_FINISHED`
- duration evidence: `sim_seconds=3.05999993160367`, `record_count=153`
- command evidence: `max_admitted_command_norm_mps=0.0`; final
  `current_command.json` has zero applied/admitted/raw command and
  `command_obs_error=0.0`
- finish evidence: finish request was written after the runner status reached
  at least two simulation seconds, then the runner latched it and exited with
  `final_reason=backend_terminal_and_measured_still`
- V12/Isaac import evidence: prelaunch no-exec specs and in-run actual imports
  both resolved to
  `/home/sun/machine-dog-nav-runs/2026-09-08_new_building_lite3_dynamics/source/v12/source/{robot_lab,rsl_rl}`
- contact evidence: native_v12 contact guard observed 153 control steps / 612
  physics substeps, `contact_detected=false`, `maximum_nonfoot_force_n=0.0`
- cleanup evidence after run: no listener on 46240/46241, ports reusable, and no
  `vla-p2b-stand-*` container/process remained.

Two-goal P2B pilot prepare-only package:

- launcher:
  `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/run_two_goal_pilot.py`
- tests:
  `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_run_two_goal_pilot.py`
- prepared run id: `two_goal_prelaunch_20260916Tlocal_p2b_r1`
- local prepared package:
  `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/two_goal_runs/two_goal_prelaunch_20260916Tlocal_p2b_r1`
- remote target encoded in commands:
  `/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/two_goal_pilot/two_goal_prelaunch_20260916Tlocal_p2b_r1`
- accepted SCAN workspace encoded for later lead-gated execution:
  `/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_03`
- actual execution status: not launched; package is prepare-only pending the
  backend ROS asynchronous stop integration gate.

The package records source/environment hashes for backend_ros, backend_adapter,
navigation_service, patched bridge, frozen PCT runtime, frozen V12 runtime and
checkpoint, frozen pilot inputs, and the captured local `scan_03` build
identity. The generated remote worker preserves failed raw logs and collects
returned artifact hashes in a `finally` path after the remote worker starts.

Validation commands observed after adding the two-goal package:

```bash
python3 -m unittest discover -s .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner -p 'test_*.py' -v
python3 -m py_compile .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/qualify_stand_runner.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/run_two_goal_pilot.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_materialize_runner_patch.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_qualify_stand_runner.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_run_two_goal_pilot.py
git diff --check -- .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner
```

Observed local results: 20 unittest tests passed; py_compile passed; git diff
whitespace check passed.

Two-goal pilot launcher review fixes after lead blocking review:

- Current launcher source fixed native pilot caps/profile back to the accepted
  baseline: `max_vx=1.0`, `max_vy=0.35`, `max_wz=1.0`,
  `max_horizontal_norm=1.0`, `speed_profile=speed_1p0`.
- The driver now reads the actual patched-runner snapshot schema:
  `applied_command` and `measured.horizontal_speed_mps`, with
  `measured.base_xyz`, `measured.base_quat_wxyz`, `measured.command_obs_error`,
  and fresh `wall_monotonic_ns` required.
- HTTP readiness no longer accepts a generic `state.ok`; it requires matching
  run id/epoch, body pose readiness, `measurement_body_pose`, a configured and
  ready applied snapshot, and a fresh matching runner snapshot.
- `finish_request.json` is written through a same-directory temporary file and
  atomic replace.
- The generated backend container script was changed from a composed `&&` chain
  to explicit multiline bash with `set -euo pipefail`, background PIDs, cleanup
  trap, `/workspace/install/setup.bash`, and controller `body_pose` remap.
- The backend container now mounts `/navigation_service:ro` so
  `backend_adapter.p2a_bridge.load_p2a_core()` resolves the accepted P2A core
  when backend_adapter is mounted at `/backend_adapter`.
- Generated planner/controller configs record `p2b_mode: true` under their ROS
  parameter blocks and document the P2B topic/remap contract.

The previous prepared directory
`isaac_runner/two_goal_runs/two_goal_prelaunch_20260916Tlocal_p2b_r1` is
preserved as an immutable superseded candidate and was not regenerated. A new
prepared revision should be generated only after the current backend_ros async
stop changes settle.

Post-fix CPU/source validation:

```bash
python3 - <<'PY'
import importlib.util, re, subprocess, tempfile
from pathlib import Path
script=Path('.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/run_two_goal_pilot.py')
spec=importlib.util.spec_from_file_location('run_two_goal_pilot', str(script))
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
src=m.remote_worker_source()
match=re.search(r'backend_script = """(.*?)"""\\.format\\(', src, re.S)
template=match.group(1)
rendered=template.format(ros_domain_id=94, run_id='dummy_run', run_epoch_ns=123, snapshot_path='/run/current_command.json', finish_request_path='/run/finish_request.json', pct_port=47631, http_port=8765)
assert '& &&' not in rendered
with tempfile.NamedTemporaryFile('w', delete=False) as f:
    f.write(rendered); tmp=f.name
assert subprocess.run(['bash','-n',tmp]).returncode == 0
PY
python3 -m unittest discover -s .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner -p 'test_*.py' -v
python3 -m py_compile .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/qualify_stand_runner.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/run_two_goal_pilot.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_materialize_runner_patch.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_qualify_stand_runner.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_run_two_goal_pilot.py
git diff --check -- .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner
```

Observed result: backend script `bash -n` exit `0`; 21 unittest tests passed;
py_compile passed; git diff whitespace check passed.

Current post-fix source hashes:

- `run_two_goal_pilot.py`:
  `ad821fae0a1eab1f4db408c0c24706bdcf70711695581f4a41e34e94b3da01ad`
- `test_run_two_goal_pilot.py`:
  `4214d73529677e322779f977890963a9293744a479b66a3f3a190beff1730822`

Actual full two-goal pilot attempts on gpu5070ti:

- `two_goal_20260916T155842Z_p2b_actual2` launched after the accepted CPU
  startup gate. It failed before any physics status snapshot or control step:
  `runner_output/runtime_error.json` reports `TypeError: float() argument must
  be a string or a real number, not 'NoneType'` while coercing
  `artifact["statistics"]["arc_length_xy_m"]`. Artifacts were manually
  collected under
  `two_goal_runs/two_goal_20260916T155842Z_p2b_actual2/returned_artifacts_manual/`.
  The code now computes a finite Euclidean XY route arc length over
  spawn -> goal A -> goal B, and the driver wait path detects runner runtime
  errors before waiting for a 600 second snapshot timeout.
- `two_goal_20260916T160655Z_p2b_actual3_retry1` launched once after the
  metadata fix. Isaac/V12 reached the bounded 45 second duration and recorded
  2250 control rows plus video, but the pilot did not issue any goal requests.
  The driver failed strict readiness because backend_ros never received a body
  pose/odom: `measurement_body_pose=null`, `body_pose_ready=false`, SCAN stayed
  in `INIT` with `no odom`, and backend service `event_seq` stayed `0` with no
  jobs. Lead independently identified the integration blocker as ROS QoS:
  bridge publishes BEST_EFFORT sensor odom while backend_ros subscribed with a
  RELIABLE depth setting. This attempt is failed integration evidence, not a
  navigation result.

Actual3 local returned artifacts:

- directory:
  `two_goal_runs/two_goal_20260916T160655Z_p2b_actual3_retry1/returned_artifacts_manual/`
- manual hash index:
  `manual_return_hashes.json`, SHA-256
  `bd3a012b222215cee64c31c16322e70b83ee042becf69707aeb0df51723c36db`
- manual collection report:
  `manual_collection_report.json`, SHA-256
  `88c4cd2c5cf1b39440cbbaac7a319b5a714da28941093b04b417a5b9e21e231d`
- runner summary:
  `runner_output/summary.json`, SHA-256
  `e735672526a012a41bcb5e6850ceb6400ba6ec1b2447cedc46608e4e8b990050`
- driver journal:
  `pilot_journal.json`, SHA-256
  `86b11329c9e316e402beb625112a8e3972f5faa36f85b0639d1efdc1f2cfe597`
- video:
  `runner_output/third_person_master.mp4`, SHA-256
  `201d66cd89938e3848cc536a484533927efb9a911de0fe244a5e71d4cfaae0da`

Actual3 observed runner summary facts:

- `status=DURATION_REACHED`, `termination_code=0`
- `sim_seconds=44.99999899417162`, `record_count=2250`
- `first_nonzero_command_s=null`, `max_admitted_command_norm_mps=0.0`
- `travel_xy_m=0.4314970637186304`
- `pose_write_attempts=0`, `reset_attempts=0`, `autoresets=0`
- native_v12 contact guard `failed=false`

Cleanup status after actual3 collection: no remaining process/container matched
`two_goal_20260916T160655Z_p2b_actual3_retry1`, port 47631, or port 8765 except
the transient inspection command itself. No further Isaac launch was performed
after the QoS blocker was identified; the next attempt is reserved for root
execution after the ROS BEST_EFFORT smoke gate.

Current full-pilot source hashes after the actual2 metadata fix and actual3
collection:

- `run_two_goal_pilot.py`:
  `74a8f973affb10b90312ffb6b3a4fde6d6e5b073c5fd92275542b45f7543bcaf`
- `test_run_two_goal_pilot.py`:
  `b5df3e23443efb1c3792c39b18796a5b14b01f07139dd81ee319cfedb4f3df94`
- `preflight_two_goal_cpu.py`:
  `df601cdf44a3057446df3462b41fef09d82c95a1e691728d854689c81003f9a3`

Source-only remote worker finalization fix after actual3 failure:

- Root observed that actual3's remote worker was interrupted inside unbounded
  `podman rm -f`, before `result.json` / `artifact_hashes.json` were written.
  The existing returned verdict therefore correctly fails hash verification;
  actual2 and actual3 evidence remains the manual post-failure collection, not
  a fabricated prior hash proof.
- `remote_worker.py` generated by `run_two_goal_pilot.py` now bounds each owned
  container cleanup with a 20 second timeout and records timeout/error details
  instead of blocking indefinitely.
- The remote worker writes `result.json` and `artifact_hashes.json` after owned
  process cleanup and again after container cleanup. Cleanup errors are carried
  in `process_cleanup`, `container_cleanup`, `cleanup_errors`,
  `post_cleanup_ports`, and `artifact_finalization` while preserving the
  original run failure in `error` / `error_type`.
- `wait_snapshot()` now accepts the actual runner process handle and fails fast
  with `runner_exited_before_snapshot` if Isaac exits before producing a valid
  snapshot, even when `runtime_error.json` was not written.
- No GPU, Isaac, ROS graph, or remote execution was launched for this fix.

Validation for this source-only fix:

```bash
python3 -m unittest discover -s .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner -p 'test_*.py' -v
python3 -m py_compile .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/materialize_runner_patch.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/qualify_stand_runner.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/preflight_two_goal_cpu.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/run_two_goal_pilot.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_materialize_runner_patch.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_qualify_stand_runner.py .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner/test_run_two_goal_pilot.py
git diff --check -- .pipeline/experiments/2026-09-16_pi_cortex_harnessvln/isaac_runner
```

Observed result: 23 unittest tests passed; py_compile passed; git diff
whitespace check passed. New tests include synthetic runner early-exit detection
and synthetic bounded podman cleanup timeout with successful result/hash file
writing.

Current source hashes after this source-only finalization fix:

- `run_two_goal_pilot.py`:
  `b76664ad2ac61b5bbcbeaa71fb87cedd7c1cab7b1bb8caea342d16cdd731003d`
- `test_run_two_goal_pilot.py`:
  `6d7cb57005b47d0df9235e59694ab3fd5ba765c3203c017827c8f29d400a0ed5`
