# v32 live runs: no collection stall in the worker; both runs still end on `odom_stale`, and the trial stands at the corridor's wrong-height cell

v32 was frozen at 2026-09-29T10:37:24Z (`manifest.json`, 2,973 files). After both runs, all 2,973 entries still
match. One audit output was overwritten after the freeze and has been restored (see Records). Both runs followed
`PHYSICAL_RUN_PLAN.md`:
- **L1** `diag_v32_clock01`: the instrumented diagnostic run. It is judged by `l1/evaluate_l1.py` exactly as
  pre-registered.
- **L2** `v32_historical_full01`: the trial. It is judged by the unchanged Building review.

v32 targets only mechanism A: full cyclic collections in the Mac worker that hold the GIL.

## L1 `diag_v32_clock01`: inconclusive by the exposure rule; neither criterion was violated

`l1/l1_evaluation_diag_v32_clock01.json`, from `l1/evaluate_l1.py` (sha256 `ef4a4b3a…`, the file the
synthetic check ran).

- **Outcome: inconclusive.** The run covered 2,818 control steps, and the rule requires 7,100. The run ended on
  `odom_stale` at 65.2 s sim, after 156 s of wall time.
- **Watchdog log:** it spans the loop, with 11,849 wake-ups and no incomplete interval.
- **Criterion 1 held over what the run covered.**
  - No automatic generation-2 collection ran inside the loop.
  - The longest in-loop collection took 16.39 ms of wall time and 2.6 ms of CPU. It was an explicit window
    collection.
  - There were 56 explicit collections. Generation 0 ran 3,789 times (longest 0.40 ms) and generation 1 ran 330
    times (longest 1.19 ms).
  - The start-up collection before the loop took 95.4 ms. It is reported only.
  - Under v31's configuration, `diag_v31_clock04` had its first full collection at control step 485, within
    this run's span. The run is still short of the pre-registered exposure, so this does not change the outcome.
- **Criterion 2 held.** No interval was a process-wide hold.
  - All 11 intervals were scheduling-type, with runnable waits of 171–977 ms.
  - The worst was a 672.6 ms step with 977 ms of runnable wait and a 191 ms watchdog gap.
- **Peak RSS:** 913 MB.
- **Container processes** (longest collection of wall time, with its generation):

  | Process | Longest collection | On the pose path |
  |---|---|---|
  | backend (`native_backend_entry.py`) | 4.12 ms (generation 2, the only one) | yes |
  | pose bridge (`foxy_bridge_node`) | 0.68 ms (1) | yes |
  | `ros2 run` wrapper of the planner (waits for its child) | 40.5 ms (0) | no |
  | PCT worker (`backend_adapter.pct_worker`) | 38.3 ms (1) | no |
  | all others (applied channel, observer, clock responder and publisher, driver, graph, controller wrapper) | ≤ 1.22 ms | — |

  - **The two long ones:** neither is on the pose path. The `ros2 run` wrapper only waits for its child, so its
    40.5 ms probably includes time the VM spent descheduled (inferred). The PCT worker's was not examined.

### How L1 ended: a delivery stall in the bridge while the whole host was short of CPU

Sources:
- the backend callback log;
- `audits/2026-09-29_wall_clock_chain/pose_gaps_diag_v32_clock01.json`;
- `pipeline_diag_v32_clock01.json`, the pre-registered delivery-path split.

- **When the fault started:** the backend's stop flow began at 146.651 s on its monotonic clock. That is inside
  a 376.9 ms gap between body-pose callbacks (146.326 → 146.703 s, stamps 65.2158 → 65.2258 s).
- **The Mac worker kept publishing (measured).** It published the next two poses 61.8 and 104.8 ms after the
  pose delivered before the gap. Its longest interval between publishes was 61.8 ms.
