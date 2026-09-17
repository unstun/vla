# Native SCAN reboundReplan dynamics repro

This directory contains a minimal source-only reproduction package for the P2B
SCAN cancel/resubmit diagnosis. It builds a small ROS 2 executable that calls the
real `scan_planner::SCANPlannerManager::reboundReplan` implementation from the
accepted frozen `scan_03` source tree.

Boundary:

- No frozen `scan_03` source is edited or copied into this package.
- The build compiles `planner_manager.cpp` directly from a read-only scan_03
  source mount and links the real installed `bspline_opt`, `plan_env`,
  `path_searching`, and `traj_utils` libraries.
- The executable initializes the real `GridMap`, `BsplineOptimizer`, `AStar`,
  and `PlanningVisualization` objects, but it does not feed point clouds. Output
  labels this as `dynamics_only_empty_grid_no_clouds`.
- It is not a navigation or obstacle-avoidance reproduction. It is intended to
  isolate native polynomial initialization, B-spline optimization, time
  refinement, and dynamic feasibility behavior.

## Expected remote inputs

Parent/root should provide these read-only paths on gpu5070ti or an equivalent
Foxy environment:

- Accepted scan_03 build/source root:
  `/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_03`
- This package, synced from local source of truth:
  `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/native_repro/scan_replan_native_repro`
- Fixture cases:
  `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/inputs/cases.json`
- Planner params:
  `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/inputs/planner.yaml`

The node name is `scan_planner_node`, matching the YAML scope.

## Build recipe inside the Foxy image

The image used by prior P2B Foxy/SCAN work was:
`e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8`.
Use the accepted local tag if one exists; the ID is included here for identity.

Example commands, with paths adjusted by root for the immutable run directory:

```bash
RUN=/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/scan_replan_diagnosis/native_repro_run_YYYYMMDDTHHMMSSZ
SCAN03=/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/builds/scan_03
PKG=/path/to/synced/native_repro/scan_replan_native_repro
IMAGE=e4aa715467b93f20a9d9cdbb6a1dbd0d3c8c1e033e7792f2d889cba03db227d8
mkdir -p "$RUN/ws/src"
cp -a "$PKG" "$RUN/ws/src/scan_replan_native_repro"

podman run --rm \
  --network=none \
  -v "$RUN/ws:/ws:rw" \
  -v "$SCAN03:/scan_03:ro" \
  "$IMAGE" \
  bash -lc 'set -eo pipefail
    source /opt/ros/foxy/setup.bash
    source /scan_03/install/setup.bash
    cd /ws
    colcon build --packages-select scan_replan_native_repro \
      --cmake-args -DSCAN03_SOURCE_ROOT=/scan_03'
```

For a lead-generated isolated instrumentation copy, keep `SCAN03_SOURCE_ROOT`
pointing at the accepted scan_03 tree for headers and pass only the copied
manager source as an override:

```bash
colcon build --packages-select scan_replan_native_repro \
  --cmake-args \
    -DSCAN03_SOURCE_ROOT=/scan_03 \
    -DSCAN_MANAGER_CPP=/instrumented/planner_manager.cpp
```

If the environment's ROS setup scripts require unset-variable tolerance, keep
`set -u` disabled as shown.

## Single-case invocation

Run the executable directly so ROS args and repro args are unambiguous:

```bash
EXE=/ws/install/scan_replan_native_repro/lib/scan_replan_native_repro/rebound_replan_repro
PARAMS=/inputs/planner.yaml
"$EXE" \
  --start -1.1422168016433716,-4.4986572265625,1.864306926727295 \
  --start-vel 0,0,0 \
  --start-acc 0,0,0 \
  --target 0.354685032877039,-4.486811256408692,1.9105468749999985 \
  --target-vel 0,0,0 \
  --poly-init true \
  --random-poly false \
  --seed 0 \
  --samples 81 \
  --ros-args --params-file "$PARAMS"
```

The process returns `0` on `reboundReplan` success, `2` on native planner failure,
and `64` on CLI/setup errors.

## Batch fixture invocation

The Python wrapper uses only the standard library and reads the parent-provided
`cases.json`:

```bash
python3 /ws/src/scan_replan_native_repro/scripts/run_cases.py \
  --cases /inputs/cases.json \
  --params /inputs/planner.yaml \
  --executable /ws/install/scan_replan_native_repro/lib/scan_replan_native_repro/rebound_replan_repro \
  --samples 81
```

Use `--dry-run` to print exact commands without execution.

## Output fields to inspect

- `INPUT`: exact CLI vectors and flags.
- `MAP_CONDITION`: confirms empty-grid dynamics-only isolation.
- `PARAMETERS`: manager and optimizer limits loaded from `scan_planner_node` YAML.
- `NATIVE_FIRST_CALL_NOTE`: explains that a fresh native manager has a static
  `flag_first_call` path that forces polynomial initialization even if
  `--poly-init false` is passed.
- `POLY_INIT_DIAGNOSTICS`: mirrors the first-call polynomial sampling loop from
  `planner_manager.cpp`, including total polynomial time, final sampling step,
  last sampled `t`, and endpoint omission `total_time - last_sample_t`.
- `POLY_INIT_END_DERIVATIVES`: prints the four derivatives used by native
  B-spline parameterization, plus the true final polynomial acceleration for
  comparison.
- `REBOUND_REPLAN_RESULT`: direct native success/failure.
- On success, `SAMPLE` and `SUMMARY` print position, velocity, acceleration, and
  jerk diagnostics over the resulting native B-spline trajectory.

