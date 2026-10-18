# v238 — terminal-search starvation repair; partial offline qualification

v238 fixes the demonstrated unnecessary200 ms final-goal-neighborhood search
while a continuing reference route still offers forward progress. It changes
two native FSM files on the exact317-file v232 tree. Existing collision,
support, freshness, dynamic, publication, goal and stop rules remain active.
**The requested zero-hesitation acceptance is not yet met.** No new physics
was run, and cold native optimization still has slow/rejected calls.

## Verified results

- 12 native test programs /97 cases pass while loading the actual v238
  libscan_native_core.so. This includes controller/terminal/stop ownership,
  support, reference path, complete B-spline checks, and the v232 delayed-A*/
  zero-speed-endpoint/shared-environment-cost regression.
- 4 actual-map boundary checks pass: original new-route goal-neighbor search;
  no-forward-reference terminal recovery; stale evidence rejected without
  unnecessary geometric search; requested goal/admitted duration unchanged.
- 5 short-pause metric tests pass. Original v237 has two measured <0.05 m/s
  episodes of0.559692 /0.659637 s, cumulative1.219330 s;45–55 s has none.
-Parent317 source files and607 installed files remain byte-identical.
  The candidate317-file source and73 installed files are inventoried. The
  original polyline reference duration remains78.57439062570015 s.

| Same-input ordered replay | Frozen v232 | v238 |
|---|---:|---:|
| Approach sampled times | 91 | 91 |
| Approach goal-neighborhood searches | 88 | 0 |
| Approach maximum target-selection cost | 200.563 ms | 0.482 ms |
| Approach complete native planning successes | 88/91 | 88/91 |
| Approach planning calls >100 ms | 46 | 7 |
| Approach maximum complete planning call | 433.761 ms | 435.169 ms |
| Stair complete native planning successes | 50/50 | 50/50 |
| Stair planning calls >100 ms | 10 | 10 |

The actual-code regression requiring no unnecessary goal search fails on the
frozen parent and passes on v238.140 fresh target selections pass; the one
already-stale recorded snapshot is correctly rejected.138 accepted planning
outputs pass the unchanged final whole-curve check. Two fresh replay calls at
109.0017/109.0717 s still reject; their old remaining curves are clear, so a
failed nominal replan alone must not be reported as an emergency stop.

At the demonstrated first long-search trigger110.7708 s, v238 target selection
is0.349 ms and subsequent complete planning4.854 ms. At112.5198 s it also produces
a native-accepted curve. These are component replay results, not new motion.

## Claim boundary and remaining work

The fixture applies1,036 original published scans in order and checks141
recorded times with original snapshot cutoffs, actual published splines and
recorded warm eligibility/reference hint geometry. It does not reconstruct
exact DDS drains, asynchronous writer timing, growth-anchor history, a
continuously advancing clock, changed commands or resulting robot motion.
Consequently it cannot certify removal of physical STAND_SETTLING episodes.

Seven approach calls still exceed100 ms, and the frozen stale snapshot remains
stale. They are deliberately not filtered from acceptance. A continuous-clock
native replay must establish that remaining slow calls do not starve evidence
or force avoidable emergency stops before a new full-route trial is justified.
The accepted physical source/display baseline remains v232/v233.

See the [precise cause/timing bill](../../audits/2026-10-17_v237_terminal_approach/RESULTS.md),
[paired results](results/paired_summary.json),
[native regressions](results/native_regressions.json),
[source/install gate](results/sync_gate.json) and
[overall partial gate](results/offline_gate.json). No build caches or raw
point clouds are included locally. No new video exists for an offline replay.
