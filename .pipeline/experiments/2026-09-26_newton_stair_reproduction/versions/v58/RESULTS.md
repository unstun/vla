# v58 results: endpoint-evidence certificate

Stage: experiment + analysis, 2026-10-03. **Component validated; physical recording completed; sustained 30 Hz and tail elimination fail.** Parent v57; frozen native candidate `runtime/scan79_goal_endpoint_evidence_v58`. v49 is excluded.

The necessary endpoint check removes repeated unsuccessful final-goal searches before warm initialization. It uses current, optimistic observation evidence for both reflected cylinder centers across possible endpoints. Possible endpoints retain native search. Near-body unknown-space handling and all occupancy, stair support, final goal, yaw, PVA, dynamics and stop rules remain unchanged. Manager, FSM, controller and configuration are byte-identical to the parent.

## Controlled component result

| Idle-host paired replay | Certificate disabled | v58 enabled |
|---|---:|---:|
| Maximum goal-search latency | 44.614381 ms | 0.259025 ms |
| Formerly expanding states requiring graph expansion | 12 | 0 |

Twenty original states and two repetitions per setting (80 alternating calls) preserve exact return values and paths. Maximum component latency falls **99.4194%**. This measures goal search, not the complete solve or live frequency. [Idle replay03](paired/idle_summary.json), [full result](paired/attempt03/result.json).

Replay02 measured 45.128580 → 0.272144 ms but overlapped another host job; that result and its load caveat remain preserved in the frozen [original summary](paired_summary.json). The unchanged-source replay03 ran with no GPU jobs or containers. The initial broader-square implementation and its incomplete improvement remain in `history/` and build/test/replay01.

Build02 and contracts02 pass: 35 native checks, 64 cache checks, 47 warm checks per fixture, 3,000 arbitrary-yaw footprint pairs, goal-region, recovery freshness, physical-floor roles/native callbacks and backend contracts. Both cold geometries remain exact. [Contract result](tests/attempt02/result.json). The source freeze contains 7,572 entries and 47 copied delta files; source/install/qualification/physical-input gates pass.

## Completed physical validation

`v58_realtime_trial02` completed the 90-second request with 90,000 steps, 89.962189 native seconds and no dropped steps. Whole-navigation-window successful planning is **27.53 Hz**; median solve **2.041 ms**, P95 **12.827 ms**, P99 **74.486 ms**, maximum **659.526 ms**. Measured 3D path is **55.188 m**; no full-goal arrival.

There are no logged emergency transitions or invalid-current-spline events. Both new versions share an initial 1.40-second navigation wait; v58 has no measured hold over one second afterward. Its worst round still enters repeated cold recovery after `target_connector` rejection. This is not general tail elimination.

The earlier `v58_realtime_trial01` attempt stopped before physics because another GPU evaluation was active; its [preflight](trials/attempt01/preflight.json) is retained. Dr Sun's instruction to wait was honored, and trial02 ran after the GPU became available.

The separate timestamp correction is [v59](../v59/RESULTS.md). See the [complete comparison](../v59/REPAIR_REPORT.md), [updated figure](../v59/analysis/v59_time_series.png) and [acceptance flags](acceptance.json). Heavy raw records and builds remain on gpu5070ti; only compact evidence and the final review video return locally. v48 remains the runnable reference.
