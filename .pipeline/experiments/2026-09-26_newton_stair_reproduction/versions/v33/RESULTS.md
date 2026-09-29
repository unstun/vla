# v33 live run on gpu5070ti: no pose gap reached the gate; the trial stood at the corridor entry until SCAN's replan limit ended it

v33 was frozen at 2026-09-29T16:58:53Z (`manifest.json`, 3,061 files). After the run and the analysis, all 3,061
entries still match. The single trial followed `PHYSICAL_RUN_PLAN.md`, as amended for the host by
`HOST_NOTE_gpu5070ti.md`. Dr Sun decided to run it on gpu5070ti after the port was validated
(`hosts/2026-09-29_gpu5070ti/PORT.md`) and reviewed in five rounds.

**Outcome:** the trial failed the Building review.
- **Where it stopped:** it climbed both flights and stood at the upper corridor entry. That is where v32's trial
  stood, as expected while the wrong-height navigation cell stays unfixed until v34.
- **How it ended:** after 1,000 failed replans, SCAN gave up (`native_replan_exhausted`), at 459.7 s of physics.
  That end was not among the plan's expected ones.
- **The gate:** it never tripped, and no pose gap came near it. The longest interval between body-pose callbacks
  was 69.7 ms. By the pre-registered exposure rule, the run therefore says nothing about how v33's gate tolerates
  stalls.

## The run

- **Run:** `v33_historical_full01` on gpu5070ti.
  - **The runner:** `hosts/2026-09-29_gpu5070ti/v33_trial_run.sh`, sha256 `2649f0e8…`, the version the fifth
    review round confirmed. The flags were `PHYSICAL_RUN_PLAN.md`'s, unchanged.
  - **Start and length:** the launcher started at 20:51:07Z. `run_bounded` recorded exit 1 after 951.4 s, not
    timed out.
  - **Why exit 1:** it is the worker's exit for a route that does not finish ("Long route did not finish;
    original outcome is retained in result.json"). The worker's `finally` block ran, so all its records exist.
- **Before physics:**
  - The runner's quiet-host checks passed, with no refusal.
  - The pre-physics gates passed: the v33 manifest, the 99 records and the native build's two manifests. P1 had
    re-checked them on the execution copy just before (`checks_out/p1_gates_attempt03.json`).
  - **Physics began:** `factory_full_rate.npz` holds 11,020 records. The run is therefore the outcome under Dr
    Sun's rule for infrastructure failures, and there was no retry.
- **After the run:**
  - The runner found no container left.
  - Its manifest listed 4,597 files and passed its own check.
  - The copy on this Mac verifies against it: all 4,597 files, with none extra and none missing.
  - Nothing was aborted.
- **The host during the run** (`analysis/host_summary_v33_historical_full01.json`, from the Linux sampler):
  - **Sampler:** 950 samples over 952 s, all within 1.005 s of each other.
  - **Load:** the 1-minute load averaged 2.44 (median; at most 3.08). The busiest CPU ran at 95–100%, which is the
    physics worker.
  - **Pressure:** the largest share of an interval with a task stalled on CPU was 21%, and the CPU avg10 peaked at
    5.1%. Memory and I/O pressure stayed at or below 0.3% and 4.2% of an interval.
  - **Memory:** no swapping, and at least 27 GB stayed available.
  - **No git process** appeared at any point.
  - **Busiest processes:**

    | Process | CPU time | Peak |
    |---|---|---|
    | the worker | 1,067 s | 197% |
    | SCAN's planner node, replanning while the robot stood | 877 s | 102% |
    | the container's Python processes | 398 s | — |
    | clash-verge's WebKitWebProcess (another user's) | 29 s | 7% |

    CPU time is a lower bound, counted only while a process was among the ten busiest.
  - **Brief ones:** a C++ compiler (`cc1plus`) ran for about 2 s early in the start-up, just before the factory
    controller appeared, and that controller then ran under emulation during the start-up. The recorder's
    `journalctl` also appears.

## The Building review: `passed=false`

- **Failing:** `common_interface`, `native_arrival`, `driver_arrival_and_pd`, `goal_xy` and `goal_floor_clearance`,
  the same five as v32.
