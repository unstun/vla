# v5: height repair verified; complete navigation still fails

Stage: experiment + analysis. Date: 2026-09-27. Parent: v4.

v5 repairs the captured height-locked optimization failure. The same original
Building input now produces a collision-clear curve with its boundary PVA
retained, and the full native planner publishes a moving curve. The live
Building test also publishes two moving curves and moves the robot. Neither
the live Building route nor the new empty-floor trial reaches its goal.
Keep v3 as the last accepted single empty-floor trial, not as evidence of
general startup reliability or Building navigation.

## One versioned change

SCAN's existing XYZ gradient is exposed when `optimization.optimize_height`
is true. Both rebound and refinement honor the same flag. The default remains
false; only the Building configuration enables it. Original ground support,
height envelope, unknown-space rejection, endpoint PVA, dynamics, complete
curve checks, policy and PD gains are preserved. `manifest.json` freezes 81
source/configuration files before compilation. `native_changes.patch` records
the two changed C++ files; `UPSTREAM.md` records the existing implementations
used as references. No later production edit was folded into v5.

## Actual outcomes

| Test | Outcome |
|---|---|
| Native build | Pass; source unchanged; source/install hashes recorded |
| Frozen v4 seed | Fixed mode exactly reproduces old failure; enabled mode passes optimizer, hard boundary PVA and full curve collision checks |
| Complete Building replay | With original measured body twist: old build 0 moving curves; v5 1 moving curve |
| Recorded v3 flat replay | Both builds accept 3 moving curves in the same partial recorded interval |
| Eight existing obstacle fixtures | Native occupancy/search and path-edge verdicts match; unknown/stale negatives retained |
| `v5_empty_route01` | Fails before motion: no checked seed, 0 moving curves, `initial_heartbeat_missing`; final PD hold 3.80 s |
| `v5_building_route01` | 2 moving curves; accumulated navigation motion 0.5495 m, net XY displacement 0.2510 m; goal remains 4.8602 m away |
| Building continuation | Native replanning fails 1000 times and stops; later backend terminal is `odom_stale` |
| Building final control | Upright, no fall; PD FIXED_STAND held 17.6703 s; gains and motor mapping checks pass |

The Building trial contains 43.4877 s of continuous physics. Its full Building
review returns `passed=false`; the empty-route review also returns false.
Source identity, original-state continuity, command acknowledgment, unchanged
source timestamps, measured stopping and sensor-byte checks are recorded
separately from arrival failures. Architectural surface contacts are not scored
by the Building reviewer; no collision-free full-route claim is made.

`COMPONENT_RESULTS.md` documents the replay input-format correction and the
preserved unsuccessful test-launch/review attempts. These are not omitted from
the evidence. Replay success does not override either failed physical run.

## New blockers, separate from the height repair

The empty-floor failure occurs before optimization. Native search reports its
existing 0.2 s search bound, followed by no accepted seed. One captured query
also shows body-pose age 0.16 s against the existing 0.1 s known-footprint
freshness condition. This does not yet identify a single causal fix. Earlier
native empty runs 05/06 also failed with `initial_heartbeat_missing`; the
single successful v3 trial never established repeatable startup.

In Building, the final accepted curve ends at
`[-5.4441242103, 5.8432940231, 0.3953802942]`. The next repeatedly selected
frontier is `[-5.4429336310, 5.6733993235, 0.4327161548]`: only 0.173953 m away.
`scan_replan_fsm.cpp` takes the previous curve's terminal state for continued
planning, but `getLocalTarget()` rejects a segment shorter than 0.2 m. The
native log repeats this frontier 3000 times, then records its 1000-retry
emergency stop. This is a source-and-record-supported candidate for the
continuation stall; a minimized native reproduction is still required.

The later backend odometry timeout must not be reported as the sole cause of
the earlier planning stop. Body-pose messages were still observed near that
terminal; the backend receipt/processing path needs its own audit. Clock
rejections also occurred, but correlation alone does not establish the cause.

The next logical behavior repair belongs in v6. First reproduce the short
frontier handoff using this actual run, compare mature upstream handling, and
retain full collision/dynamics and original-goal checks. Audit live startup and
backend timing separately rather than enlarging freshness thresholds.

## Videos and preservation

Regular local MP4 files, each decoded in full and checked against original
state times and frame hashes:

- `output/2026-09-27_lite3_versions/v5_building_test.mp4`: 543 frames, 43.44 s.
- `output/2026-09-27_lite3_versions/v5_empty_test.mp4`: 185 frames, 14.80 s.

The Building clip starts with an exterior roof view, then follows the robot at
the staircase. Both videos visibly retain the failed terminal and final PD
state. Curve-message counts include stationary hold splines; there are only
two moving curves in Building and none in the empty run. Encoded duration is
distinct from the original solver clock and its startup sampling transition.
No physics steps occur during rendering.

`video_delivery.json`, `FOLLOWUP.json`, `LOCAL_ONLY_BYTES.json`, and `evidence/`
retain media checks, the next diagnostic lead, regenerable frame provenance,
build/replay/physical requests and results. Original run data remains under its
immutable run IDs. v3/v4 source snapshots and videos remain unchanged. The
original Isaac A4, strict physical factory calibration, remote execution and
hardware actuation are outside this result.
