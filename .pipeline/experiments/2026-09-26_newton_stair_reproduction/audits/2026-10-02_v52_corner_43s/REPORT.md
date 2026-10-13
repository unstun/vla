# v52 corner failure near 43 seconds

Stage: experiment + analysis. Run: `v52_realtime_trial02`.
Analysis of the frozen run and unchanged native v52 source; no navigation fix,
new version, timeout, stop-protocol or goal/yaw/PVA/safety change was made.

The failure begins at **42.353352 s**, while the previous accepted curve still
has **1.026282 s** remaining. A same-owner PCT route refresh clears both the
warm-start binding and the feasible-window hint, and selects a much longer
target across the corner. The native planner cannot admit a replacement.
Repeated searches consume the remaining curve time, and the controller later
publishes zero commands through its existing end-of-curve rule. Subsequent
recovery encounters a persistent, heading-dependent support-map rejection at
the front footprint. The first loss of continuation and the later inability to
restart are different parts of the same failure chain.

## Recorded timeline

All times below are simulation time; solve durations are measured wall time.

| Simulation time | Evidence | Consequence |
| --- | --- | --- |
| 42.108486–42.338360 s | Curves 854–862 retain the same endpoint and absolute end time, 43.379634 s. | These fast accepted warm starts trim the remaining curve; this interval adds no execution reserve. |
| 42.338360 s | Last successful nominal round: 1.408170 ms; trajectory 862 published. | Continuation is still accepted, with 1.041274 s duration. |
| Before the next nominal round | Native `scan.log` lines 31932–31936 show a regenerated reference frontier and PCT route callback. | Callback clears warm-start eligibility and the feasible window. |
| 42.353352 s | First persistent failed round: 455.376721 ms; four warm attempts reject `identity_or_owner`; four graph searches fail with status 2. | No replacement curve is published. No spline optimizer runs in this first failed round. |
| 42.853077 s | Next solve fails in 488.698514 ms, with 13 skipped nominal slots. | More curve reserve is consumed. |
| 43.347805 s | Another failure, 485.760648 ms, with 15 skipped slots. | The old curve reaches its end during recovery. |
| 43.379634 s | Trajectory 862's absolute curve end. | Finite continuation is exhausted. |
| 43.407772 s | First exactly zero tagged raw command; gated command is also zero. | This is consistent with the native controller's end-of-curve finish rule. |
| Round starting 43.847530 s | Worst recorded round: 711.404016 ms, seven seed calls and four optimizer calls. During it, at 44.347256 s, the native log records the initial spline collision query. | Recovery now also fails on the fixed initial segment and missing front-footprint support. |

Primary compact records are `corner_evidence.json`, `rounds.csv`, and
`timeline_identity.json`. The original `scan.log`, observer JSONL, applied JSONL
and point-cloud NPZs remain in the remote run archive.

## What the route refresh actually changes

The preceding route and refreshed route carry identical run, epoch, request,
goal, route, command, generation and map identity fields. This is not evidence
of a new command owner or cancellation. Geometry changes: the route start moves
from approximately `[6.654686, -4.386812, 1.860547]` to
`[7.354687, -4.286812, 1.860547]`, and its reference trajectory is regenerated.
The path still has 433 points. Its numerical final endpoint changes by about
4.745 micrometres, so identity equality alone is insufficient for an exact-goal
binding contract.

`planGlobalTrajByWaypoints()` unconditionally calls `invalidateWarmStart()` and
clears `feasible_window_.valid`. `invalidateWarmStart()` sets the accepted
trajectory ID to -1 and clears its context/map pointer. Consequently the live
`identity_or_owner` message means the accepted binding was cleared; it does not
establish that an external owner changed.

Before refresh the short local target is the existing curve endpoint:
`[7.492718412386, -4.249730183469, 1.854956340741]`. After refresh it becomes
`[8.565581255651, -1.352130701777, 2.263495774586]`, approximately 3.12 m from
the previous endpoint. Reference times such as 0.855816 and 3.5 belong to
different regenerated time parameterizations and must not be copied across
them as if they were the same coordinate system.

The unchanged-native replay separates state preservation from target validity:

| Probe | Result |
| --- | --- |
| Before refresh, same recorded curve/input, reconstructed preceding feasible hint | Both full native rounds succeed through warm start. |
| Apply captured refresh before the nominal failure, restoring the observed native order | Accepted warm ID becomes -1, window becomes invalid; both full rounds fail. Start PVA and selected long target match the captured boundary. |
| After refresh, diagnostically restore compatible binding and request the long target | Warm seed rejects `target_connector`. Restoring only eligibility does not solve the target problem. |
| Same post-refresh inputs and diagnostic binding, request the old endpoint | Warm seed accepts eight nodes, including the unchanged full remaining-curve collision/support check. This is seed/continuation evidence, not proof of progress around the corner. |