- **Passing:** among others, `no_fall`, `continuous_physics`, `automatic_native_layers`, `historical_route_length`,
  `correct_goal_level`, `original_pd_gains` and `final_pd_two_seconds` (426.3 s of final PD hold).
- **Local review:** it fails `process_completed` and `bounded_driver_completed`, as for v31 and v32. Its source
  checks found no mismatch among 36, 99, 97 and 515 files.
- **Run size:**
  - **Length:** 461.81 s of physics in 22,425 control steps, over 951 s of wall time. That makes it the longest
    trial so far; v32's ran 286.48 s.
  - **Peak memory:** `process.json`'s `child_peak_rss_bytes`, 1,494,784, is in KiB on Linux (host note), so
    1.43 GiB.
  - **Paths:** 9.82 m of actual XY path and 10.47 m of navigation path, with 12 moving curves.
  - **Result:** goal XY error 6.83 m, no arrival and no fall.
- **Motion** (`video_states.json`):
  - **Climb:**

    | Body z | v33 | v32 |
    |---|---|---|
    | 0.90 m | 19.34 s | 19.26 s |
    | 1.40 m | 24.22 s | 27.90 s |
    | 1.65 m | 27.98 s | 33.25 s |
    | 1.80 m | 31.97 s | 35.17 s |

  - **Stop:** from 32.61 s on, it stayed within 0.1 m of (−4.865, −3.422, body z 1.848) at the upper corridor entry.
    That is 0.05 m from where v32's trial stood.
  - **Stance:** `STAND_SETTLING` at 33.25 s, `STAND_TRANSITION` at 33.49 s, then `FIXED_STAND` (the PD stance hold)
    from 35.49 s to the end.
  - **Timing on this host:** the climb ran faster in physics time than on the MacBook. The physics is numerically
    different (PORT.md, P5), so the difference is not attributed.

## How the trial ended: SCAN's replan limit

- **The sequence (measured):**
  - SCAN counts failed replans without a success in between. The planner configuration sets its limit,
    `fsm.max_replan_fail_count`, to 1000.
  - At 21:06:52Z SCAN logged "Replan failed 1000 times; emergency stop and wait for a new target"
    (`scan_replan_fsm.cpp:1014-1022`). It stopped and published its admission as rejected, with the reason
    `native_replan_exhausted`.
  - The backend's stop flow then started, as a fault, at 459.71 s of physics. The goal failed with the cause
    `native_replan_exhausted`, and physics ended at 461.81 s.
- **Against the plan:** `PHYSICAL_RUN_PLAN.md` expected the stand to end at the 600 s physics bound or the 1500 s
  goal wall budget. It listed only those and the gate's faults. This SCAN limit ended the stand first, after
  about 427 s of standing (from 32.6 s).
