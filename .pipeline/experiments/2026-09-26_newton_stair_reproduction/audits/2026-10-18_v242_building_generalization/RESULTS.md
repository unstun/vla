# v242 Building endpoint matrix — physical coverage gate failed

The frozen12-case matrix completed all60 fresh-process calls. **Only A02
passed5/5 PCT→GPMP→static-review→first-SCAN-publication chains.** The other
55 calls returned `Native PCT: pct_no_route` before GPMP/static service/SCAN.
No process failed in the60 scored calls. This does not establish general
endpoint coverage or physical locomotion performance.

The approved selection order admits only A02. The design explicitly stops
before physics when fewer than two eligible representatives exist. Therefore
**v243 was not frozen or physically run; new physical attempts/videos=0**.
The prepared entry rejects this failed selection. See
[delivery status](delivered/README.md). The completed v241 historical control
was reused and never rerun. Selected baseline remains v232/v233.

## Protocol and identity

- Local source of truth: this repository. Frozen
  [v242 manifest](../../versions/v242/manifest.json) and
  [requested cases](offline/cases_manifest.json) precede scored calls.
- Twelve unique pairs; five fresh native processes each, no scored replacement
  or retry. Discovery history, every request/path/verdict and all failures remain
  in the [returned evidence](offline/RETURN_MANIFEST.json).
- Actual installed v240 plugin/core and inherited native PCT. Parent gate
  rechecks317 source/282 overlay installed files plus the original v232 base.
  [Installed/source receipt](offline/native_identity.json).
- The original rebuilt admission probe and new adapter give byte-identical
  historical component routes: SHA256
  `3c30655acbc4e628f816f086a12470592590f11a234c2919a318a573540d37b9`.
  [Positive, stale and identity controls](offline/adapter_controls.json).
- Explicit case start yaw,0.3m body reference and original managed
  RouteSession inferred terminal tangent. Global benchmarking uses original
  static review; optional live feedback is unavailable before case observations.
- Each case has six own-pose original geometric LiDAR windows at0.1s cadence,
  paired body/sensor/cloud stamps and immutable captured state. Zero physics;
  nominal standing fixture, not measured factory/foot-contact qualification.
  All72 measured captures meet100ms; maximum22.194590ms. Original1000-frame
  policy golden passes (max error0.00595093, original limit0.01), exact model
  SHA unchanged. Radius/support0.35m and v237 deadline remain unchanged.
- ROS time is held at the case capture epoch for geometric component checks.
  Native steady-clock timings are measured; this batch does not test live
  callback scheduling or full-route feedback execution.

## Per-case results

SCAN rates below are conditional on admitted global routes; N/A is not a
failed optimizer attempt or an observed clearance. All five calls remain in
each global denominator. Detailed values are in [matrix_table.csv](offline/matrix_table.csv).

| Case | Direction | Global admission | First SCAN publication | Global median/max ms | SCAN median/max ms |
|---|---|---:|---:|---:|---:|
| A01 | ascent |0/5|N/A|0.982/1.005|N/A|
| A02 | ascent, oblique entry |5/5|5/5|457.778/482.698|14.720/14.866|
| A03 | ascent |0/5|N/A|0.993/1.032|N/A|
| A04 | ascent |0/5|N/A|4.000/4.262|N/A|
| G05 | ascent, hall destination |0/5|N/A|0.986/0.989|N/A|
| G06 | ascent, corridor destination |0/5|N/A|0.955/0.987|N/A|
| G07 | ascent, corner destination |0/5|N/A|3.988/4.017|N/A|
| B08 | boundary goal, ascent |0/5|N/A|0.947/1.039|N/A|
| B09 | boundary goal, same floor |0/5|N/A|0.956/1.178|N/A|
| R10 | descent |0/5|N/A|0.939/0.963|N/A|
| R11 | descent |0/5|N/A|131.427/131.737|N/A|
| R12 | descent |0/5|N/A|135.861/136.981|N/A|