The preceding hint's growth anchor is reconstructed for the pre-refresh probe;
it is not a fully captured live internal state. Binding restoration is a
diagnostic counterfactual, including binding to that case's exact final goal.
No such policy was installed in a live planner.

## Why recovery remains stuck at the corner

At the later native initial-collision query:

- Planned start is the expired curve endpoint
  `[7.49271841, -4.24973018, 1.85495634]`, with zero velocity and acceleration.
- Measured body is `[7.56760883, -4.17841291, 1.84793353]`.
- The 3D offset is 0.103653 m, XY offset 0.103415 m. The body is ahead of the
  planned endpoint in X/Y.
- Measured yaw is 0.267710 rad (15.3 degrees); the recorded spline collision
  query uses 0.736197 rad (42.2 degrees).

The native footprint uses radius 0.35 m and two centers offset by ±0.18 m along
query heading. At the planned start and recorded 42.2-degree query heading:

| Query | Native result |
| --- | --- |
| Body support | Free |
| Front center `[7.62610337, -4.12886475, 1.85495634]` | Support association fails. Its accepted support map has elevations 0.058030 m and 6.080675 m, with no layer near the required 1.554956 m. |
| Rear center `[7.35933345, -4.37059561, 1.85495634]` | Valid supported layer near 1.560884 m; free. |
| Measured body substituted, same query yaw | Front support still fails. The 10 cm start offset alone does not explain or remove the rejection. |

At both planned footprint centers, the retained raw contributors in this probe
are classified as free. The front rejection occurs in support association,
before the final obstacle verdict. An inflated voxel by itself is therefore
not evidence of a physical wall here. The fixed-height recovery also cannot
create a missing floor layer or change the front query's XY cell.

The source of the omission is visible in the native floor-fill inputs. The
navigation ground lacks this floor, but the surface evidence contains a floor
at **1.558031 m** in the front cell. The existing v34 guarded floor-fill rule
refuses to add it because neighboring evidence cells within its 0.35 m
cell-square guard have no corresponding level and contain lower ground. Two
recorded examples are `[7.45468531, -3.68681145]` and
`[7.55468531, -3.68681145]`, each with evidence near 0.058 m and 6.075 m.

Read-only vertical intersection with the pinned static building mesh finds a
horizontal surface at **1.558030 m** beneath the rejected front query, and
surfaces near 1.560884 m and 1.583030 m at the two guard-neighbor centers. This
establishes a mismatch between physical surface geometry and the selected PCT
support evidence at these coordinates. It does **not** establish clearance of
the entire footprint or authorize removing the drop guard. There are other
building surfaces at these XY coordinates; full geometry and sensor admission
remain required. The exact upstream PCT selection reason at those neighbors
was not localized: the dense-generation intermediate products are absent from
this execution copy. See `mesh_probe_result.json` for exact mesh face IDs.

## Input freshness amplifies the failed search chain

The first live failure tries prefix times 1.75, 0.875 and 0.4375 on the new
reference. The 1.75 target passes its endpoint check but fails full graph
search. The two shorter targets return `occ=1` and are skipped. Their live
per-query rejection subtype was not logged.

In the fixed-clock reconstruction those same short endpoints are clear. The
original log records cloud stamp 42.308 s during the second search; the next
refresh reports cloud age **0.2699 s before draining queued inputs**. Native
`reactive_cloud_max_age` is **0.25 s**. Prefix endpoint checks occur between
that search and the next refresh, without a fresh-input drain at that boundary.

This strongly supports freshness as an additional cause of the live skips.
The native predicate probe isolates it using the recorded rounded cloud stamp,
unchanged terrain support and a free obstacle: advancing query time from
42.553242 to 42.578228 s crosses the 250 ms freshness threshold: both targets
change from **Free (0)** at 245.242 ms age to **StaleInput (4)** at 270.228 ms.
The verdict is recorded in `result.json`. This proves how these queries reject on
age alone; it does not retroactively supply a missing live per-query verdict.
Refreshing inputs before a recovery check and relaxing freshness are different
operations. Only the former is a possible safety-preserving investigation.

## Why this prevents 30 Hz

The first failed round occupies 13.66 periods of a 30 Hz planner; the worst
round occupies 21.34 periods. Their inclusive profiles are:

