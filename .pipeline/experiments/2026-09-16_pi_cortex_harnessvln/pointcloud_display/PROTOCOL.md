# Bounded Live Point-Cloud Display Probe

Date: 2026-09-16. Stage: experiment + analysis.

Dr Sun authorized a lightweight live display trial after asking whether point
cloud rendering could stall the computer. The target is the existing 5070 Ti
execution host. This does not test display performance on the local Mac.

## Change boundary

The existing P2B navigation package already publishes the live raw point cloud.
The missing behavior is an independently running viewer and measured evidence
of its resource/control-loop impact. New code lives under pointcloud_display/:
an observer configuration/runtime, a resource sampler, a small packaging wrapper
that reuses isaac_runner/run_two_goal_pilot.py, and analysis of the returned
artifacts. The wrapper may add observer start/stop hooks to its new generated
execution copy. The previously accepted package remains frozen.

Navigation source, checkpoint, sensor parameters, route requests, controller
limits, scene/map and stopping thresholds retain the actual4 settings. No
physical robot, model API call, perception-model integration or formal long
experiment is included. Raw and planner cloud inputs are not downsampled or
rewritten; only display settings are constrained.

## Pair and limits

Run one fresh baseline with the observer instrumentation but no RViz window,
then one matching run with the latest-only RViz point-cloud display. Each
retains the P2B 45 simulation-second / 1200 wall-second ceiling and the same
goal-A cancel/stop/resubmit then goal-B sequence. Source and input identities
must be frozen before each launch, and all returned bytes hash-checked.

The viewer uses /quad_0/cloud_raw, BEST_EFFORT keep-last depth 1, Points style,
Decay Time 0, no point selection and a 10 Hz drawing limit. It may show a grid
and current odometry for orientation. No cumulative dense/global cloud layer is
enabled. Any selected OpenGL backend and display/capture resolution must be
recorded before launch, not inferred from GPU activity.

## Evidence and acceptance

- Both runs must pass the existing independent P2B physics/goal/stop review.
- The live viewer must receive advancing stamped clouds and produce actual
  rendered point-cloud evidence; a successful process start is insufficient.
- Sample total GPU utilization/memory and host CPU/RAM at 1 Hz; also record
  available per-process information. Do not equate sampled host GPU memory
  with model allocation or assign unrelated load to the viewer.
- Compare physics-loop wall time / simulation time, control-loop median/p95/p99,
  deadline exceedances, command watchdog events, transport drops, resets,
  contacts and stopping/arrival results. Separate app startup/cleanup time.
- Report display/capture overhead together if recording runs only in the
  display condition; do not call that isolated RViz overhead.
- No OOM/crash/hang and completed navigation support a bounded successful trial.
  Report measured changes even when small; do not invent a speed-regression
  threshold or extrapolate this short, approximately 2,850-point case to dense
  accumulated maps, long runs or every computer.
- Decode and inspect delivered media, retain failed trials, and stop only owned
  processes/containers. Verify resource release and local artifact completeness.

Local VLA is the source of truth. Frozen upstream and sibling repositories are
read-only references. No automatic commit or task archival is part of this probe.

## GPU display amendment, before the GPU launch

After the initial software-rendered RViz condition, Dr Sun requested greater
GPU use. Preserve both initial conditions and add one bounded `rviz-gpu`
condition using NVIDIA hardware OpenGL and NVENC video encoding. Verify the
actual Ogre renderer string and encoded video; requesting GPU flags alone is
insufficient. Keep point count, 10 Hz display/capture rates, navigation inputs,
controller limits and physics duration ceiling unchanged. Do not introduce
artificial GPU load just to increase utilization.

The first OFF condition exposed a SCAN dynamic-feasibility rejection after
goal-A cancellation/resubmission, before any RViz display. Retain this failure
and the original complete-navigation acceptance criterion. Display operation
and sampled resource measurements can be reported separately, but they do not
turn a failed navigation trial into a passed end-to-end comparison.
