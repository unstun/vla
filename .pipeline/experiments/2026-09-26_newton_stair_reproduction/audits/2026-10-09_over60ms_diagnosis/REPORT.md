# Recorded local-planning rounds above 60 ms

Date: 2026-10-09. Stage: experiment + analysis.

The six latency spikes are dominated by CPU work inside path initialization,
collision recovery, or target search. Several failed candidates are also tried
synchronously within one complete planning round. The three largest spikes
contain a single failed A* search lasting 111–137 ms. They are not explained
primarily by waiting for the OS or by inline map construction.

This is a retrospective audit of `v116_mac_trial01_attempt02`, using unchanged
native **v114**. That navigation run ended **FAILED**. It is distinct from the
earlier successful v114 trial. No planner, safety threshold, frozen version,
or runtime was changed, and no new physical trial was launched.

## Six cases

All 900 original round starts/results match the latency CSV and delivered HTML
data. Six rounds (0.667%) exceed 60 ms. Times below are elapsed video positions,
not ROS timestamps. "Attempts" counts native rebound planning attempts; a
target search can consume time before any such attempt starts.

| Round | Video s | Complete ms | Attempts | Dominant stage: wall / thread CPU ms | Recorded trigger and outcome |
|---|---:|---:|---:|---|---|
| 1 | 1.285 | 65.739 | 5 | Optimizer: 57.183 / 57.185 | First plan has no previous curve. Collision recovery, two fixed-height attempts and two shorter-prefix proposals accumulate; eventually succeeds. Optimizer timing includes internal A*, not just numerical optimization. |
| 123 | 5.355 | 68.635 | 6 | Seed: 64.640 / 64.514 | Reused curve fails final collision validation; cold initialization, fixed-height recovery and shorter targets are tried. Eventually succeeds. |
| 165 | 6.786 | 62.746 | 3 | Seed: 59.751 / 56.933 | Reused curve fails minimum-cruise/dynamic checks (0.509 m/s versus requested 0.600 m/s). Cold search fails, then a shorter prefix succeeds. |
| 670 | 24.926 | 118.671 | 2 | Seed: 117.244 / 116.942 | Previous curve cannot connect to the new target. Cold A* fails after 111 ms and 8,865 queue-loop iterations; shorter prefix succeeds. |
| 703 | 26.086 | 138.782 | 1 | Seed: 137.834 / 137.835 | Target connector rejected; cold A* fails after 137 ms and 9,564 queue-loop iterations. Optimizer never starts. Subsequent target/prefix checks reject and the round fails. |
| 899 | 42.496 | 120.458 | 0 | Target: 120.435 / 117.681 | Target selection searches from the current start to the final-goal neighborhood. A* fails after 118 ms and 8,068 queue-loop iterations. No spline initialization or optimization occurs. |

Evidence: [machine-readable attribution](attribution.json),
[CSV](attribution.csv), and the original numbered excerpts
[1](round_001.log), [123](round_123.log), [165](round_165.log),
[670](round_670.log), [703](round_703.log), [899](round_899.log).
The line-number prefixes refer to the original `nav2.log`.

## What the timers establish

The dominant stage's thread CPU time is at least 95% of its elapsed time in
every case. Tiny CPU/wall inversions reflect separate clock samples. These
calls spend their time executing work rather than mostly blocked or descheduled.
Input refresh takes 0.106–0.599 ms per complete round; final curve checks take
0–0.726 ms. Inline cloud/sliding-map profile entries are zero. Background
mapping still runs and is relevant to freshness; zero inline mapping does not
mean the mapper is idle or has no resource interaction.

Timers overlap: target includes goal search/proof; seed includes warm-seed,
initial graph search, fitting and control-point collision searches; optimizer
includes collision/rebound searches. Input refresh is nested in other stages.
**Do not sum every profile column or label all optimizer time as L-BFGS.**
The two smaller seed spikes lack an individual timer for every nested A* call,
so their exact per-search split is not established.

## Why the implementation permits a long round

The 30 Hz scheduler specifies when a round should start. Its reported 33.333 ms
budget is not a bound on synchronous work inside that round. A single A* call
has a 200 ms guard, and fallback planning can invoke multiple calls in sequence.
The 111/137/118 ms warnings are emitted after failed search exhaustion/recovery,
not by the 200 ms timeout. Queue-loop counts include obsolete heap records and
must not be called counts of distinct expanded nodes.