| Recorded round | Total wall ms | Target selection ms | Seed ms / calls | Optimizer ms / calls | Cloud processing ms / calls |
| --- | ---: | ---: | ---: | ---: | ---: |
| Last accepted, 42.338 s | 1.408 | 0.748 | 0.375 / 1 | 0.022 / 1 | 0 / 0 |
| First persistent failure, 42.353 s | 455.377 | 110.758 | 310.781 / 4 | 0 / 0 | 133.265 / 4 |
| Worst, starting 43.848 s | 711.404 | 32.412 | 414.063 / 7 | 201.707 / 4 | 185.392 / 6 |

Profile scopes overlap and must not be summed. The first failure's warm checks
take only 0.001213 ms in total because they reject immediately; the expensive
work is repeated native search and input processing. Later optimizer work is
additional failed recovery. Matching CPU and wall measurements in the original
run support CPU computation as the cost, rather than GPU rendering as the
explanation for these solve durations.

For the original whole navigation window, attempted planning is 11.538 Hz and
successful completion is 10.190 Hz, while raw controller publication remains
approximately 30 Hz. The frequency setting schedules attempts; it cannot make
a synchronous 455–711 ms failed chain finish in 33.3 ms. Fast warm-start
statistics also do not prove that accepted curves extend execution reserve.

## Stop behavior and excluded explanations

The focused 39–47 s applied capture contains 400 rows, all with reason `active`.
Raw, admitted and applied commands agree in the retained samples. Tagged raw
and gated commands are both zero at 43.407772 s. There are no emergency-state
transitions in the original run. The controller's native finish rule emits zero
after its execution time reaches curve duration and XY error is below 0.15 m;
the later XY error is about 0.103 m. These observations support ordinary curve
completion as the stop mechanism. Curve expiry follows the first failed solve;
it is not its initial cause. No v49 deadline or altered stop protocol is involved.

## Verification, limits, and next repair boundary

The diagnostic harness builds against the unchanged frozen native source and
libraries. It reproduces pre-refresh success, post-refresh failure and later
initial-segment failure twice each. Four fixed-input snapshots distinguish
route, mid-search inputs, and exact later recorded body pose. Native source
hashes and returned result hashes are verified. The raw capture archive hash is
`e874a8ddccad2057e29ae997ed565dc6b0363cdef5163d7fe1e9f99c5a53d8e6`;
static mesh hash is
`e55e4a9507441b8f1788503f909505a49b63d6eb36f6882ba782aee7c38a5d39`.

Replay needs one explicit observer-order correction: its route receipt is
5.724685 ms after the nominal start, while native `scan.log` proves that the
callback completed before start. It retains other observer input order and
uses fixed clock per snapshot. It does not reproduce live DDS batching,
mid-solve clock/input progression, every optimizer seed, or the original
455/711 ms timings. Another GPU job was present during offline diagnosis;
replay timings are functional diagnostic measurements, not an uncontended
performance comparison or a new physical acceptance result.

The next behavior changes should be separate, reviewable integer versions:

1. Revalidate remaining trajectory and reproject a feasible target in world
   geometry across compatible reference refreshes. Preserve exact final-goal,
   ownership, PVA and full native admission; do not copy old reference times or
   merely force the new long connector through a safety check.
2. Verify fresh queued input before recovery target admission while retaining
   the existing freshness limit. A boundary regression should distinguish a
   genuinely blocked target from an otherwise clear target rejected on age.
3. Trace/correct the selected support evidence at this corner, or find a path
   that satisfies its unchanged footprint and drop contracts. Keep true-drop,
   multi-floor association, unknown-space, obstacle and whole-curve negative
   fixtures. A mesh point intersection is insufficient acceptance evidence.

The first two preserve continuity and avoid needless cold work; the third
addresses the geometric reason later continuation cannot be admitted. None
requires a hard timeout or a stop-protocol change. Sustained physical 30 Hz and
progress around the corner still require a future authorized version/run.

## Storage and regeneration

Remote root:
`/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-02_v52_corner_43s`.
Raw capture, 59.65 MB converted event stream, build products and full diagnostic
logs stay on gpu5070ti. Only source, compact reports/hashes and this static
figure return locally. Failed converter attempt01 and diagnostic attempts are
retained remotely. Earlier compact attempt02/03/04 results remain separate.

On gpu5070ti, `trace_corner.py` reads the original archive and `summarize.py`
produces `corner_evidence.json`. `prepare_replay.py`, `inside.sh`,
`CMakeLists.txt` and `corner_replay.cpp` define the offline replay;
`remote_replay.py` records mounts, image ID, external diagnostic supervisor
bound, source identity and artifact hashes. Use a new attempt directory for any
rerun, preserving old evidence. `mesh_probe.py` reads the pinned mesh.
Locally, `plot_corner.py` regenerates `corner_diagnosis.png/pdf` from compact
evidence. See `verification.json` for final local return checks.