- **The bridge held the next delivered pose (measured).**
  - Pose 65.2208 was superseded. The bridge received it 0.49 ms before 65.2258, so the blame rule assigns it to
    transit or receipt.
  - Pose 65.2258 took 4.5 ms in the worker's queue, 0.1 ms to send and 16.5 ms in transit and receipt. It then
    waited **254.5 ms in the bridge**, followed by 5.8 ms of ROS delivery.
  - One bridge publish callback took **288.5 ms**, and there was no collection in the bridge during the gap.
- **The worker was starved at the same moment (measured).** The overlapping steps had 1,002 ms of runnable wait,
  and 74% of their CPU time ran on efficiency cores.
- **Cause of the bridge stall: not measured.** There is no CPU accounting inside the Linux VM. A host-wide CPU
  shortage is the likely cause (inferred).
- **The other four gaps over 150 ms:**
  - **157.6 ms:** 4 poses superseded after publishing. The blame rule gives 2 to the bridge timer and 2 to
    transit or receipt, and one bridge publish callback took 104.4 ms.
  - **181.8, 263.0 and 282.0 ms:** no pose published during a slow worker step, with efficiency-core shares of
    0.73–0.93. The last two came after the fault.
- **Delivery stages over all 11,272 body states** (8,493 delivered):

  | Stage | Median (ms) | Max (ms) |
  |---|---|---|
  | worker queue | 0.2 | 21.7 |
  | send | 0.1 | 14.0 |
  | transit and receipt | 0.2 | 41.9 |
  | bridge hold | 4.5 | 254.5 |
  | ROS delivery | 0.8 | 63.6 |

- **Clock sync:** 62 rejected samples and 2 TTL windows, of 817 and 219 ms. The 817 ms window held a 207 ms send
  pause, inside the 672.6 ms scheduling step. There were 3 command reconnects, the last with
  `clock_observation_stale`.
- **Its navigation:**
  - It climbed both flights: body z reached 0.9 m at 19.26 s, 1.4 m at 24.62 s, 1.65 m at 28.86 s and 1.8 m at
    32.21 s.
  - Between 30 and 35 s it paused several times between curves, each time for under a second. It then walked
    through the corridor entry at up to 0.79 m/s and reached (−2.27, −4.33) at 40 s.
  - It walked along the upper corridor and had stopped by about 60 s at (7.42, −4.29, body z 1.85).
  - SCAN logged 26 clear final checks and 2 collision rejections. Both rejected curves started at (7.26, −4.34),
    with their first colliding sample near (7.6, −4.2). That spot is not analysed.

## L2 `v32_historical_full01`: failed; it stood at the corridor entry, then ended on `odom_stale`

- **Gates:** the integration-version, native-identity and reviewed-candidate gates passed before physics.
- **Building review:** `passed=false`.
  - **Failing:** `common_interface`, `native_arrival`, `driver_arrival_and_pd`, `goal_xy` and
    `goal_floor_clearance`.
  - **Passing:** among others, `no_fall`, `continuous_physics`, `automatic_native_layers`,
    `historical_route_length`, `correct_goal_level`, `original_pd_gains` and `final_pd_two_seconds` (238 s of
    final PD hold).
  - **Against v31:** v31 failed the same five plus `final_pd_two_seconds` and `original_pd_gains`.
- **Local review:** it fails `process_completed` and `bounded_driver_completed`, as v31 did.
- **Run size:**
  - 286.48 s of physics in 13,721 control steps and 721 s of wall time. That is longer than any earlier trial;
    the previous longest, `v26_historical_full02`, ran 110.7 s.
  - Peak RSS 1.15 GB.
  - Actual XY path 9.92 m and navigation path 10.72 m. Goal XY error 6.88 m. No arrival and no fall.
- **Motion** (`video_states.json`):
  - **Climb:**

    | Body z | L2 | L1 | v31 |
    |---|---|---|---|
    | 0.90 m | 19.26 s | 19.26 s | 19.34 s |
    | 1.40 m | 27.90 s | 24.62 s | 25.82 s |
    | 1.65 m | 33.25 s | 28.86 s | — |
    | 1.80 m | 35.17 s | 32.21 s | — |

  - **Stop:** from 39.3 s on it stayed within 0.1 m of (−4.91, −3.45, body z 1.84) at the upper corridor entry.
  - **Stance:** it settled from 39.97 s, passed through `STAND_TRANSITION` at 46.37 s and held `FIXED_STAND`
    (the PD stance hold) from 48.37 s to the end.

