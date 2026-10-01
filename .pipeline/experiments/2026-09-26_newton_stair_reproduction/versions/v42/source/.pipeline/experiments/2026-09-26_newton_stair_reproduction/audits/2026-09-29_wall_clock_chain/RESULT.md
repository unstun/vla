# What ends runs on `odom_stale`: the Mac-side Newton worker stalls

On 2026-09-29, after the v31 trial, Dr Sun chose to diagnose the wall-clock freshness chain that ended v28,
v30 and v31, and then build v32 against it. This audit is that diagnosis. Everything here is a local
simulation on this Mac: an Apple M5 with 4 performance and 6 efficiency cores, running the pinned planner
image as `linux/amd64` under `--cpus=4`.

The record was revised after two rounds of independent review (`versions/v32/independent_review_round1.json`
and `independent_review_round2.json`). Round 1 failed with five blocking findings:
- **The float32 unit error:** pose stamps had been mapped to physics steps as `stamp × 1000`. MuJoCo-Warp's
  float32 time drifts, so the stamps are now mapped through the run's own telemetry pairs.
- **A bridge "mechanism C" that the data do not support.**
- **Inferences stated as measurements.**
- **A leak in the first v32 candidate.**
- **Two checks that could not fail.**

Round 2 failed with two:
- **Where B gaps arise:** the claim that every gap arose before publishing is wrong for B gaps.
- **Signs that were never recorded:** in-step counters were presented as measurements of freezes between
  steps.

In this record, **measured** means read directly from a run's own records, and **inferred** means a
reading of such records that they do not prove.

## Answer

The gate that ends these runs is the Linux backend's `odom_stale` check. It measures the wall time between
body-pose receipts, and the limit is 0.25 s (`runtime_sources/backend_adapter/backend_adapter/control_gate.py:138`,
fed by `time.monotonic()` in `backend_ros/p2b_backend_ros/node.py:226`).

**Where the gaps arise.** The two instrumented runs had 20 backend gaps over 150 ms (`pose_gaps_*.json`),
of two kinds. The discriminating measurement is the longest interval between two consecutive poses the
Mac-side Newton worker published inside the gap. Normally it is about 10 ms.

- **A, no pose published: process-wide freezes (7 of 20).** The worker published nothing for the whole gap
  (161–274 ms), and the backend received each pose 2–12 ms after its publication. So these gaps arose
  entirely in the worker, before publishing (measured).
  - **Measured for all 7:** the clock client thread in the same process stopped sending for as long
    (157–274 ms), and an external probe process woke on time (at most 10 ms late). So one thread held
    Python's GIL and the others could not run.
  - **Measured for the 2 A gaps inside a physics step only:** the process was not waiting for a CPU
    (runnable wait about 0), and its CPU time was on performance cores (efficiency-core share 0.03). The worker recorded these
    counters only inside steps, so for the 5 A gaps that fell between steps they were not measured.
  - **In `diag_v31_clock04`:** both A gaps coincided with logged full cyclic garbage collections, of 143 ms
    (in-step) and 176 ms (between steps) (measured).
  - **In `diag_v31_clock03`:** collections were not logged, so full collections are the inferred cause of
    its five freezes.
- **B, a worker slowdown plus poses superseded after publishing (13 of 20).**
  - **The slowdown (measured):** the worker kept publishing, but slowly. The longest interval between
    consecutive publishes was 39–87 ms instead of about 10 ms. Over the physics steps overlapping each
    gap, the process accumulated 152–724 ms of runnable-but-waiting time, and 0.09–0.64 of its CPU time ran
    on efficiency cores, against 0.04 in normal steps. Reading this as host CPU contention is an
    inference: the counters sum over all threads and whole steps, so they bound the physics thread's own
    waiting rather than measure it.
  - **The superseding (measured):** in all 13, 3–6 poses the worker published inside the gap never reached
    the backend. The Linux bridge keeps only the newest body state, and it superseded them. That makes a
    backend gap as long as several publish intervals together.
  - **Both parts were needed (inferred):** had every published pose been delivered with the receipt delays
    observed (3–49 ms), none of the 13 gaps would have exceeded about 135 ms, far under the 0.25 s gate.
  - **Not measured:** where the superseded poses were delayed after publishing. It could be the worker's
    own sender thread, the host-to-VM network, or the bridge's telemetry thread or 10 ms publish timer.

**The clock chain is a symptom (inferred).** The clock-observation rejections and command reconnects of the
"chain" are a sibling symptom. The clock client lives in the same worker process, and both kinds of stall
starve it.

**The physics computation is not the stall for v31 (measured by replay).**

## Evidence

