# v48 results: remaining-trajectory warm initialization

**Warm starting improved common-case latency but did not reduce the live tail or
reach 30 Hz.** The qualified gpu5070ti run measured local attempt frequency
**15.85853 Hz**, versus v47's 16.23180 Hz.
Median full-round time fell from 25.267 to
3.092 ms, while P95 remained near 126 ms and P99
increased. This is a separate live trajectory, not a paired replay of identical
live input states, so it does not isolate a causal frequency regression.

## Implemented change and preserved contracts

v48 implements audit Candidate 2 on the frozen v47 parent; Candidate 1's window
policy remains unchanged. The FSM supplies run/epoch/request/goal/route/command/
generation/map identity, exact final goal, and the same curve time used for
original start PVA. The manager accepts only its own last accepted curve, checks
clock/layout/PVA, refreshes inputs and validates the complete remaining cubic
against current native occupancy and stair support. Any target extension must
pass the existing collisionFreeSegment check.

The guess retains the accepted timing, receives a new hard-boundary-PVA fit and
runs the original optimizer, retiming, minimum-cruise, upper-dynamics, final-PVA
and newest full-curve checks. No old curve is restamped or republished. Invalid
reuse falls through to the original graph search; failed warm solving executes
the original graph and fixed-height recovery. Route regeneration, collision,
emergency, stale/invalid evidence and ownership changes invalidate reuse.

Only planner-manager/FSM header and implementation pairs change; the other 94
native files match v47. Final XYZ/yaw rules, tolerances (XY 0.25 m, yaw 0.25 rad,
Z 0.20 m), PVA/dynamic acceptance thresholds, terrain/collision implementation,
controller, physics, policy, sensing and all schedule settings retain parent
bytes. The exact versioned backend dependency is materialized before freeze;
the live status exposes the original navigation contract and actual 1 Hz global
refresh. No deadline, cross-callback cache or global-planner optimization was
introduced. See [inline review](INLINE_REVIEW.md) and [upstream pin](upstream_identity.json).

## Native component evidence

Final build02 and test02 pass: 34 native goal/timing/stop checks, 48 cache checks,
94 warm assertions across two recorded real-map fixtures, and exact cold v32/v33
geometry equality with the frozen parent oracle. Every accepted paired curve has
independent endpoint-PVA, dynamics and complete-curve assertions and a new native
trajectory ID. Invalid reuse falls back to a successful original graph solve;
invalid terminal PVA forces warm/graph rejection without publication.

Three alternating cold/warm pairs per fixture use identical source curve, input
PVA, target, map and fixed ROS clock. These are stopped-state component cases,
not the live tail distribution.

| Fixture | Cold median | Warm median | Warm-only accepts |
|---|---:|---:|---:|
| v33_stand | 11.712 ms | 3.083 ms | 3 / 3 |
| v32_stand | 10.611 ms | 2.999 ms | 3 / 3 |

Build01 used nominal arc-length timing; all six paired warm optimizers rejected
and fell back. The v33 warm-enabled median was about 56 ms. Build02 preserves the
accepted source timing and all six paired warm optimizations pass without graph
fallback. Both source candidates, build/test logs and hashes are retained.
The reviewed patch and materializer exactly reproduce the final 98-file native
source. No independent agent review occurred under the inline restriction.

## Qualified full-stack measurement

Run `v48_realtime_trial01` on gpu5070ti: the same historical Building profile,
single executor, 6-CPU native quota, original CPU physics graph, factory PD/stance,
ZMQ transport, LiDAR and target RTF 1 as v47 trial02. The observation is bounded
to 90 native seconds / 360 wall seconds. Recorded physics is
89.962 s; navigation pacing covers
78.941 native seconds and
82.851 wall seconds.

| Full-round measurement | v47 trial02 | v48 trial01 |
|---|---:|---:|
| Nominal attempt frequency | 16.232 Hz | 15.859 Hz |
| Successful completed-round rate | 16.227 Hz | 15.757 Hz |
| Completed / successful rounds | 1355 / 1355 | 1311 / 1303 |
| Mean / median solve time | 42.670 / 25.267 ms | 36.390 / 3.092 ms |
| P95 solve time | 126.051 ms | 126.496 ms |
| P99 solve time | 170.256 ms | 207.175 ms |
| Maximum solve time | 300.001 ms | 1090.481 ms |
| Solves over 33.333 ms | 518 | 440 |
| Skipped nominal slots | 1150 | 1169 |
| Measured path length | 22.732 m | 29.794 m |
| Low-speed fraction | 2.32% | 3.09% |

There are 1217 warm selections in completed rounds,
1207 warm-only accepts and 10
warm-to-graph fallbacks. Warm acceptance therefore occurs in about
92.07% of completed rounds.
3 rejection categories are recorded:
`{'identity_or_owner': 173, 'remaining_curve_not_clear': 1, 'target_connector': 4}`. Precheck median/P95 is
1.158/2.510 ms.

Warm-only rounds have median 2.755
ms but P95 113.338 ms, because
the full round includes target selection, input refresh and the complete solve.
The 94 rounds without warm acceptance
have median 97.529 ms,
P95 455.294 ms and maximum
1090.481 ms. Thus the
fast common case does not remove cold-path or callback/solve tail exposure.
No CPU profiler has isolated the contribution of every stage, and these groups
have different conditions; their differences are not causal estimates.

The native controller output measures
30.00053 Hz and published global
refresh starts 0.99997 Hz in the final bounded history. RTF is
0.952815, with zero dropped physics steps. The 1:1
pacing target also remains unmet. No measured low-speed pause exceeds one second
(XY speed <0.05 m/s, sensor intervals <0.5 s, nominal navigation interval,
simulation seconds). Final body XYZ is `[8.547382354736328, 0.8148956894874573, 2.587005853652954]`; maximum body Z
is 2.587 m. The job remains accepted at the recording bound,
with no arrival terminal or complete final-goal/PD-hold acceptance. Neither run
establishes complete Building arrival or arbitrary-scene stair safety.

## Source, return and reproduction

- Frozen source: 6442
  selected files, 98 native source files and 516 installed files; all source and
  snapshot bytes verified. Manifest SHA-256: fea5802d2d93c31f3e5cc835e111beab0297caad35979ff61c236750d7c7680d.
- All 909 original simulator artifacts (1,208,225,417 bytes)
  returned locally and passed SHA-256. Exact owned-container cleanup is confirmed.
  Original files remain under `../../runs/v48_realtime_trial01/`; the return
  manifest is `trials/attempt01/return_manifest.json`.
- Recompute with `python3 versions/v48/analyze_trial.py` from the experiment
  directory. Raw-source SHA values and per-round line intervals are in
  `analysis/metrics.json` and `analysis/v48_rounds.json`.
- `materialize.py --output <new-directory>` reproduces source from the pinned
  parent and reviewed patch; its default refuses to overwrite a frozen runtime.
- After syncing all frozen dependencies and the exact native installation to
  the execution copy, `remote_trial.py --attempt 2` owns a new bounded run and
  preserves this result. Verify live global_refresh/navigation_contract.

Candidate 2 is implemented and measured. Median latency improves, but the live
P95 tail is unchanged, P99/max worsen, and local frequency remains below 30 Hz.
No Candidate 3/4 change, training or hardware actuation was performed. v3 remains
the last accepted navigation condition. No automatic commit was made.
