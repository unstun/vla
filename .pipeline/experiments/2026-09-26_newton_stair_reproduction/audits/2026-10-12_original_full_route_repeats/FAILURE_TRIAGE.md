# Existing full-route failure triage, 2026-10-12

Stage: experiment + analysis. Dr Sun requested continuation of navigation work
and put the host-incident investigation aside. Frozen v147 remains unchanged.
This is source-verified inspection of preserved captures, not a reproduced cause.

| Attempt | Terminal | Last recorded revoke | FollowPath aborts | Longest low-speed interval |
|---|---|---|---:|---:|
| 02 | FAILED | scan_trajectory_missing | 7 | 26.685 s |
| 03 | FAILED | scan_safety_rejected | 7 | 10.894 s |
| 04 | FAILED | scan_trajectory_missing | 7 | 23.687 s |
| 08 | FINISHED | requested_goal_reached | 5 | 12.286 s |
| 09 | FAILED | scan_safety_rejected | 7 | 4.797 s |

The successful control08 also revokes for negative safety and stale evidence,
then recovers. Negative safety messages alone are therefore not an explanation
for the complete-route failures. Preserve the whole recovery sequence, including
all retries and the last state, when reconstructing a failing case.

## Directly checked source meanings

The actual v147 export files match the original native build receipt. In its
controller, missing initial trajectory beyond the original startup timeout
throws scan_trajectory_missing. Negative native safety remains latched through
stopping and is surfaced as scan_safety_rejected. The output log records those
triggers, but does not identify the exact map cell or full verdict lineage.

The A-star message "Ran out of pool" is emitted by Coord2Index when a coordinate
index is outside the allocated spatial grid. The optimizer initializes that
grid as 100 x 100 x 100. This message is not a failed memory allocation. It occurs
2,192 times in successful 08 and 1,726 times in failed 09, so its count does not
establish the failure cause. The report must not credit increasing the pool or
retry budget without reconstructing the actual failed query.

Attempt04 repeatedly reports the robot/initial control points in obstacles near
its final pause. Attempt02's final recovery proposals include rejected occupied
endpoints and failed seed searches. Attempt03 reports occupied targets and
endpoint/index failures near its final safety rejection. Attempt09's final
revoke is a negative safety decision while the robot was still moving; its
longest pause is much shorter than 02/04. These are different diagnostic fixtures.

Next replay priority is the latest failed 09 safety event and its original
published sensor/body/route history; retain successful 08 as a recovery control.
Then inspect the persistent blocked-start cases 02/04. Preserve all original
collision, support, freshness, owner and measured-stop gates. Do not simply
increase retry counts or relax collision thresholds.

## Validation and returned evidence

The lightweight analyzer ran only on gpu5070ti, at low CPU/I/O priority, without
GPU use, physics or navigation edits. It checked log hashes against the original
metrics and source hashes against the installed receipt. Detailed source snippets,
revocations and half-second pre-abort windows are in `triage/RESULT.json` and
per-run files. All 6 returned files (207,813 bytes) match the remote manifest in
`triage/return_verification.json`. Original raw data remains remote.

Executed analyzer SHA-256:
`ff1e179b1b6684c9272f3c284ed7137efbc63aa4cfc3a94104a2a85a88be1e58`.
Remote output: `/data/sun/vla_mppi_20261009/results/full_route_repeat_triage_20261012`.

The continuation launcher separately preserves the original 08/09 cohort prefix
and waits at most 600 seconds for admission before attempts10–13. Its 6 guard tests
pass on gpu5070ti: retain the failed prefix; reject changed prior output, changed
boot, omitted failure or existing remaining attempt; never launch on a busy host.
These guard tests do not count as simulator trials or navigation acceptance.