### Why the trial stood at the corridor entry: the wrong-height navigation cell

`corridor_entry_curves.py` → `corridor_entry_curves.json`. The script replays SCAN's own log offline:
- it pairs every final check with the checked cubic B-spline that SCAN logged just before it;
- for each rejection, it evaluates the curve at the logged first-collision time;
- it places curve samples in PCT's 0.1 m navigation grid.

It does not rerun the native check.

- **Cross-check against the v30 audit:** on `v30_historical_full01` it finds exactly the audit's 109 rejections
  at cell (47, 41). Their offsets are 0.120–0.1355 m above the 1.4189 m landing layer plus 0.30 m, where the
  audit's native replay gave 0.1200–0.1354 m.
- **The cell:** (47, 41) is centred at (−2.345, −4.187). It carries only the landing height where the corridor
  floor is 1.561 m. The native check fails a sample whose offset exceeds 0.12 m.
- **Where the curves failed:**

  | Run | Start of the last rejected curve | Collision rejections from there | First sample at cell (47, 41)'s west edge | Other collision rejections |
  |---|---|---|---|---|
  | L2 `v32_historical_full01` | (−4.91, −3.48) | 2,130 | 2,130 | 8: 6 at the corridor-entry corner, 2 on the stairs |
  | `diag_v31_clock03` | (−4.90, −3.55) | 4,812 | 4,812 | 3 |
  | `diag_v31_clock04` | (−4.90, −3.56) | 3,444 | 3,444 | 8 |

  - **L2's samples:** all 2,130 of those curves cross x = −2.345 at y = −4.143/−4.144, inside the cell's row
    (y −4.237…−4.137).
  - **Cell assignment:** their first samples lie within 1.5 mm of the cell's west edge at x = −2.395, so the
    offline evaluation splits them between (47, 41) and (46, 41) by rounding.
  - **Offsets:** the (47, 41) samples sit 0.1265–0.1274 m above the reference.
- **How L1 passed:** no L1 curve entered the cell. Its first clear curve from the corridor entry started at
  (−4.86, −3.65), about 0.2 m further along than where L2 stood. It crossed x = −2.345 at y = −4.119, 1.8 cm
  north of the cell's row, and its two later clear curves crossed 0.10–0.13 m south of the row.
- **How v30 passed:** its curves at the corridor entry did cross the cell, and four of them passed its check
  with offsets of 0.1191–0.1200 m. v30 paused there for about 15 s.
- **Reading:** this is v30's wrong-height cell. In 3 of the 4 v31/v32 runs that reached the corridor entry, it
  blocked all progress. Whether a run passes depends on centimetres in the curve's position, set by where the
  preceding curve left the robot, which run-to-run timing changes (inferred).

### How L2 ended

- **The fatal gap:** a 0.320 s pause in body-pose callbacks, between stamps 284.4008 and 284.4059 s. The stamps
  are consecutive, so no pose was superseded.
- **Where it sat:** inside control step 13,618, which took 0.326 s of wall time while the robot stood in
  `FIXED_STAND`. The worker published nothing for 320 ms (inferred from the consecutive stamps and the step
  length; L2 carries no instrumentation).
- **Not a process-wide hold (inferred).** The clock client kept sending during the step, with a longest send
  gap of 101 ms inside the 462 ms TTL window that overlapped it. So the worker stalled in the step without
  stopping the whole process. The pattern fits mechanism B (worker slowdown), not A.