Target selection itself can run A* before spline planning: when the final goal
is not accepted by the occupancy query, `adjustGlobalTargetIfOccupied` calls
`findGoalNeighborhoodPath` before walking back along the reference route. This
is the expensive path in round 899. Earlier `Ran out of pool` messages describe
an endpoint outside the local search pool, not host RAM exhaustion; those cheap
returns must not be confused with the later long failed search.

Source anchors, with bytes checked against the v114 manifest:

- [A* guard and loop](../../runtime/scan_nav2_foxy_v86/src/path_searching/src/dyn_a_star.cpp#L257), terminal recovery at line 407 and exhaustion warning at line 449.
- [Target-neighborhood search](../../versions/v114/src/plan_manage/src/scan_replan_fsm.cpp#L377), nominal-round scheduling at line 899 and fallback planning at lines 1190/1380.
- [Seed and optimization](../../versions/v114/src/plan_manage/src/planner_manager.cpp#L331), nested control-point initialization at line 448 and optimizer at line 461.
- [Thread CPU profiling](../../versions/v114/src/plan_env/include/plan_env/planning_profile.h#L17).

## How long searches interact with stale-map stops

The mapper computes snapshots on a separate worker, but the native planner and
sensor callbacks share one mutually exclusive callback group. `/clock` is
separate. Native sensor messages are drained and map snapshots are adopted at
explicit refresh points; that does not happen continuously inside an A* call.

The recorder received clouds during both long failed rounds, so sensor
publication did not simply stop. The planning reader still crossed the
unchanged 250 ms map-age threshold before a replacement map was available to it:

| Round | Reader age before → after search | Clouds observed during round | Following recorded events |
|---|---|---|---|
| 703 | 119.9 → 259.9 ms | +35.2 and +135.6 ms | Output revoked `scan_safety_rejected` (original line 27822); snapshot for cloud stamp 37.311122894 appears later (27866), with mapping 96.097 ms + copy 5.397 ms. |
| 899 | 129.9 → 254.9 ms | +13.5 and +116.2 ms | Output revoked `scan_safety_rejected` (35610); snapshot for cloud stamp 53.702114105 appears later (35637), with mapping 103.370 ms + copy 5.247 ms. |
| 670 | 154.9 → 274.8 ms before refresh | +110.2 ms | A snapshot is published during search (26548); the following refresh adopts it and reduces age to 174.9 ms (26552). Planning then succeeds. |

See [adjacent original evidence](freshness_followup.log). This supports a coupled
failure sequence: expensive planning consumes the remaining freshness margin,
sensor ingress/snapshot adoption waits for explicit boundaries, and stale
queries reject before fresh mapping completes. The recorded revocation reason
is generic; stale age is a sufficient rejection condition in the collision
policy, but the logs do not identify every rejected voxel or prove that
separating callbacks alone would prevent the stop. Mapping completion itself
also takes time. Staleness reached during search may additionally affect later
collision queries in that same search.

Source anchors:

- [Shared native work group](../../versions/v114/src/scan_nav2_controller/src/controller.cpp#L40).
- [Sensor callback group](../../versions/v114/src/plan_env/src/grid_map.cpp#L160) and `refreshSensorInputs` at line 1060.
- [Stale-input rejection before occupancy](../../versions/v114/src/plan_env/include/plan_env/reactive_collision.h#L120).

## Remaining uncertainty and next investigation

This audit locates the measured cost and the fallback paths that trigger it.
It does not establish which exact obstacles, unknown cells, support queries or
freshness transition make each A* query fail. That needs per-query rejection
counts and timing, or replay of the same map/start/target/clock inputs.

The next useful work is to trace those failed searches, identify repeated work
across fallback candidates, and measure sensor enqueue/map-publication/adoption
times separately. Any implementation change should preserve collision and
freshness checks and be tested in a new version. Increasing the stale-map
threshold or merely truncating search is not a demonstrated repair.

## Reproduction and provenance

From the repository root:

```sh
python3 .pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-09_over60ms_diagnosis/analyze_over60.py --run-root /private/tmp/vla_newton_v116_0cy8ee75/runs/v116_mac_trial01_attempt02
```

The script verifies original log/observer hashes against the raw member
manifest, all 900 CSV/HTML durations, and eight native source hashes against
the frozen v114 manifest. `attribution.json` records these SHA-256 values.
Raw archive storage and recovery are documented in
[the preceding storage receipt](../2026-10-09_local_curve_timing/STORAGE.json).
The retained temporary run is an execution copy, not the durable source of truth.
