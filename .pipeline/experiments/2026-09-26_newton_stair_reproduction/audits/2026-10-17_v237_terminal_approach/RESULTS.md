# v237 terminal-approach attribution and v240 offline repair

The two physical interruptions are real. Their demonstrated trigger is stale
collision evidence after an avoidable 200 ms final-goal-neighborhood search,
followed by safety replan failure and an explicit emergency-stop Bspline.
This is distinct from curve expiry, final goal completion, or a warm-seed-only
rejection. v238 removes the avoidable goal search; real-clock testing then
exposes starvation inside optimizer-local A*. v240 delivers pending inputs
during search while preserving its map snapshot and original final admission.
The offline continuity gate passes. Improved physical motion remains untested.

## Original measured events

Source: unchanged v237 raw archive SHA-256
`fb4d1eab6dfaa92d3d485d8319b4cfa330003a8dd317b24cc76fbdd60f0d92f2`.
Clock mapping uses the original accepted clock samples and telemetry pacer;
latency.csv stores round-start ROS time, and its last field is warm_accepts.

| Event | First episode | Second episode |
|---|---:|---:|
| Preceding slow nominal round | 110.770751953 s; success; 204.453 ms | 112.279922485 s; success; 204.036 ms |
| Goal-neighborhood search portion | 200.026 ms | 200.077 ms |
| Failed nominal round(s) | 110.980636597 / 111.030609131 s | 112.519790649 s |
| Failure site | Target selection; no optimizer entered | Target selection; no optimizer entered |
| Cloud age at final failed target checks | ~0.3598 s | ~0.3598 s |
| Original allowed cloud age | 0.35 s | 0.35 s |
| Safety stop | Collision reported at remaining-curve time zero; immediate replan fails | Same; repeated safety transition also appears |
| Actual emergency Bspline ROS stamp | 111.040603638 s | 112.529785156 s |
| First telemetry STAND_SETTLING | 111.110565186 s | 112.609741211 s |
| First telemetry back in RL mode | 111.450378418 s | 113.149444580 s |
| Measured horizontal speed <0.05 m/s | 111.310455322–111.870147705 s | 112.869598389–113.529235840 s |
| Measured low-speed duration | 0.559692383 s | 0.659637451 s |

Both zero-command episodes remain fresh/active commands, not host command
timeout. STAND_SETTLING still gives joints to RL. Stance labels do not measure
physical stop duration. The two low-speed episodes total **1.219329834 s**,
separated by **0.999450684 s** of motion. Their cluster spans 2.218780518 s;
that span is not stopped time. The >=0.5 s count is 2, the >=1 s count is 0.
The 45–55 s control has neither >=0.5 s stops nor split cumulative hesitation.
Normal final zero-command/stance closure starts near117.307 s; the driver's
first arrived=true observation is122.184479 s. Those are different gates.

## Complete 109–114.5 s planning bill

There are110 completed nominal rounds, four failures and seven >100 ms rounds.

| Round start ROS s | Success | Total ms | Dominant attribution |
|---:|---:|---:|---|
| 109.071685791 | 0 | 70.774 | Warm target_connector rejected; native cold/prefix retries and dynamic refinement exhausted; optimizer22.035 + refine36.881 ms. Current valid curve continues. |
| 109.141647339 | 1 | 198.220 | Cold recovery; optimizer176.562 ms, seed18.264 ms. |
| 110.770751953 | 1 | 204.453 | Goal-neighborhood search200.026 ms. |
| 110.980636597 | 0 | 52.751 | Goal search50.512 ms, then stale target/fallback evidence. |
| 111.030609131 | 0 | 2.859 | Already-stale snapshot; target/fallback rejects all points. |
| 111.930114746 | 1 | 206.139 | Goal-neighborhood search199.292 ms. |
| 112.279922485 | 1 | 204.036 | Goal-neighborhood search200.077 ms. |
| 112.519790649 | 0 | 15.261 | Goal search12.769 ms crosses evidence limit; target/fallback fails. |
| 112.729675293 | 1 | 299.630 | Goal search196.792 ms + seed97.540 ms, prefix recovery succeeds. |
| 113.029510498 | 1 | 192.828 | Goal-neighborhood search187.195 ms. |
| 113.324348450 | 1 | 200.548 | Goal-neighborhood search195.296 ms. |

111.280471802 s is also successful (69.062 ms); it is not another failed
round. The configured planning horizon is3.5 m. The route-wide49 warm connector
rejections are neither49 failed rounds nor49 terminal-region failures.
The observer records only one PCT route for the entire run. These events do
not show a new GPMP/global-route replacement; the expensive searches here are
the native SCAN goal-neighborhood/local seed/optimizer paths.

## Initial v238 repair and fixed-clock verification

Only the FSM source/header change in [v238](../../versions/v238/RESULTS.md).
An active reference round first proposes a collision-free forward reference
frontier if the occupied final goal does not yet need neighborhood recovery.
The original local horizon, minimum translation, A*, seed edges, optimizer,
whole-curve sampling, publication lease/revision and terminal gates still
decide. New-route admission and no-forward-progress terminal recovery keep
the old neighborhood search. Already-stale evidence is rejected explicitly.

