# v6: short continuation repaired; Building navigation remains unsuccessful

Stage: experiment + analysis. Date: 2026-09-27. Parent: frozen v5.

The captured 0.173953 m continuation now passes native target selection, search,
optimization, boundary PVA and full-curve collision checks. Both physical runs
publish a third moving spline ending at the exact frontier rejected in v5.
The complete Building goal is not reached. The successful component repair
must not be reported as full navigation acceptance.

## Confirmed cause and one change

The original native FSM and manager reject the captured short target twice
with identical outputs. Existing native queries classify its start, target and
entire straight segment as free. Four related 0.2 m guards prevented planning
from reaching the optimizer: neighbor admission, shorter-prefix admission,
final local-target admission, and the manager's close-goal guard.

v6 shares one manager predicate across those four sites. The explicit Building
mode requires at least one map resolution of horizontal translation and
different XY cells, using existing native map coordinates. The default keeps
the legacy finite-input 0.2 m rule. The Building map resolution is 0.05 m.
This follows the cell-aware distinction observed in pinned Nav2 Smac and adds
one full-resolution minimum to reject tiny cross-cell movements. Exact source
and license references are in `UPSTREAM.md` and `upstream_reference/`.

Only three native source files and the Building mode configuration change.
The pre-execution manifest freezes 94 selected source/configuration files.
Search, curve fitting, objective weights, terrain/obstacle decisions, full-curve
checks, endpoint PVA, dynamics, original route goal, PD/RL control and watchdogs
remain unchanged. The default empty-floor mode remains unchanged.

## Validation results

| Check | Recorded result |
|---|---|
| Native build | Pass, unchanged source bytes |
| Original native v5 rejection | Two identical failures on the captured 54-scan state |
| v6 default mode control | Same target and rejection as v5 |
| v6 enabled native continuation | Pass twice; same target, boundary PVA, complete curve and unchanged global goal |
| Repeat identity | All six native curve captures and complete diagnostic outputs identical |
| Negative inputs | Same position, sub-resolution, vertical-only, non-finite, explicit-mode out-of-map and stale-without-restamping all rejected |
| Original v3 recorded flat interval | 3 moving curves / 3 accepted plans with v6 default mode |
| Building attempt 01 | Incomplete: applied-state acknowledgment timeout at about 27.3 s; 3 moving curves observed |
| Building attempt 02 | Reaches 90,000 physics steps; no arrival; 3 moving curves observed |

The frozen diagnostic caller initially failed compilation because inspection
APIs require a mutable spline reference. The independently hashed qualified
caller uses a value copy, leaving the frozen production and diagnostic source
snapshots intact. See `REGRESSION_CALLER_NOTE.md`. This failed test attempt and
the audit setup failures are retained; they are not counted as passing runs.

## Physical outcomes

Attempt 01 has no completed `result.json` or driver result. Its final Linux
state is newer than the last received acknowledgment, so final byte identity
fails. The saved partial review records 0.3934 m net XY displacement and
0.8205 m accumulated XYZ motion through the last logged state. It cannot
establish complete command acknowledgment or final stopping/PD acceptance.

One unchanged repeat was run to obtain a complete bounded physical record.
Attempt 02 records:

- 90,000 steps and 89.9622 s of the original float solver clock;
- 0.4158 m net XY displacement and 0.8707 m accumulated XYZ motion;
- 4.6976 m remaining XY distance to the original goal;
- 3,899 positive original-state acknowledgments, no byte/command mismatch,
  and verified final Linux copyback;
- no fall under the declared `base_up_z >= 0.5` condition; minimum 0.8819,
  with visible body tilt in the video;
- final mode `STAND_SETTLING`, not `FIXED_STAND`; no final PD dwell acceptance.

The native planner exhausted its 1000-replan bound earlier. The backend still
had no navigation terminal result when the physical limit was reached, so no
driver terminal file exists. The existing complete-episode reviewers cannot
score that missing result. Their errors are retained. `bounded_review.json`
reports the available physical/interface evidence separately, without creating
a stand-in terminal file or claiming a successful run. Architectural collision
acceptance is not assessed.

## Next blocker and claim boundary

The third moving spline reaches the old rejected frontier at reference time
0.347905694. After it, native frontier candidates stay at or behind that
reference time; no later forward target passes local-target screening and no
new seed reaches optimization. Native queries report both `StaticObstacle`
and `UnknownSupport`, followed by the replan-limit stop. `FOLLOWUP.json`
retains the candidate coordinates, verdict examples and source hashes.

These verdicts do not prove that physical ground is absent or that the scene
is genuinely impassable. The next audit must trace the raw occupied contributors,
support cells and query heading at the rejected proposals using the recorded
cloud/body state. Inspect source-backed self/terrain filtering and consistent
heading calculation before proposing a v7 change. Keep observed obstacles and
unknown space blocked until the input/geometry cause is established. Separately
audit why the native failure did not become a backend terminal result.

The earlier live empty-floor startup failure is still open; a passing recorded
flat interval does not establish repeatable 12 m live execution. v3 remains the
last accepted single empty-floor trial. Original Isaac A4, strict physical
factory calibration, remote execution and hardware actuation remain outside
this result. The original Trellis task remains in progress.

## Video and reproduction

The ordinary local file is
`output/2026-09-27_lite3_versions/v6_building_test.mp4`: 1,124 original-state
frames, 89.92 s encoded duration, complete decode and frame/source hashes
verified. Representative frames show v6, the original Building and robot,
movement at the entrance, the tilted final stance, `STAND_SETTLING`, and the
not-arrived caption. No physics steps occur during rendering. Curve-message
counts include stationary holds. Encoded time is distinct from the solver clock.

Use the immutable run requests, qualified regression caller, native build
identities and `video_delivery.json` for reproduction. Re-running unchanged
code requires a fresh run ID. Derivative CMake objects and PNG frames have
path-specific local-only provenance; retain original source, states, logs and
delivered MP4. Do not edit a frozen version to incorporate the next repair.