### 1. The physics computation, for v31

- **Replay benchmark:** `bench_physics.py` replays v31_historical_full01's recorded commands through the
  same robot, Building, factory start-up, LiDAR scan thread and evidence writer thread.
  - **Reproduction:** it reproduces all 946 control steps' joint states exactly (worst error 0.0).
  - **Alone:** the worst step is 96 ms (median 32 ms). This includes v31's fatal step 836.
  - **Under load:** with four busy loops in the pinned amd64 image under `--cpus=4`, the median rises to
    44 ms (the trial's median was 47 ms) and the worst step is 127 ms.
  - **Pose gaps:** neither condition has a pose-publish gap over 91 ms (`bench/b01_alone`, `bench/b02_load4`).
  - **Scope:** this covers v31's commands only.
- **Planner (inferred from log silence):** SCAN logged nothing from 83.6 to 85.2 s on the Linux monotonic
  clock, around v31's fatal stall. It was most likely executing a curve, not planning.

### 2. What the saved trials show (`analyze_runs.py` → `analysis.json`)

| Run | Steps | Median / max step | Steps > 250 ms | Pose gaps > 0.2 s | Clock TTL windows | Reconnects |
|---|---|---|---|---|---|---|
| v28 | 333 | 39 / 344 ms | 1 | 0.373 s (fatal) | 2 | 2 |
| v29 | 3,867 | 38 / 211 ms | 0 | none | 0 | 0 |
| v30 | 3,022 | 42 / 348 ms | 13 | 5, incl. 0.264 s (fatal) | 2 | 1 |
| v31 | 946 | 47 / 347 ms | 6 | 3, incl. 0.288 s (fatal) | 3 | 3 |

- **v31's fatal step 836:** it took 0.347 s, with the command `active`. The backend received two
  consecutive poses 0.288 s apart, so no pose was published for 288 ms inside the step.
  - The clock client sent every 22–37 ms during the step, except for one 78 ms gap.
  - The LiDAR scan running beside it took a normal 28 ms.
  - So only the physics thread stalled. The clock client kept running, so it was not a process-wide
    freeze.
  - The trial has no per-step CPU data. A scheduling delay is the most likely cause (inferred), with a
    collection of up to about 78 ms possible.
- **v28's fatal gap (0.373 s, consecutive poses):** a 0.344 s step, preceded by a 200 ms gap between steps.
  The next step's command reads `disconnected` and the stance `STAND_SETTLING`.
- **v30's fatal gap (0.264 s):** two poses were superseded, and the step took 0.161 s after a 125 ms gap
  between steps.
- **Limit:** neither v28 nor v30 can be separated further.

### 3. The instrumented live run `diag_v31_clock03`

- **Setup:** the frozen v31 configuration with v31_historical_full01's exact flags. The worker is the
  unchanged pinned `newton_episode.py`, run by `diag_worker.py`, which adds only observation:
  - per-step wall, main-thread CPU and `rusage_info_v6` deltas;
  - per-substep timing;
  - a GIL-safe stack-sampling watchdog.

  An external lateness probe and a 1 Hz host sampler run beside it (`DIAG_RUN_PLAN.md`, written before the
  run).
- **Status:** a diagnostic run, not a v31 trial.
- **Outcome:** it ran 578 s of simulation (28,301 control steps) in 1,229 s of wall time and ended on
  `odom_stale`.

**Process-wide freezes (measured; cause inferred).**
- **Between-step freezes:** 4 over 100 ms, of 159, 200, 211 and 262 ms.
  - Each comes right after a scan-submission step (the steps whose `state_sequence` is a multiple of 5).
  - Each coincides with a clock-client send gap of the same length (168, 216, 214 and 274 ms).
  - The step after the 200, 211 and 262 ms freezes read `clock_unsynchronized` or `watchdog_timeout`; the
    one after the 159 ms freeze read `active`.
- **The fatal event:** the run's fatal 0.269 s pose gap is the 262 ms freeze. The physics steps on both
  sides took 35 and 41 ms.
- **In-step freeze:** one substep lost 221 ms with 3 ms of main-thread CPU.
  - Another thread used 244 ms of CPU in that step, and the watchdog could not get the GIL for 212 ms.
  - When it could, the LiDAR scan thread was inside Warp's kernel constructor
    (`codegen.extract_function_source` → `ast.parse`).
  - `newton.intersect_ray` (`newton/_src/geometry/raycast.py:916`) defines its kernel inside the function
    with `module="unique"`. So every scan, 10 per simulated second, rebuilds a `wp.Kernel` in Python before
    Warp finds the cached binary, and discards cyclic garbage.
- **External probe:** during all four between-step freezes, the probe process woke at most 10 ms late, its
  normal lateness. That supports a hold inside the worker, not an OS-wide stall.
- **Offline costs (`probe_scan_codegen.py`, `probe_gc_freeze.py`):**

  | Measurement | Result |
  |---|---|
  | Kernel rebuild per scan | median 0.6 ms, max 1.4 ms |
  | Collections per scan | one young-generation collection |
  | Kernel built once | outputs bitwise identical, 2 ms faster |
  | Full collection, fresh worker (910k tracked objects) | 70 ms |
  | Full collection, 28,000 retained telemetry rows (1.6M objects) | 160 ms |

  The worker retains one telemetry dict per control step (`rows.append(row)`) as well as the video states.
- **The cause is inferred:** collections were not logged in this run, so the freezes are attributed to
  full collections from the pattern and the offline costs. Section 4 shows that such collections occur,
  and at what size; it does not prove the cause of these particular freezes.

**Scheduling delays (inferred from process counters).**
- **Scale:** 57 steps exceeded 100 ms.
- **Upper bound, not a measurement:** of the physics thread's 4,053 ms off-CPU in those steps, up to
  3,487 ms is matched by the process's runnable waiting (`ri_runnable_time − CPU`, summed over all threads).
- **Efficiency cores:** the share in those steps reached 0.89, against 0.04 in normal steps.
- **External probe:** it was mostly 7–16 ms late in these steps (up to 44 ms), so it neither confirms nor
  excludes contention for CPU-bound threads.
- **Host load:** the host sampler shows the Docker VM process at about 200% CPU and the worker at about
  110% throughout.

### 4. The instrumented live run `diag_v31_clock04`: collections logged

- **Setup:** the same configuration as `diag_v31_clock03`. The worker now also logs every cyclic garbage
  collection (`gc.callbacks`: start, duration, generation, thread) and samples stacks during gaps between
  steps.
- **Outcome:** 390 s of simulation (18,939 control steps) in 832 s of wall time, ending on `odom_stale`
  (`gc_attribution_diag_v31_clock04.json`).
- **Collections in the control loop (measured):** 7,218 young (generation 0, max 0.9 ms) and 656 middle
  (generation 1, max 2.6 ms). Together they reclaimed about 3.7 million objects, roughly 970 per scan.
- **The five full collections** lasted 99, 112, 128, 143 and 176 ms. They came 20, 155, 299, 454 and 624 s
  into the loop, and four of them ran on the LiDAR scan thread. Each coincides with a stall, lying inside
  it or taking up nearly all of it:

  | Full collection | Stall |
  |---|---|
  | 99 ms | 103 ms between-step gap |
  | 112 ms | 156 ms in-step stall |
  | 128 ms | 172 ms in-step stall |
  | 143 ms | 186 ms in-step stall |
  | 176 ms | 181 ms between-step gap |

- **The other stalls:** 12 stalls of 151–196 ms have no collection behind them. They had process runnable
  waits of 150–490 ms (in-step counters), which is the slowdown of type B.
- **The fatal gap (0.297 s):** it is type B, with poses mapped through the telemetry pairs.
  - **What the worker published:** the eight poses from physics step 387,640 to 387,675, at 0, 83.5,
    121.6, 146.9, 179.7, 216.6, 244.5 and 278.6 ms. The longest interval was 83.5 ms.
  - **The slowdown:** in that window, a 176.8 ms step had 58.3 ms of main-thread CPU and 465.5 ms of process
    runnable wait. A 119.7 ms step followed it.
  - **The superseding:** the six poses in between were superseded after publishing, and only the first and
    last reached the backend.
  - **What tripped the gate (inferred):** had they been delivered, the backend's longest gap here would
    have been about 84–105 ms, given the receipt delays observed, which is under the 0.25 s gate. The
    superseding, not the slowdown alone, tripped the gate.
- **Correction:** the round-1 version of this record called this gap a bridge delivery stall. That came
  from mapping stamps as `stamp × 1000`, which is off by 1.78 s at that point.

### 5. Every gap over 150 ms in the two instrumented runs (`analyze_pose_gaps.py` → `pose_gaps_*.json`)

| | A: no pose published | B: poses superseded after publishing |
|---|---|---|
| `diag_v31_clock04` gaps | 2 (161, 189 ms) | 6 (151–297 ms) |
| `diag_v31_clock03` gaps | 5 (162–269 ms) | 7 (156–201 ms) |
| Longest interval between consecutive Mac publishes | the whole gap, 161–274 ms | 39–87 ms |
| Poses published inside the gap and superseded | 0 | 3–6 |
| Backend receipt delay of the two received poses | 2–12 ms | 3–49 ms |
| Clock-client send gap | 157–274 ms (stopped) | 30–105 ms (running) |
| Runnable wait over the overlapping steps (in-step counters) | about 0 for the 2 in-step A gaps; not measured for the 5 between steps | 152–724 ms |
| Efficiency-core share of those steps (in-step counters) | 0.03 for the 2 in-step A gaps; not measured between steps | 0.09–0.64 |
| Logged collection (`diag_v31_clock04` only) | 143, 176 ms | none |
| External probe, worst lateness | 7.6–10 ms | 9–39 ms |

- **Where A gaps arise:** before publishing.
- **Where B gaps arise:** the worker contributes its longest publish interval (39–87 ms), and the rest of
  each gap arose after publishing, where the location is not measured.

### 6. The clock chain is a symptom (inferred)

**How the chain works.** The clock client (`scripts/clock_sync.py`) samples every 20 ms and drops a sample
whose round trip reaches 10 ms. After 200 ms without an accepted sample, `estimate()` raises
`clock_observation_stale`. The command receiver then rejects the batch and the stream reconnects, and the
command reads zero until it recovers.
- **Rejected samples:** in v31 their return leg was inflated (median 16.2 ms, against 2.7 ms outbound). That
  fits the client thread waiting on the Mac side, but the host-to-VM path could also add it (inferred).

**The TTL windows (`ttl_windows.py` → `ttl_windows.json`)** come in two kinds:
- **Client thread frozen:** a single send gap of 206–274 ms. This covers 5 of `diag_v31_clock03`'s 7
  windows (three match its between-step freezes and one its 266 ms in-step freeze) and 1 of v31's 3.
- **Client thread running with rejected samples:** send gaps of 45–123 ms, with 5–10 consecutive samples
  rejected at 11–98 ms round trips. This covers both of v28's windows, both of v30's, 2 of v31's and 2 of
  `diag_v31_clock03`'s. `diag_v31_clock04` had no TTL window at all.

**The reconnect cannot block the physics:** it runs in the command receiver's thread and holds no lock that
`robot.step` waits on. Its zero command does switch the controller to `STAND_SETTLING`, and v31's replay
covers that branch at 96 ms or less. v28's order, a reconnect before its 0.344 s stall, is therefore most
likely two results of one starved process (inferred).

## Which stall ended which run

| Run | Fatal gap | What happened | Status |
|---|---|---|---|
| v31 trial | 0.288 s, no pose published | Only the physics thread stalled, inside a 0.347 s step. The clock client kept sampling (one 78 ms gap), so it was not a process-wide freeze | no-publish measured; cause inferred (a scheduling delay most likely; a collection of up to about 78 ms possible) |
| `diag_v31_clock03` | 0.269 s, no pose published | A: a process-wide freeze of 262 ms between steps | freeze measured; garbage-collection cause inferred |
| `diag_v31_clock04` | 0.297 s, six poses superseded | B: a worker slowdown (longest publish interval 83.5 ms) plus six poses superseded after publishing. The superseding made it exceed the gate | slowdown and superseding measured; the superseding's location not measured |
| v30 trial | 0.264 s, two poses superseded | a 125 ms gap between steps and a 0.161 s step | not separable |
| v28 trial | 0.373 s, no pose published | a 200 ms gap between steps, then a 0.344 s step | not separable |

## Other explanations considered

- **Blocking calls in the worker's main loop:** the ZMQ round trip, and reading `backend_latest.json`
  every fifth step.
  - They cannot cause A, because they release the GIL: the clock client would keep running.
  - B's slow time falls inside `robot.step`, which makes no such call.
- **Host memory pressure:** a residual factor.
  - **Host:** free memory fell from 7.4 to 2.5 GB during `diag_v31_clock03`, with 1,112 swap-ins and
    6,803 decompressions, and from 10.6 to 3.9 GB during `diag_v31_clock04`.
  - **Worker:** it had only 26 page-ins in each run's steps, so paging is not the direct cause.
- **Instrumentation:**
  - The watchdog polls every 10 ms, and every step makes two `proc_pid_rusage` calls. These add a little
    GIL traffic.
  - Both instrumented runs had fewer long steps than the v31 trial, and both still failed.
- **Stamps are float32 simulation time:** MuJoCo-Warp's time runs ahead of `physics steps × 1 ms`, by
  −43 ms at step 100,000, +451 ms at 200,000 and +1,779 ms at 387,640. Every analysis here maps stamps
  through the run's own (step, time) pairs. Any gate or analysis in simulated time must use one clock
  consistently.

## What v32 can and cannot change

- **A: v32's hypothesis.** v32 calls `gc.collect()` and then `gc.freeze()` before the control loop and after
  every 50th control step.
  - `gc.freeze()` resets the collection counters and moves the survivors into the permanent generation.
    Automatic full collections then no longer traverse the retained heap.
  - The explicit collection before each freeze reclaims each window's garbage, including every scan's
    discarded kernel objects. The first candidate froze without collecting, and would have leaked about
    0.14 MB per scan.
  - L1 tests the hypothesis (`versions/v32/PLAN.md`).
- **The worker's slowdown under host load (B's first part):** not addressed.
  - On its own it kept publish intervals at 87 ms or less in the diagnostic runs.
  - A stall of the physics thread with nothing published, like the v31 trial's 288 ms, can still exceed
    the 0.25 s gate alone.