The offline fixture applies1,036 original published scans chronologically and
checks141 recorded times:50 stairs +91 approach. Final paired replay restores
actual published spline messages and recorded warm-seed eligibility/reference
hint geometry. Growth-anchor history, exact DDS batching, asynchronous map
completion order, continuous time and resulting physics are not reconstructed.

The regression asserts zero unnecessary goal-search calls on these continuing
rounds. It fails on the frozen baseline and passes on v238.140 fresh targets
pass; the one already-stale snapshot remains rejected.138 complete planning
calls pass their native final curve check; two fresh calls at109.0017/109.0717 s
still fail in this replay, with their old remaining curves clear. The candidate
also retains some >100 ms cold optimizer calls. **This is not a zero-hesitation
or sustained30 Hz qualification.** See the exact CSVs and v238 gate summary.

New audit metrics retain raw low-speed intervals, >=0.5 / >=1 s counts, maximum
single duration, cumulative low time and split clusters with motion gaps kept
separate. The1.1 s clustering gap is an explicit audit parameter, not a planner
or stopping threshold. Five metric regression tests pass.

Reproduce with prepare_replay.py, then replay.sh baseline/candidate using the
pinned v232 container and read-only parent install plus private v238 workspace.
Raw point clouds/build caches remain on5070Ti. No physics or video was generated;
the original v237 videos remain the physical evidence.

## Continuous-clock diagnosis and final v240 candidate

The supplementary reproduction advances ROS time while actual native planning,
safety and input callbacks share their original mutually exclusive lane. At
the long-goal-search trigger, baseline cloud age reaches0.363053s and an
emergency message is published; v238 avoids it. In the fuller due-message
window, however, v238 still publishes an emergency in each of two repeats.
One occurs with a fresh measured-body-aligned seed, cloud age0.352582s and
231.692ms optimizer-local A* work. This demonstrates remaining input starvation,
not merely disagreement between old body motion and a new candidate path.

v239 drains inputs every20ms and cancels searches when adopting new maps.
It removes emergency messages but has an active-curve expiry gap from
111.084140672 to111.268702043s, duration0.184561371s. It is rejected. Unioning
older curve lifetimes would hide expiry of the actual replacement curve.
Earlier attempts before all static consumers were rebuilt are excluded;
candidate_window03 and candidate_recorded02 are the valid v239 runs.

v240 keeps ordered delivery but holds its immutable search snapshot. Original
caller/final refresh and publication lease adopt completed maps. Evidence
still expires under the original0.35s source/0.1s body limits. No collision/
support guard, stop rule, output epoch or deadline is relaxed.

| Native real-clock evidence | Rounds | Success / normal curves | Emergency messages | Active-curve gaps |
|---|---:|---:|---:|---:|
| Frozen baseline approach |100|94|2|Not instrumented|
| v238 approach repeat1 |141|136|1|Not instrumented|
| v238 approach repeat2 |124|119|1|Not instrumented|
| v239 valid approach |126|103|0|1;0.184561s|
| v240 approach repeat1 |159|155|0|0|
| v240 approach repeat2 |157|151|0|0|
| v240 staircase control |298|298|0|0|

All approach runs use the same979-scan prefix digest and release486 original
body/56 sensor/56 cloud messages. Round counts vary with wall execution and
scheduling; these are not paired per-round rates or new physical trial counts.
Coverage bounds after once-only restoration are109.001724–114.5s and
45.001896–55s. Actual executor/input/writer time advances; body motion remains
the old v237 recording. No intermediate curve state is reset within the live
window. Initial mapping-window internals and DDS batching are not exact.

v240 also passes97 rebuilt native cases,4 boundary contracts,141 recorded
times,10 audit tests and two direct contracts. The DDS contract proves worker
delivery cannot change/freshen held evidence. The new-support negative proves
a completed invalid support update is adopted by final refresh/lease and
rejects a previously clear complete curve; restoring support restores clear
admission. This is a component test of actual final-admission primitives,
not a full manager optimization with an injected obstacle.

[v240 results and exact gates](../../versions/v240/RESULTS.md) qualify offline
native continuity. Physical speed/stance improvement, new route arrival/PD,
sustained30Hz and a new comparison video require a separately authorized
physical run. v232/v233 remains the selected baseline.

## Evidence retention note

An early supplementary trigger test reused remote baseline03/candidate03
names and overwrote their full-run stdout. Complete141-row CSVs had already
returned locally and were restored from verified copies. Original stdout hash
receipts are historical receipts, not current-file claims. Trigger results
are separately retained in results/live_trigger01 with an explicit
retention_note. Original v237 raw evidence is unchanged. Subsequent runs use
unique IDs and refuse existing outputs. Valid live v238/v239/v240 full logs
have separate remote path/size/hash receipts.
