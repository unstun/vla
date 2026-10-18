# v240 — native terminal-approach continuity gate passed

Two continuous-clock approach runs and the staircase control publish without
emergency messages or expired-active-curve gaps. The demonstrated input
starvation is repaired in native offline replay. Improved physical motion is
not yet tested; the selected single-route baseline remains v232/v233.

## Change and rejected intermediate candidate

v238 removes unnecessary final-goal-neighborhood A* from continuing admitted
reference rounds. Actual new-route and no-progress recovery retain that search.
Residual optimizer-local A* can still occupy the mutually exclusive work lane
long enough to starve the mapper of DDS inputs.

v239 drains existing inputs every20ms but adopts each completed map during
search, then cancels searches whose map changes. Its valid live run has zero
emergency messages but a0.184561371s expired-active-curve gap. It is rejected;
its source, valid runs and failure receipt remain preserved.

v240 changes three files on v239: GridMap header/implementation add a
non-adopting ordered drain, and A* calls it at the existing20ms polling point.
The writer receives actual pending paired scans while A* keeps its immutable
read snapshot. Stale held evidence still rejects under the original limit.
Synchronous revision/source/origin changes still cancel the search. Original
caller refresh and publication lease adopt and validate completed maps.
The200ms budget, old two-argument ABI, object layout and hard gates remain.

Cumulative native delta from v232 is five files: two FSM files from v238,
two GridMap files and one A* file. No new upstream acquisition or RL/action
interface change. The new support negative adapts existing local v81/v82 tests.

## Returned results

| Real-clock native run | Rounds | Success / normal splines | Emergency messages | Active-curve gaps |
|---|---:|---:|---:|---:|
| Approach109.001724–114.5s, repeat1 |159|155|0|0|
| Approach109.001724–114.5s, repeat2 |157|151|0|0|
| Stairs45.001896–55s |298|298|0|0|

Both approach runs use the same979-scan prefix/map digest and deliver486
original body messages,56 sensor poses and56 clouds. The stair control starts
from339 scans and delivers897 body/101 paired scans. Live logs prove actual
cloud/body delivery inside A*. Failed nominal replans retain the valid active
curve. Coverage respects replacement ownership: publishing a shorter curve
retires the old curve; unioning historical lifetimes must not hide expiry.

-12 rebuilt native programs /97 cases pass with zero failures/errors/skips.
  Static plan_env/path_searching/bspline_opt archives and their consumers are
  rebuilt; linked SCAN core, new/old ABI symbols and actual A* code verify.
  Tests include v232's delayed-A*/zero-speed/shared-environment-cost case.
-141 recorded times:50 stairs +91 approach.140 fresh target proposals pass,
  one originally stale input still rejects, zero unnecessary goal searches.
  All138 accepted curves pass native final checks. Two fresh optimizer
  rejections at109.0017/109.0717s remain in the bill; static replay is not motion.
-4 original-map contracts pass: new-route search, no-progress recovery,
  stale-input rejection and unchanged goal/reference duration.
-The DDS drain contract proves a queued original scan reaches the writer
  while held digest/revision/source stamp remain unchanged; queued input
  cannot freshen stale held evidence; default refresh adopts the new map.
-A separate support-change negative proves a complete cubic stays clear on
  the held map, then rejects after default refresh and publication lease
  adopt completed invalid support. Restoring original support restores clear
  admission. It tests native final-admission primitives, not the whole manager
  optimizer; the component clock is fixed.
-10 audit tests pass:5 pause tests and5 active-curve ownership tests. Original
  v237 measured episodes last0.559692/0.659637s, cumulative1.219330s; >=0.5s
  count2, >=1s count0. Motion gaps are excluded. Original45–55s has none.

## Identity, reproduction and limits

The [offline gate](results/offline_gate.json) verifies original317 native
source/607 installed files unchanged, plus the frozen v238 install and v239
source. It indexes317 candidate sources, installed bytes, actual linked
library, input stream/frames, full remote logs and returned XMLs. Bulk stays
on gpu5070ti under `/data/sun/vla_mppi_20261009/cooperative_search_v240`.
No build cache, CMakeFiles or raw cloud is returned locally.

Use prepare_candidate.py, build.sh and native_tests.sh in the pinned container
with read-only parent task and private v240 workspace mounts. Run the audit
replay.sh candidate with input05, REPLAY_LIVE_WINDOW=1 and distinct
REPLAY_RUN_ID values; add REPLAY_LIVE_STAIRS=1 for stairs. Use input02 without
live flags for recorded replay. Run publication_contract.sh separately, then
return_evidence.py and the audit unittest suite. Scripts refuse existing run
outputs; use new IDs when repeating, rather than replacing evidence.

RL SHA7030ba47…, ENV225 SHA7ec06542…, original endpoints,0.35m hard
collision/support,0.1s scans,0.35s source age,0.1s body age, dynamic/PVA/epoch,
whole-curve/publication/stop/terminal gates are unchanged. No physics is stepped.
Body follows the old v237 physical recording, not the new commands; initial
mapping completion history and original DDS batching are not exactly restored.
Changed speed, STAND_SETTLING, arrival/PD, sustained30Hz and a new video remain
unvalidated. No new physical trial or baseline promotion occurred.

[Precise original attribution and candidate history](../../audits/2026-10-17_v237_terminal_approach/RESULTS.md),
[live receipts](results/live_clock_summary.json),
[native cases](results/native_regressions.json),
[recorded replay](results/recorded_summary.json),
[new-map negative](results/publication_contract.json).
