# P2B Lead Execution And Qualification

This directory is lead-owned. It freezes inputs, verifies the runtime and keeps
independent execution evidence for the real PCT/SCAN/Isaac integration. The
backend and runner implementation packages are siblings; their unit tests are
not simulator acceptance.

## Inputs and provenance

Run `python3 freeze_inputs.py` from any directory to recreate the hash-checked
scene/map/configuration records using the read-only sibling artifacts. The
script refuses changed baselines or overwritten frozen pilot definitions.
`input_manifest.json` records every copied input and its exact original path.
Only the scene and tomogram bytes are ignored by explicit path; their local
VLA copies exist under `inputs/`. Historical metadata selects the pilot's start
and two target coordinates; actual routes must be newly computed from measured
pose. It is not a prerecorded-path controller.

The first pilot uses the level-1 flat platform, known geometric map and labelled
simulator-truth localization. The initial provisional 75-second simulation cap
was reduced to 45 seconds before any Isaac launch to retain the native
flat_nominal limit. The previous config and revision reason are preserved.
No acceptance geometry or stop threshold was relaxed.

## PCT native runtime

`inspect_pct_runtime.py` inspected the existing Humble image and verified the
wrapper plus native Python extension identities against the earlier qualified
baseline. `freeze_pct_runtime.py` returned ten native binaries/dependencies and
materialized pinned Python sources into `pct_runtime/`, with every hash and
origin tracked in `pct_runtime_manifest.json`. That path is local-only,
explicitly ignored, regenerable and hash-checked. Source and mixed-license
notices remain under the selected upstream acquisition; these exact binaries
are imported artifacts, not a claim that a new source build was performed.

`qualify_pct.py` ran real native optimized PCT on both pilot endpoints in the
isolated, hash-identified Humble image. Successful raw evidence:
`qualification/pct_20260916T145741Z/`. Both routes have ten native points and
endpoint errors of 0.04150 m and 0.04566 m. The second start in this compute-only
check is the first requested endpoint, not a measured robot pose. Returned
files match remote hashes. The earlier Python-path failure remains beside it.

## Locomotion identity

`qualify_v12.py` verifies the existing local VLA snapshot and all 217 runtime
files against the selected 5070 Ti execution copy. Successful evidence:
`qualification/v12_20260916T145351Z/`. An earlier SSH banner timeout is retained
in `v12_remote_match.json`; it is not a failed policy run. The checkpoint hash
also matches `a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450`.

## Actual controller and simulator qualification

`build_scan.py` builds a locally captured overlay in the fixed Foxy image.
`qualify_controller.py` drives the actual compiled controller with synthetic
ROS odometry and splines. Rejected scan_01 and scan_02 probe results are retained.
Accepted `builds/scan_03/controller_probe_03/result/` passes all six checks,
including protection against stale trajectory geometry and cancellation before
spline delivery. `builds/scan_03/install_identity.json` records a fresh source
comparison and the 380 installed-file hashes. This is a controller boundary
test, not robot movement.

### scan_04: terminal-acceleration fix candidate (task 09-16-scan-terminal-accel-fix-qualification)

`builds/scan_04/src` was materialized by the unchanged materializer (SHA-256
`69954316…`, same invocation as scan_03, recorded in
`builds/scan_04/materialize_record.json`). Before the fix it was byte-identical
to `scan_03/src`. `apply_scan_terminal_accel_fix.py scan_04` then changed
`planner_manager.cpp:171` from `evaluateAcc(t)` to `evaluateAcc(time)`. It
refuses a wrong base hash (`0c51df…`), a wrong line, a repeated application
and an already built tree. The result is in
`builds/scan_04/terminal_accel_fix_manifest.json`.
`compare_scan_trees.py builds/scan_03/src builds/scan_04/src --expect-one-line`
wrote `builds/scan_04/tree_compare_scan_03.json`: one file and one line differ,
and nothing else. scan_04 was built on 2026-09-17 (`build_result.json`, 74 s) and its install identity
captured (380 files; only `scan_planner_node` differs from scan_03).

**Accepted build since 2026-09-17 (Dr Sun):** pass `builds/scan_04` as `--accepted-scan-build-dir` (remote
`.../p2b/builds/scan_04`). Evidence: `../scan_fix_qualification/RESULT.md`. The native suite passed AC0-AC6.
Isaac passed 7/8 episodes (one-sided 95 % bound 0.529). Episode 3 failed the goal-B stillness check: the V12
policy stands on a zero command with no PD stance hold. A native replay shows the original build rejects the
resume plan at 6 of the 8 stops. Rollback: pass `builds/scan_03` again; nothing was overwritten.

Remaining steps, which need Dr Sun's approval of the run budget:

```sh
python3 build_scan.py scan_04
python3 capture_install_identity.py scan_04 --dry-run   # inspect first
python3 capture_install_identity.py scan_04
```

`capture_install_identity.py` hashes the remote `install/` tree over SSH. It
writes `install_identity.json` in scan_03's form only when the remote `src/`
matches `source_sha256.json`. Bytecode caches (`__pycache__/`, `*.pyc`) are
listed as excluded, not hashed; scan_03's identity contains none, although
compileall ran during its build. `--compare-existing scan_03` re-hashes a
recorded build and writes nothing, so the Isaac launch gate can be checked
against scan_03 before any episode. The capture code, the Isaac launch gate
(`../isaac_runner/run_two_goal_pilot.py`) and the local check all share one
hashing implementation.

The articulated stand qualification is stored in
`../isaac_runner/runs/stand_20260916T152235Z_p2b_fix1/`. Independent metrics and
video checks are in `qualification/stand_lead_review/`. The run covers 3.06
simulation seconds and a verified post-request stillness window without resets.

`review_two_goal.py` independently evaluates a returned continuous pilot:

```sh
python3 review_two_goal.py ../isaac_runner/two_goal_runs/RUN_ID \
  --output qualification/RUN_ID/lead_review.json
```

The checker correlates HTTP terminal records and PCT requests with the raw
physics clock, requested target coordinates, measured planning start poses and
continuous stop windows. It also verifies returned hashes, executed runner
identity, no-reset counters and contacts. Running the checker is required
before accepting any full-pilot success reported by the execution worker.

No physical robot interfaces are used. Formal language evaluation, actual
sensor-derived localization and physical deployment remain separate gates.