- **Host load:** `audits/2026-09-29_wall_clock_chain/l2_host/v32_historical_full01_host.jsonl` holds one sample
  per second.
  - Across the run, the 1-minute load average had a median of 6.8. `git` ran in 412 of 653 samples: 619 of the
    642 git process sightings were in `/Users/sun/tongbu/study/phdproject/machine-dog`, and up to 6 ran at
    once.
  - At the fatal gap, a burst of four git processes in `machine-dog` began.
    - 0.5 s before, the load average was 7.3 and no git process ran.
    - At +0.7 s it was 11.2, with four git processes at 4–26% CPU.
    - By +3.2 s they were at 61–98%.
  - These processes are the Claude desktop app's session-diff refreshes (`git diff --numstat`) for another
    session, identified from their command lines during the diagnosis.

### Signatures and the clock record, against the diagnostic runs and v31

| | L2 | L1 | `diag_v31_clock03` | `diag_v31_clock04` | v31 trial |
|---|---|---|---|---|---|
| Control steps | 13,721 | 2,818 | 28,301 | 18,939 | 946 |
| Clock-client send pauses over 150 ms | 0 | 1 (207 ms) | 6 | 2 | 1 |
| Steps over 150 ms | 34 | 11 | 10 | 17 | 18 |
| …with a clock pause covering ≥ 80% of the step | 0 | 0 | 1 | 1 | 0 |
| Command reconnects | 5 | 3 | 1 | 0 | 3 |
| Conflict stops at 0.000 s / executing-curve invalidations | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Final checks clear / collision rejections | 12 / 2,138 | 26 / 2 | 12 / 4,815 | 12 / 3,452 | 9 / 0 |
| "The robot is inside an obstacle" | 10 | 2 | 4,806 | 4,592 | 0 |

