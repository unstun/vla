# v52: lookup speedup confirmed; live cold recovery still misses 30 Hz

Stage: experiment + analysis, 2026-10-02. Parent: frozen v50, directly from v48.
v49 remains frozen and excluded from ancestry. Navigation reference remains v48.

**The idle-host paired maximum improves by 10.67%, from 473.514 to 422.981 ms.
Live v52 achieves 11.54 Hz attempts and 10.19 Hz successful plans, with a
711.404 ms maximum and a 46.57 s late pause. Tail, continuity and 30 Hz
acceptance remain failed.** Frozen source and stop behavior were preserved.

## Why the planner cannot sustain 30 Hz

A 30 Hz period is 33.3 ms. Common warm rounds take about 2 ms, but the live mean
is 55.84 ms and P95 is 452.71 ms. A fast median therefore does not imply enough
throughput. The C++ planner uses a CPU SingleThreadedExecutor: synchronous cold
recovery blocks subsequent nominal planning calls, and missed slots are skipped.
The time-series plot shows near-30 Hz planning during motion, followed by zero
successful completions after about 43 s. The whole-run average is dominated by
that prolonged failed recovery phase.

The worst live round, at simulation 43.848 s, fails after seven seed searches,
four optimizer calls, three target selections, 23 input refreshes and six cloud
updates. Inclusive measured stages include 414.06 ms seed work, 201.71 ms
optimization and 187.75 ms input application; these overlap and must not be
summed. Final-goal-neighborhood search is only 0.0176 ms. The v50 precheck
already removed that earlier upfront bottleneck.
The optimizer logs first-three-control-point collisions and an inability to
generate valid rebound constraints. These are rejections by the planner's
collision/support model, not evidence of a physical contact. The precise query
behind the corner failure still requires an isolated replay.

The last observed nonemergency curve started at 42.338 s, lasted 1.041 s and
ended at 43.380 s, before the worst round. Warm rejections across the run report
identity_or_owner 654 times and target_connector eight times. Once warm reuse
is unavailable and cold recovery keeps failing, the old curve runs out and the
robot pauses. Observer packets do not reconstruct unpublished manager state;
the rejection logs and original code define the checks.

The idle paired cold case takes 422.981 ms wall and 422.927 ms thread CPU, about
12.7 planning periods, even without incoming clouds or competing GPU work.
Meanwhile, the controller separately measures 29.9998 Hz. A faster timer or a
20 ms abort cannot supply the missing safe plans.

Evidence: [live diagnosis](analysis/live_tail_diagnosis.json),
[measured metrics](analysis/v52_realtime_trial02_metrics.json),
[planning and scheduling source](../../runtime/scan74_terrain_lookup_v52/src/plan_manage/src/scan_replan_fsm.cpp),
[single CPU executor](../../runtime/scan74_terrain_lookup_v52/src/plan_manage/src/scan_planner_node.cpp).

## Idle-host paired comparison

One binary alternates original lookup and v52 reuse three times per fixed-input
case, restoring manager/FSM state. Both paths retain v50's precheck, v48 warm
initialization and all native final checks.

| Original simulation stamp | Original max / median | v52 max / median | Maximum reduction | Outcome in both modes |
|---|---:|---:|---:|---|
| 33.453 s | 95.640 / 95.089 ms | 88.893 / 87.727 ms | 7.05% | Success |
| 44.952 s | 473.514 / 465.129 ms | 422.981 / 422.885 ms | 10.67% | Failure |
| 74.041 s | 229.898 / 227.553 ms | 210.652 / 210.087 ms | 8.37% | Failure |

All 18 rounds retain identical outcomes and control points/knots. Faster
rejection does not create a feasible plan; all cold cases still exceed 33.3 ms.
[Paired result](profiles/attempt02/result.json), [summary](idle_paired_summary.json),
[PNG plot](analysis/idle_paired_latency.png), [PDF plot](analysis/idle_paired_latency.pdf).

The original shared-host attempt01 is preserved in
[its report](history/2026-10-02_component_only_report.md) and
[measurements](profiles/attempt01/result.json). It gave 483.747 to 434.117 ms
under concurrent IsaacLab load. The idle rerun confirms a similar component gain.
Replay omits live DDS batching, input arrivals and unpublished failed state;
never compare a live 1,829 ms spike directly with the 422.981 ms replay as a
causal speedup.

