# P2B: Continuous Native Navigation Pilot

> Archive update, 2026-09-16: actual4 remains one accepted pilot. Three later
> display-condition runs failed at SCAN resubmission. The endpoint-derivative
> cause and isolated native candidate are verified; production adoption and a
> corrected Isaac episode remain pending. See [current archive](../../handoffs/2026-09-16_harnessvln_local_archive.md).

Date: 2026-09-16. Stage: experiment + analysis.

The root accepted one continuous Isaac Lab/Lite3 V12 episode using real native
PCT planning, the compiled Foxy SCAN planner/controller, and the new persistent
HTTP goal service. The sequence was goal A, cancel during motion, confirm
physical stillness, replan to A from measured pose, then reach goal B and stop.
There was no robot, map or policy-history reset between these goals.

This is a known-map, simulator-truth, approximately four-metre flat-platform
diagnostic. It is not a language-driven HarnessVLN reproduction, a benchmark
score, actual Cortex execution, a real SLAM test or physical robot deployment.

## Accepted result

Run: `two_goal_20260916T162236Z_p2b_actual4`.

| Measurement | Result |
|---|---|
| Actual simulation time | 16.52 s |
| Physics-loop wall time, excluding app startup and cleanup | 22.26 s |
| Continuous control records | 826 |
| Measured horizontal travel | 3.919 m |
| Cancellation trigger displacement | 0.419 m, against the declared 0.4 m trigger |
| Goal A XY error at confirmed stop | 0.179 m |
| Goal B XY error at confirmed stop | 0.154 m |
| Declared XY arrival tolerance | 0.25 m |
| Body-height errors at A / B | 0.046 / 0.039 m, within the 0.20 m tolerance |
| Independently checked stop windows | Each exceeds 1.0 simulation second |
| Resets / pose writes / pose injections | 0 / 0 / 0 |
| Maximum non-foot contact force | 0 N |
| Maximum roll / pitch magnitude | 3.74 / 4.60 degrees |
| Command observation error | 0 |
| Real model calls / physical robot commands | 0 / 0 |
| Returned raw artifacts | 34, all hashes matched |

Each of the three native PCT requests records the actual start pose, requested
target, map layer and returned waypoints. The replanning start after cancellation
differs from the corresponding physics record by only 0.12 mm; the other two
starts match those records exactly. Arrival is evaluated against the original
requested targets, rather than the grid-snapped PCT endpoints.

## Evidence and rerun

- [Independent acceptance](p2b_execution/qualification/actual4_lead_review/result.json)
- [Execution package and raw return](isaac_runner/two_goal_runs/two_goal_20260916T162236Z_p2b_actual4/)
- [Original video](isaac_runner/two_goal_runs/two_goal_20260916T162236Z_p2b_actual4/returned_artifacts/runner_output/third_person_master.mp4)
- [Video metadata](p2b_execution/qualification/actual4_lead_review/video_probe.json)
- [Detailed lead review](../../../.trellis/tasks/09-16-emos-harnessvln-reimplementation/research/P2B_LEAD_REVIEW.md)

The root decoded and inspected video frames. The original render is low
contrast; the video contains no added goal labels. Its 207 frames at 12.5 FPS
give 16.56 s playback; simulation duration is obtained from physics records.

Generate a fresh run ID with `isaac_runner/run_two_goal_pilot.py`. Its default
is prepare-only; execution requires the explicit execution flags and accepted
scan_03 workspace. The package fixes source hashes, runtime, checkpoint, scene,
tomogram, configs, local-only ports and ROS domain. The local repository remains
the source of truth. Root review uses `p2b_execution/review_two_goal.py` against
returned raw records. Execution ceilings remain 45 simulation / 1200 wall s.

## Implemented behavior and important corrections

The service submits typed, identity-bearing routes and cancels. A command gate
accepts only its active generation, monitors fresh state and controller traffic,
and requires a matching controller hold acknowledgement plus measured applied
zero/stillness evidence before release. A persistent asynchronous stop flow
avoids resetting that evidence window. The runner accepts a final request only
for its own run epoch and waits for physical stillness before termination.

The native PCT code runs in its own Python 3.10/Humble process. Foxy/Python 3.8
uses bounded TCP RPC. Native body-reference heights are recovered through the
optimizer; the wrapper's display-only +0.5 m offset is not sent to SCAN.
The original V12 policy, velocity limits and SCAN gains were retained.

The native C++ boundary was independently tested with actual ROS messages:
stale trajectory geometry, cancellation-before-spline, old generations and
matching controller hold receipts. Rejected scan_01/scan_02 and accepted
scan_03 results are retained. Frozen upstream and sibling sources were not edited.

The first full launch failed before physics on null route-length metadata.
The following 45-second attempt remained stationary because odometry did not
reach the new service. Both are retained as failures, with manual recovery
explicitly labelled where cleanup interrupted the original return manifest.

Two separate ROS transport defects were then verified and corrected:

1. The service odometry subscription must use the bridge's BEST_EFFORT sensor
   QoS. A real Foxy publisher/subscriber test passed after that change.
2. The split ROS containers require `--ipc=host` in this environment. A separate
   CPU experiment showed zero delivery with isolated IPC and fresh delivery
   with host IPC; both used effective domain 94 and localhost-only networking.

Final cleanup escalated unresponsive container processes to SIGKILL under the
bounded cleanup policy. It completed successfully and all four execution ports
were free. The successful motion result precedes this process shutdown.

## Remaining work

Pi currently has a separately tested fixture loop. Connecting that loop and
the Cortex-compatible tool layer to this real service remains open. Actual
RGB-D grounding, task decomposition, graph/event memory, backtracking, SLAM
localization and language-driven evaluation have not been implemented here.
Map invalidation/reconnect and sensor/model fault cases need integrated tests;
physical deployment needs sensor replay, receive-only checks and separately
authorized supervised trials. This one pilot does not establish general
navigation reliability or paper-level reproduction.