- **v32's trial** stood for 245 s and logged no such warning before its `odom_stale` end.
- **SCAN's failures while standing differ from v32's** (`runs/<run>/trial_signatures.json`, and
  `analysis/corridor_entry_curves_v33_historical_full01.json` from v32's unchanged script):

  | SCAN log, whole run | v33 | v32 |
  |---|---|---|
  | "The robot is inside an obstacle" (B-spline optimizer) | 6,000 | 10 |
  | "Ran out of pool" (A* search) | 9,012 | 1,105 |
  | final-check collision rejections | 7 | 2,138 |
  | clear final checks | 12 | 12 |

  - **In v33:**
    - The inside-obstacle messages ran from 33.23 s to 459.71 s of physics.
    - All 6,000 are followed by A* errors: "Ran out of pool", then "Unable to handle the initial or end point,
      force return!".
    - 9,000 of the 9,012 pool errors repeat at three indices, 3,000 times each.
    - None of the 7 final-check rejections had its first colliding sample in the wrong-height cell (47, 41).
  - **So:** from almost the same standing place, v33's replans failed in SCAN's search, which placed the robot
    inside an obstacle. v32's replans produced curves that the final check rejected at that cell's western edge.
  - **Not examined:** why the robot is inside an obstacle there. Whether 5 cm of difference in the stand explains
    it, and how the wrong-height cell is involved, are left to v34's diagnosis.

## The gate (v33's change)

From `analysis/trial_analysis_v33_historical_full01.json` (`analysis/trial_analysis.py`, written and checked
before the trial; see Records).
- **The simulation base was active throughout:**
  - `odom_time_base` was `simulation` in all 4,485 status samples;
  - `sim_clock_s` ran from 11.08 s to 461.78 s, with no backward event.
- **Pose ages:**
  - `last_body_pose_sim_age_s` was at most 0.0101 s (p99 0.0), and never negative;
  - `last_body_pose_age_s`, the wall age, was at most 0.068 s (p99 0.017 s).
- **Body-pose callbacks:** there were 81,733.
  - Their wall gaps were at most 0.0697 s (p99 0.030 s), and their simulated gaps at most 0.0201 s.
  - No wall gap exceeded 0.25 s.
- **Exposure:**
  - There was no pose wall gap over 0.25 s, so no gap was exposed, unknown or flagged.
  - There was no terminal gap either: callbacks continued past the stop flow's start, to the last physics step
    (stamp 461.81 s).
  - As pre-registered, the run says nothing about the gate's tolerance of stalls.
- **The gate's faults:** no `odom_stale`, `heartbeat_stale`, `initial_heartbeat_missing` or
  `applied_evidence_stale`. The only stop flow was `native_replan_exhausted`.
- **What this does show:** over 450 s of control on this host, the simulation-time rule did not trip without a
  stall, and the backend ran with `/clock` subscribed. It is not evidence about stalls: v32's wall-clock rule would
  not have tripped here either.

## Watched

- **Clock sync** (`analysis/analysis_v33_historical_full01.json`, `analysis/ttl_windows_v33_historical_full01.json`):
  - **Samples:** 46,927, of which 6 were rejected after convergence (median round trip 23.6 ms).
  - **One TTL window:** 259 ms without an accepted sample. The client's longest gap between sends inside it was
    also 259 ms, so the clock thread did not run.
    - It ended 0.01 s before the first applied snapshot (physics 11.04 s), as the factory start-up handed over to
      the control loop.
    - No control step over 150 ms overlapped it, and it left no pose gap.
    - Its cause was not examined.
  - **Not comparable with v32:** clock results here are not comparable with v32's, because the container shares
    this host's clock (host note).
- **Control steps:** median 38.7 ms, p99 44.5 ms and at most 49.5 ms of wall time; none over 150 ms.
- **Command transport:** one connection, no reconnect, 44,448 frames, no protocol or I/O error, and 5 coalesced
  frames.
- **The bridge's diagnostics** at the end:
  - **Stalls:** one `simulation_clock_stall_events` (v32: 2), and `trial_fault_latched` false.
  - **Body states:** none stale or missing, no sequence regression, and 7,967 superseded before delivery (v32:
    10,856).
  - **Warnings:** "Dropping a backward simulation timestamp" appears once per status sample, as in v32 and P6.
    The only other warnings are the two stream resets as the worker ended.

## Claim boundary

- **Numerics:** the physics on gpu5070ti is numerically different from the MacBook's (PORT.md, P5). The
  comparisons with v32 above are qualitative: where the robot stood, how the run ended, and what SCAN logged.
- **Timing and the clock:** results about timing and the clock describe this host only (host note).
- **Stalls:** the pose path never stalled, so the gate's behaviour under stalls is untested. What v33's change
  does under stalls rests on its component checks K1–K5 (`COMPONENT_RESULTS.md`) alone.
- **Navigation:** the failure at the corridor entry is v34's subject. SCAN's inside-obstacle failures there are
  measured, not explained.
- **Labels:** v33 is still `frozen_unvalidated`. A version increment is not acceptance, and v3 remains the last
  accepted navigation condition. No MacBook result is replaced or reproduced.
- **Known inaccuracies in the run's own records**, as `PHYSICAL_RUN_PLAN.md` and the host note list them:
  - `episode_request.json` carries the fixed watchdog text;
  - `child_peak_rss_bytes` is in KiB;
  - `input_identity.json` names the MacBook's worker environment;
  - `container_command.json` keeps the Docker form, and the podman arguments are in
    `host/v33_historical_full01_docker_calls.txt`.

## Records

- **Run and host files:**
  - the run is `runs/v33_historical_full01/`;
  - the runner's files are in `host/`: `_runner.log`, `_prerun.txt`, `_host.jsonl`, `_docker_calls.txt`,
    `_postrun.txt`, `_SHA256SUMS.txt` and `_manifest.log`.
- **Credential check, counts only.** The checker flagged 1 line in `host/`, a false positive of its own rule.
  - The line is a sampler line that names `cloudflared` as a process and holds 10 long runs.
  - All 10 are path segments in the invoking user's own command lines: the trial's own commands, the container's
    Python processes under the experiment directory, and a path in the controller process's command line.
  - The line's two other-user entries have no command line.
- **Analysis outputs**, in `analysis/` unless stated:
  - `trial_analysis.py`, checked before the trial:
    - on the port's P6 run and on v32's trial, where it matches `evidence/clock_lead_survey.json`;
    - on two synthetic copies of v32's trial with callbacks removed (`check_trial_analysis.py` and `.json`,
      passed), which exercise the flagged, exposed and terminal-gap paths.
  - `host_summary.py`, checked before the trial on a dry-run record.
  - Three tools that write a fixed file beside themselves were run with their output directory redirected to
    scratch: `ttl_windows.py`, `analyze_runs.py` and `corridor_entry_curves.py`.
    - Their outputs were copied here under run-named files.
    - Run the same way on v32's trial, the first two reproduced its recorded files byte for byte.
    - The pinned and committed outputs they would otherwise overwrite were hash-checked before and after, and are
      unchanged.
  - `runs/v33_historical_full01/trial_signatures.json` comes from v31's unchanged `trial_signatures.py`.