## Live Building comparison

These use the same Building profile and control configuration on gpu5070ti,
with independent physical trajectories. They are descriptive live comparisons.

| Run | Maximum solve | Whole-window successful planning | Measured 3D path | Longest pause |
|---|---:|---:|---:|---:|
| v48 historical trial01 | 1,090.481 ms | 15.29 Hz | 29.79 m | See original report |
| v50 trial01 | 1,829.626 ms | 10.39 Hz | 23.67 m | 42.58 s |
| v50 trial02 | 858.031 ms | 10.47 Hz | 23.66 m | 44.18 s |
| v52 trial02 | 711.404 ms | 10.19 Hz | 23.19 m | 46.57 s |

v52 records 89.962 s physics and an 84.594 s navigation wall window; actual
navigation RTF is 0.9332 with zero dropped physics steps. There are 116 rounds
at least 100 ms and zero at least 1,000 ms in this recording. This does not
establish elimination of extreme tails in general. The live maximum is lower,
while throughput/progress do not improve and the late pause remains. v50
trial02 retains its initial artifact-transfer overlap caveat.

No emergency-state transitions or remaining_spline_invalid events were logged.
The robot traveled 23.19 m, so v49's early 1.4 m paralysis is not reproduced;
the late pause still fails continuity acceptance. Full-route arrival and final
hold were not achieved. Process exit zero confirms recording completion only.

[Time-series PNG](analysis/v52_time_series.png), [PDF](analysis/v52_time_series.pdf),
[latency CSV](analysis/v52_realtime_trial02_latency.csv),
[frequency CSV](analysis/v52_realtime_trial02_frequency.csv).
Frequency counts events in trailing wall-second windows and maps them to
simulation time, retaining stalled time. Additional STOP messages are not
counted as native controller timer executions.

## Source, safety and evidence gates

Only grid_map.h and scan_reactive_grid_methods.inc change native behavior;
the other 98 files retain v50 bytes. The 4096-cell lookup cache holds raw/scored
layer pointers in the existing scope, clearing them at original mutation
boundaries. Each query still checks layer selection, freshness, collision and
support. Final goal, yaw, PVA, dynamics, ownership, recovery attempts and stop
protocol retain parent rules. There is no new planning deadline or cancellation.

Both builds passed; 35 native and 64 cache checks passed, including 16 lookup
assertions. Both recorded continuations retain exact parent geometry. Each warm
fixture passes 47 checks, goal-region checks pass, and all 17 backend stop tests
pass. All 18 paired cold rounds preserve exact output.

Post-run validation verifies all 6,761 frozen source hashes, 518 installed native
files and every one of 795 archived original members. All 17 compact returns
(4,791,064 bytes) match their declared SHA-256 and size. The frozen analyzer
computed metrics remotely; matplotlib is absent there, so the version-bound
diagnostic helper exports compact CSVs for local plotting. Frozen runtime and
analyzer bytes were preserved.

[Component qualification](component_qualification.json),
[live verification](analysis/live_verification.json),
[return verification](analysis/live_return_verification.json),
[plot provenance](analysis/live_plot_provenance.json), [acceptance](acceptance.json).

## Storage and continuation

Attempt01's busy-GPU preflight is preserved and executed zero physics.
Attempt02 ran after idle checks. Its 795 bulk members remain in the verified
227,438,274-byte archive on gpu5070ti at:

`/home/sun/vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction/runs/v52_realtime_trial02/raw_capture.zip`

No raw NPZ/JSONL, capture archive or build tree returned locally. Source
snapshots reference pinned inherited bytes instead of duplicating parent trees.
[Original-member manifest](../../runs/v52_realtime_trial02/raw_capture_manifest.json),
[remote artifact manifest](trials/attempt02/remote_artifact_manifest.json).

Next work must address the failing corner continuation and repeated cold
seed/optimizer work, retaining newest occupancy/support and final PVA checks.
Another small lookup speedup alone does not resolve that failure. Native behavior
changes require v53; keep v52 frozen and preserve its failed full-run acceptance.
Do not introduce v49 abort/stop mechanics or count asynchronous polling as
30 Hz successful planning.
