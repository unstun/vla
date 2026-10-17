# v191 Mac attempt 01: interrupted applied-state transport

Stage: experiment + analysis. Execution date: 2026-10-14. **The authorized
attempt ran and failed near the start; full-route acceptance is false.**
The unchanged frozen Option B direct Nav2 + SCAN sources passed verification
(4,407 source/snapshot pairs and 618 runtime inputs) before launch.

`run_mac_full.py --task-root /private/tmp/vla_stop_audit_20261012 --attempt 1`
exited 1 after 70.908 s including initialization and teardown. Applied-state
sequence 143 received no ACK in three 100 ms receive attempts and raised
`zmq.error.Again`. The returned Linux state did not match the last acknowledged
sequence 142, so `state_copyback.verified` is false. The underlying delay cause
has not been established. No retry or source change was made.

`close_mac_trial.py` ran and preserved its interrupted outcome: the normal
analyzer could not find the unwritten final `result.json`. The supplemental
[partial metrics](results/v191_mac_full_attempt01/partial_metrics.json) read
original telemetry, video states, ROS observations and converged clock samples;
they do not manufacture a completed result or replace the frozen closeout.

| Measurement | Observed result |
|---|---|
| Completed navigation time | Unavailable; no arrival |
| Recorded navigation prefix | 2.841148 simulated s / 5.218612 wall s |
| Prefix RTF | 0.544426 |
| Last recorded physics time | 13.861972 s, including factory startup |
| Recorded poses | 280, beginning at actual physics time 0 |
| Final held XY / yaw error | Unavailable; no final hold |
| Last recorded XY / yaw error to requested goal | 11.496981 m / 0.375675 rad |
| PCT route / B-spline publications | 1 / 106 |
| Observed direct-command stops | 0 nonzero-to-zero transitions; initial zeros excluded |
| P2B measured-stop proofs / wait | Not applicable: this protocol was removed |
| State copyback | Failed verification |
| Raw retention | Completed, preserving the failed process status |

The prefix RTF ends at the last completed telemetry pacing sample; it excludes
the next failed ACK and teardown. Last recorded pose errors are not terminal
accuracy results. The recorder's historical `gated_command` event name now
contains direct `/quad_0/cmd_vel` Twist messages, not a gateway output.

v189 recorded 20 replacement stops and **34.225422 s** of cancel-to-proof wall
time (the requested 34.22 s reference), plus 2.290349 s from proof to replacement
route publication. These totals are recalculated from its frozen recovery
proofs. v191 stopped near the beginning and has no comparable full-route wait
measurement. Zero observed command stops does **not** establish a reduction in
stopping, better runtime, physical holding, or reliability.

Evidence: [closeout](results/v191_mac_full_attempt01/outcome.json),
[process](results/v191_mac_full_attempt01/execution.json),
[failed ACK](results/v191_mac_full_attempt01/applied_client_failure.json),
[copyback](results/v191_mac_full_attempt01/state_copyback.json), and
[reproducible prefix analyzer](results/v191_mac_full_attempt01/analyze_interrupted.py).