- **The reviews ran on the execution copy.** The run records the native build's path on gpu5070ti, which the
  local review re-hashes.
  - The first attempt on this Mac failed on that path, and the first on gpu5070ti failed because the copy had no
    `validation/` directory. Both logs are kept as `analysis/*_mac_attempt01.log` and `*_host_attempt01.log`.
  - The second attempt wrote `validation/v33_historical_full01_review.json` and `_building.json`, and the logs
    `runs/v33_historical_full01/review_stdout.log` and `building_review_stdout.log`.
  - All four are identical on both hosts.
- **Videos:** see below.
- **v33's manifest,** re-verified after the analysis: 3,061 files and 0 mismatches.

## Videos

Rendered on this Mac after the copy was verified, with the unchanged renderers, as for v32.

- **Standard view:** `output/2026-09-27_lite3_versions/v33_historical_full_native_replan_exhausted.mp4`.
  - **Render:** from `runs/v33_historical_full01_video01`. The executed renderer and scene scripts and
    `appearance.json` are identical to v32's render.
  - **Receipt** (`video_receipt.json`): 5,743 frames at 12.5 fps, and the full decode passed.
  - **Frames checked by eye:** 240, 406, 1,872 and 5,742, at 19.34, 32.61, 150.00 and 461.79 s. They show the
    climb, the arrival at the corridor entry with the route turning left, the stand in `FIXED_STAND`, and the end
    with "Navigation: failed (native_replan_exhausted)". The robot is visible throughout.
- **Heading-follow view** (display camera only):
  `output/2026-09-27_lite3_versions/v33_historical_full_native_replan_exhausted_heading_view.mp4`.
  - **Render:** from `runs/v33_historical_full01_video02`, with its own receipt.
  - **The renderer:** both executed scripts are identical to v32's heading view. `heading_camera.json` differs
    only in its run-derived frame count and per-frame cameras.
  - **The same four frames** show the same states.
- **Local-only bytes:** the two renders' frames and in-run MP4 duplicates are listed with SHA-256 in
  `LOCAL_ONLY_BYTES.json` and `runs/v33_historical_full01_video02/LOCAL_ONLY_BYTES.json`, with the trial's raw
  captures: 4,501 files and 1.92 GB, preserved at their paths and ignored by exact entries.

## Status

- **Stage:** experiment and analysis. v33's trial is complete and analysed.
- **Next, per Dr Sun's plan:** v34, the corridor's wrong-height cell.
- **For v34's diagnosis:** this trial adds SCAN's inside-obstacle failures at the corridor entry and the replan
  limit that ended the stand.
- **Nothing is committed.**