- **The superseding after publishing (B's second part):** not addressed, and its location is not measured.
  - What L1 adds: each frame's enqueue and send time in the worker, and each body state's receive and
    delivery time in the bridge.
  - What could follow: a delivery-side change would keep B gaps near the worker's publish interval without
    changing any gate. It would apply wherever L1 locates the delay: the worker's sender thread, the
    host-to-VM path, or the bridge's newest-only timer. That would have prevented `diag_v31_clock04`'s end.
- **For Dr Sun, two different options:**
  - **(1) a delivery-side change,** once L1 has located the superseding.
  - **(2) a new gate time base:** the gate would measure the age of the newest pose in simulated time
    instead of the wall time between receipts. This is the only option for stalls with nothing published,
    like v31's. It changes the navigation stack's safety semantics in simulation, and MuJoCo-Warp's float32
    time drift would have to be handled.
  - Both are Dr Sun's decisions, not part of a default v32.

## Other observations

- **`diag_v31_clock03`'s route:** from the same v31 configuration, it climbed both flights and reached the
  upper landing. It stood at the corridor entry, (−4.86, −3.51, body z 1.84), from about 290 s. SCAN
  rejected 2,870 final curves as `Collision` (status 1) and 487 as `InvalidCurve` (status 2), which is
  consistent with the known wrong-height corridor cell. This is recorded, not analysed, and it is not a v31
  result.
- **`diag_v31_clock04`'s route:** it reached the same place, (−4.82, −3.64, 1.85), by 54 s of simulation
  and stood there until `odom_stale` at 390 s.
- **Invalid attempts:** `diag_v31_clock01` and `diag_v31_clock02` failed through my instrumentation
  (`DIAG_RUN_PLAN.md`).
  - Attempt 1 left 49 cold-compiled kernel modules at the root of `runtime/warp-cache/`, outside the
    `1.17.0/` directory that pinned runs read. Warp ignores them, and they are left in place.
- **Memory:** peak RSS was 1.70 GB for `diag_v31_clock03` (578 s of simulation) and 1.35 GB for
  `diag_v31_clock04` (390 s), against 0.91 GB for the 30 s v31 trial.

## Files

- **Analysis scripts:**
  - `analyze_runs.py` → `analysis.json`;
  - `analyze_diag.py` → `diag_attribution_diag_v31_clock03.json`;
  - `ttl_windows.py` → `ttl_windows.json`;
  - `analyze_gc.py` → `gc_attribution_diag_v31_clock04.json`. Its pose-gap section used the wrong stamp
    mapping and is superseded by the next script.
  - `analyze_pose_gaps.py` → `pose_gaps_diag_v31_clock03.json` and `pose_gaps_diag_v31_clock04.json`.
- **Benchmark:** `bench_physics.py`, `run_bench.py` and `probe_latency.py`, with results under `bench/`.
- **Instrumented runs:** `DIAG_RUN_PLAN.md`, `diag_launch.py`, `diag_worker.py`, `rusage_v6.py`,
  `container_site/sitecustomize.py` (with `smoke_check.sh` and `smoke_check_output.txt` from the pinned
  image) and the supervisor logs. The runs themselves are `runs/diag_v31_clock01`–`04`.
- **For v32's L1:**
  - the worker records absolute counters at each step's start and end, marks explicit collections, and
    records each telemetry frame's enqueue and send times (`diag_worker.py`);
  - `analyze_pipeline.py` splits each body state's delivery into the pre-registered segments;
  - `analyze_linux.py` summarises the container-side records.
- **Offline probes:** `probe_scan_codegen.py` → `probe_scan_codegen.json`, and `probe_gc_freeze.py` →
  `probe_gc_freeze.json`. The latter measured collections right after a freeze, so it shows only the
  pre-freeze costs as evidence.