- **Sources:** `clock_pause_signature.py` → `clock_pause_signature.json`, and `runs/<run>/trial_signatures.json`
  (v31's `trial_signatures.py`, unchanged).
- **Input refresh (L2):** every after-refresh age was under its gate, with the body pose at most 0.025 s and the
  scan at most 0.126 s.
- **L2's clock:**
  - 309 of 27,514 converged samples were rejected (1.1%).
  - There were 4 TTL windows (249, 316, 304 and 462 ms). In each, the client kept sending, with longest send
    gaps of 87–101 ms.
  - Output: `audits/2026-09-29_wall_clock_chain/ttl_windows_v32_historical_full01.json`.
- **"Inside an obstacle":** the difference between L2 (10) and the diagnostic runs (4,806 and 4,592), which
  stood 7–8 cm further along, is not analysed.
- **What the pause counts suggest:**
  - In the v31-config diagnostic runs, send pauses over 150 ms came once per about 4,700 steps
    (`diag_v31_clock03`) and 9,500 steps (`diag_v31_clock04`).
  - In those runs, 7 of the 8 pauses coincided with a recorded worker stall: 5 freezes between steps and 2
    stalls inside a step. Each of `diag_v31_clock04`'s two pauses overlapped a logged full collection, of 143
    and 176 ms.
  - At those rates, L2's 13,721 steps would have had about 3 and 1.5, and it had none. The v31 trial had 1 in
    946 steps.
  - This fits the absence of mechanism A, but it is not a measurement. A send pause alone cannot separate A
    from a scheduling delay, and host load differs between runs.

## What this shows and what it does not

- **Shown (measured, L1):** over 2,818 steps, v32's worker had no automatic full collection and no process-wide
  hold of more than 100 ms. Its longest collection took 16.4 ms. L1's pre-registered outcome is still
  inconclusive, because its exposure was short.
- **Consistent, not measured (L2):** the uninstrumented trial ran 13,721 steps without a clock-client pause over
  150 ms.
- **Not fixed:** mechanism B ended both runs, in two different places:
  - **L1, delivery side (measured):** the bridge held a pose for 254.5 ms, during a 288.5 ms publish callback in
    the VM.
  - **L2, worker side (inferred):** no pose was published for 320 ms inside a 326 ms step, while the clock
    thread ran.
- **So one delivery-side change would not have saved L2.** Only a gate that does not count wall time during a
  simulation stall, or a quieter host, addresses both.
- **Not attributable to v32:** L2 ran longer before its fault (284 s against v31's 27.7 s), but the v31-config
  diagnostic runs reached 578 and 390 s. With this much run-to-run variation in host load, one run cannot credit
  the longer run to v32.
- **Navigation:** the corridor entry's wrong-height cell is now the blocker that stops the trial, independent of
  the clock. L1's pass through it was a matter of centimetres.

## Options for the next step (Dr Sun's decision)

1. **A quiet host during trials.** No code change: pause the other session's `machine-dog` diff refreshes while a
   trial runs. It reduces B but does not remove it. The container stack (emulated `linux/amd64`, `--cpus=4`)
   still shares the Mac's cores with the worker.
2. **The gate's time base.**
   - **The change:** judge body-pose freshness by simulation-time age instead of wall time between receipts.
   - **What it covers:** both L1's and L2's fatal stalls, since simulation time stops when physics stalls.
   - **What it touches:** the navigation stack's safety semantics in simulation. It must also handle MuJoCo-Warp's
     float32 time drift.
3. **A delivery-side change in the bridge,** for example publishing on receipt instead of on the 10 ms timer. L1
   located two bridge stalls (288.5 and 104.4 ms). The change would not have prevented L2's worker-side gap, and
   it may not help if the VM itself is starved.
4. **The wrong-height cell (navigation).** The v30 audit's scopes apply: correct the cell, or tolerate an
   isolated support outlier. This is the blocker that holds the trial at the corridor entry.

## Videos

- **Standard view:** `output/2026-09-27_lite3_versions/v32_historical_full_odom_stale.mp4`.
  - Unchanged renderer; its executed files and `appearance.json` are identical to v31's render.
  - Receipt in `video_receipt.json`: 3,567 frames at 12.5 fps, full decode passed. Frames 239, 496, 1,872 and
    3,566 were checked by eye.
- **Heading-follow view:** `output/2026-09-27_lite3_versions/v32_historical_full_odom_stale_heading_view.mp4`.
  - Display camera only. The run is `runs/v32_historical_full01_video02`, with its own receipt.
- **What they show:** the robot climbs the stairs under RL, reaches the corridor entry at about 39 s with the
  PCT route turning left into the corridor, and then stands there in `FIXED_STAND` until
  `Navigation: failed (odom_stale)`. It is visible throughout.

## Records

- **Restored after the freeze:** `audits/2026-09-29_wall_clock_chain/ttl_windows.json` is pinned in the manifest.
  Running `ttl_windows.py` on L2 overwrote it, because the script always writes that one file.
  - The frozen file was restored from `versions/v32/source/` and matches the manifest again.
  - L2's output is kept as `ttl_windows_v32_historical_full01.json`.
  - L1's was produced with the output redirected, as `ttl_windows_diag_v32_clock01.json`.
  - The pinned script was not changed.
- **New post-trial analyses** (not part of v32's change or its judge): `corridor_entry_curves.py`,
  `clock_pause_signature.py` and their JSON outputs.
- **Local-only bytes:** each is inventoried with its size and SHA-256, and ignored by a path-specific entry.
  - **`LOCAL_ONLY_BYTES.json`:** L2's raw captures (v31's thirteen kinds), K3's replay caches and the standard
    render's frames.
  - **The heading-view render:** its own inventory in `runs/v32_historical_full01_video02/`.
  - **L1 and the other diagnostic runs:** their raw captures are in
    `audits/2026-09-29_wall_clock_chain/LOCAL_ONLY_BYTES.json`. That inventory also holds their GC and substep
    arrays and every other file of at least 10 MB.
  - **L2's `scan.log` (24.7 MB) and `sensor_manifest.json`:** they stay tracked, following v31's convention.

## Status

- **The trial failed.** The robot stood at the corridor entry's wrong-height cell from 39.3 s, and the run ended
  on `odom_stale` at 284.4 s.
- **Versions:** v32 is frozen and unvalidated. v3 remains the last accepted navigation condition.
- **Mechanism A** is absent over L1's short, measured exposure and consistent with absence in L2.
- **Mechanism B** remains.