Overall: global admission5/60; first-SCAN publication5/60 overall and5/5
conditional on global admission. First GPMP/static admission passes5/5 where
reached;55 calls never reach GPMP. No graph-fallback route is returned.
The small1ms failed calls are early failures, not a planning-speed improvement.
Map/field initialization and container-inclusive times are separately retained
per call; createPlan timings exclude plugin construction.

## Exact remaining rejection ledger

Post-score attribution uses a fresh actual installed PCT poseToIndex/Search
observer with the same ENV225, without smoothing or publication. These12
diagnostic graph searches are outside the60 scored calls and do not change
their inputs/results. [Native output](offline/endpoint_inspect02.txt).

| Cases | Scored rejections | Native graph evidence |
|---|---:|---|
| B08, B09, R10 |15|Goal costs31.984375,25,50 exceed original threshold20; direct goal rejection|
| A01, A03, G05, G06 |20|Search closes only the start state, then no path|
| A04, G07 |10|Search exhausts1232 states without reaching the goal|
| R11, R12 |10|Search exhausts46284/46290 states without reaching the goal|

All24 endpoints select the same native layer whether inspected with the body
input or the ground-height diagnostic control (downstairs0, upstairs7).
These records do not show a WrongHeight or GPMP-Z failure. A high start-cell
cost alone is not the rejection rule: A02 starts at cost50 yet reaches its
goal. The graph's actual expansion, rather than a blanket start-cost veto,
must be inspected next.

Both B cases stop before SCAN, so **required boundary neighborhood-search
coverage is unmet**. A02 performs one original new-route goal search per call;
that does not substitute for the B stratum.

## A02 margins and observation limits

All five successful calls produce the same geometric margins:

| Quantity | Result | Meaning |
|---|---:|---|
| Global extra edge margin, minimum |0.140384254m|ENV225; hard0.35m retained|
| Global original-PCD solid margin, minimum |0.098977983m|Independent static raw-cloud oracle|
| First local curve extra edge margin |>=0.15m|Positive score cap, not exact distance|
| First local observed non-terrain point margin |0.143858228m|Own case rays, native terrain classification and receive-range filtering|
| Raw cylinder-center observation |124/248 observed;124 unknown;0 outside|Not100% observed coverage|
| First published curve independent native status |Clear,5/5|Original live/unknown/body/publication rules retained|

The global route has3386 margin samples/call, all floor-known;3371 are at the
0.15m edge cap. Static raw PCD and case-observed LiDAR are separate sources.
Unknown center counts remain explicit even where the original native body
allowance admits the query. No threshold or unknown-space rule was changed.
All other cases' route/curve margins are N/A because global planning failed.

## Limits, storage and continuation

Actual destinations cover the inspected hall/corridor/corner geometry; distinct
room coverage is not established. A04's intended transverse-entry behavior is
untested because no route is returned; the exact requested yaw remains frozen.
Five repeated component passes are not five physical successes or a reliability
estimate. New-route pauses, stair/approach physical margins, terminal PD,
downstairs RL and full-route videos remain untested.

Only source/configuration and326 compact evidence files returned:10,869,254
bytes before the return-manifest file itself. Raw clouds/maps/archives and
CMake/Warp caches stay at
`gpu5070ti:/data/sun/vla_mppi_20261009/generalization_v242`.
Every returned file was size/SHA256 verified. No peer jobs were modified;
post-run Docker inventory is empty. [Host receipt](offline/host_after.json).

Two unscored harness startup failures (ROS log directory/domain) were repaired
before source freeze and retained. The first endpoint observer called the
native GetNeighbors stub; its empty counts are superseded and excluded from
this attribution. The final observer uses actual Search. These are evaluation
development records, not new controller-server crash claims.

Next work is PCT endpoint/graph reachability analysis and a reviewed follow-up
evaluation. Preserve this failed matrix; do not select replacement successes
after scoring or run the sole A02 case as the requested2–3case physical suite.
v243 preparation remains unfrozen and unqualified. No baseline promotion.
