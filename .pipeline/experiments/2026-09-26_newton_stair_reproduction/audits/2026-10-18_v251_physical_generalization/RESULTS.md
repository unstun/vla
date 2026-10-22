# Frozen v251: three single physical route attempts

Stage: experiment + analysis, 2026-10-18. Native treatment **v251**, execution
binding **v252**, unchanged frozen v248 mission bridge. Host: gpu5070ti.

**G07 and R11 pass the original complete-route and measured terminal-PD gates.
A02 fails before route movement with `pct_no_route`.** Each case received
exactly one formal physical attempt. No algorithm, policy, endpoint, hard
threshold or scanner change was made during this cohort; there were no retries.

## Physical outcomes

| Case | Formal attempts | Outcome | Recording ends, physics s | Final goal XY error | Final measured PD suffix |
|---|---:|---|---:|---:|---:|
| A02, oblique ascent entry | 1 | FAILED: global search has no route | 19.781 | Goal not reached | Not a goal hold |
| G07, new upstairs destination | 1 | FINISHED; full-route gate PASS | 137.810 | 0.1174 m | 4.411 s, PASS |
| R11, reverse descent | 1 | FINISHED; full-route gate PASS | 119.506 | 0.1314 m | 4.298 s, PASS |

The original verifier checks the unchanged scenario/spawn and actual goal
payload, zero-step initial state, increasing continuous physics time, no fall,
shared-state consistency, native FINISHED, endpoint XYZ/yaw and measured PD.
G07 final height/yaw errors are 0.00635 m / 0.05335 rad; R11 errors are
0.00857 m / 0.10845 rad. All original numerical tolerances remain in force.
No physical fall or native process crash occurred. A02's normal FAILED closure
completed promptly rather than idling to the 600 s recording limit.

The table reports physical recording end times, not MP4 durations. First actual
`arrived=true` driver observations occur at 135.776 s and 117.447 s; recording
continues through the original completion/stand closure. An outer process
exit code of zero is not used as a navigation-success criterion.

## Planning, pauses and margins

Planning and pause denominators run from measured goal request through first
actual arrival, or the last preterminal driver observation on failure. Low
speed means measured horizontal speed below 0.05 m/s at the original 20 ms
telemetry cadence. Planning wait remains included; final goal PD is separate.

| Metric | A02 | G07 | R11 |
|---|---:|---:|---:|
| Completed local rounds, successful / total | Not reached, 0/0 | 3263/3294 | 2695/2709 |
| Local success within this trial | N/A | 99.06% | 99.48% |
| Whole-navigation pauses >=0.5 s / >=1 s | 1 / 1 | 2 / 2 | 2 / 2 |
| Full cross-floor pauses >=0.5 s / >=1 s | Not reached | **0 / 0** | **0 / 0** |
| Emergency spline publications in navigation | 0 | 0 | 0 |
| Native hard-support Free samples / samples | 64/64 | 1235/1235 | 1052/1052 |
| Minimum gap-aware ENV extra edge margin | 0.00728 m | 0.08753 m | 0.10273 m |
| Minimum independent raw-cloud solid margin | >=0.15 m, capped | 0.09808 m | 0.09180 m |

The two long low-speed intervals in each successful route are the initial
planning/motion wait and final goal settling/stand sequence. There is no
>=0.5 s intermediate low-speed interval. These intervals are retained, not
removed to improve the headline count. The full cross-floor windows are
29.755–110.571 s for G07 and 33.513–106.993 s for R11, including platforms.

The earlier failed G07 body location is independently revisited as a diagnostic
measurement window: within 0.6 m of the original exact failure position
(7.710203648, 6.484551907, 3.355505943), current samples occur at
72.292–74.291 s. All 21 native samples are Free; minimum gap-aware extra edge
margin is 0.1380 m. The closest measured pose is 0.1186 m away at 73.191 s.
This region lies within the zero-pause full floor-transition interval. The
coordinates are an analysis reference only and never enter planner code.

Fixed raw windows are retained separately:

| Raw window | A02 | G07 pauses >=0.5 s / >=1 s | R11 pauses >=0.5 s / >=1 s |
|---|---|---:|---:|
| 45–55 s | Not recorded | 0 / 0 | 0 / 0 |
| 109–115 s | Not recorded | 0 / 0 | 1 / 1 |

R11's latter low interval begins at 112.890 s in the terminal approach/stand
sequence; it is not a staircase stop. The corresponding 109–115 s raw clip
contains 2.110 s of low motion. A02's unrecorded windows are N/A, not evidence
of zero stops. Geometry-relative windows and raw time windows are not exchanged.

Local planning remains below sustained 30 Hz: successful wall rates are
25.74 Hz for G07 and 24.84 Hz for R11. Solve p95/max are 33.93/479.69 ms and
36.94/351.80 ms. There are 36 and 33 rounds above 100 ms, respectively; no
round exceeds 1000 ms. The analyzer's `full_qualification=false` and
`sustained_30hz_validated=false` remain unchanged. A high within-run round
success rate is not a route-reliability estimate.

ENV margins are soft and capped at +0.15 m, using v251's shared gap evidence.
Hard support is a distinct verdict. The independent original v224 raw-cloud
oracle uses the same 0.35 m / 0.18 m geometry and conservative voxel padding
0.04330 m; it is separate from native admission, original mesh contact and
future foot coverage. Its extra edge minima for G07/R11 are 0.12158/0.14143 m.
Do not compare old and new ENV minima as if their gap-evidence inputs were
unchanged. Current body margins use the new gap-aware evaluator consistently.

## A02: continuous support passes; discrete search still fails

The actual recorded goal-request body pose is
(-6.110767841, 6.878930569, 0.398654997), yaw -0.785801903 rad. It differs from
the unchanged nominal spawn by approximately 9.3 cm in XY after PD startup.
All 64 navigation-window samples pass native hard support. Thus the previous
SupportGapMask false-positive repair is effective at the actual body pose.

Fresh independent queries through the installed frozen C++ planner reproduce
the distinction without changing either request:

| Input | Continuous native verdict | PCT grid-center XYZ | Grid-center verdict at measured heading | Discovered unique grid nodes | Plan |
|---|---|---|---|---:|---|
| Original nominal | Free | (-6.045315, 6.813189, 0.358030) | Free | 36899 | Pass |
| Actual measured | Free | (-6.145315, 6.913189, 0.358030) | SupportGap(11) | 18 | `pct_no_route` |

There are two unique initially admissible neighboring states for the measured
input, not zero. The observer also reports 18 alias-edge entries; those are
duplicates across stored slices and must not be called 18 unique exits.
The failed search reaches only 18 unique (height-index, X, Y) grid nodes.
This localizes the remaining gap to continuous measured-start versus discrete
search representation/connectivity, before GPMP or final height projection.
It does not prove that a physical escape path exists, and it does not establish
the original mesh truth at every rejected grid-center heading.

The actual mission makes seven internal PCT requests before ordinary Nav2
failure closure; these are within the one formal attempt. No local trajectory
is generated, no endpoint is moved and no threshold is relaxed. No repair of
this newly exposed graph-start limitation is included in this experiment.
Inputs, exact C++ observer/source hashes, individual candidate-edge verdicts
and both fresh-query results are under `results/measured_start02/`.

## Same-case comparison with v248

| Case | Previous v248 physical attempt | Current frozen-v251 / v252 attempt |
|---|---|---|
| A02 | Failed at post-PD SupportGap | Continuous support now Free; graph still no-route |
| G07 | Failed on middle platform | Complete ascent, new upstairs goal and terminal PD PASS |
| R11 | Complete descent at 133.520 s; 4 whole-navigation >=1 s intervals, 2 during floor transition | Complete descent at 119.506 s; 2 whole-navigation intervals, 0 during floor transition |

This is a comparison of complete treatments on the same host/cases, one
attempt each. It does not isolate any single residual as the sole cause, prove
repeatability, or qualify different maps/slopes. The current cohort is 2/3
full-route passes. Broad generalization acceptance is not achieved, and the
selected source/display baseline remains v232/v233.

## Sensor, source and execution checks

- Scanner period and absolute deadline remain 0.1 s. A02/G07/R11 complete
  87/1267/1085 jobs: **2439 total, zero deadline failures**. Maximum measured
  scan latency is 25.834/28.250/29.184 ms. Longer planner solves are not scanner
  jobs and do not redefine the sensor budget.
- Three zero-step package/profile/graph/scanner preflights pass before v252
  freeze. Actual navigation lifecycle ACTIVE is observed before each goal.
- v251 source/install/fixture/evaluator hashes, v248 bridge installation and
  original v232 graph/driver, v237 scanner and v216 RL/PD chain are verified.
  Runtime planner/controller library maps identify v251. Final post-run source
  and binary verification passes, and no owned container remains running.
- RL SHA-256 remains
  `7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b`.
  Radius 0.35 m, offsets 0.18 m, requested scenario bytes and original
  arrival/PD rules remain unchanged. No 40901 operation or peer-job change.
- Native manifest SHA is
  `a16be7c4d6064a0af79865ca948908a22116f48eb79fe5ecbfdcb4bc08a6e158`;
  execution manifest SHA is
  `c405a6d17c3c837e324c28a45746cb82541bb967a0cad492eb64f069c4a45456`.

## Delivered media and retention

All three complete recorded attempts are regular local MP4 files in
[delivered/](delivered/README.md), including the A02 failed prefix. They retain
startup, planning wait, all pauses and terminal/failure closure. A failed
attempt is never labelled a completed route. Rendering advances zero physics.
Remote causal verification checks every output frame, source indices, event
availability, first/last recorded states, terminal labels and full decoding.
Local files are hash/frame-count/full-decode checked and representative startup,
stair/platform and terminal images are inspected.

The first display pass failed on an inherited manifest-path convention; the
second rendered successfully. Visual QA then shortened only the version title
to keep clock/status text visible. Final delivery is render03. Earlier display
roots, code and logs are retained. These display passes never rerun physics or
change its recording. The physical cohort remains exactly three attempts.

Raw roots are
`gpu5070ti:/data/sun/vla_mppi_20261009/trials/v252_{CASE}_attempt01/runs/v252_{CASE}_attempt01`.
Original recorder retention archives remain there with SHA-bound member
inventories. Full raw clouds, state streams, arrays, verbose native logs and
build/runtime caches remain remote. Finished review videos and compact reports
are returned through the explicit `return_manifest.json` allowlist. No old
evidence or unrelated build is deleted; /data retains approximately 11 GiB free.

Reanalysis uses the pinned worker Python and `postprocess_case.py` on the
closed captures; render-only passes use separate `V252_RENDER_ID` roots.
`raw_pose_audit.py` retains the original independent oracle. `measured_start/run.py`
does fresh offline queries only. Never rerun `run_three.py` for this cohort:
the launch-once ledgers already exist. No commit, task archive or baseline
promotion is performed in this follow-up.

Compact machine-readable results: [SUMMARY.json](results/SUMMARY.json),
[SUMMARY.csv](results/SUMMARY.csv), [local quality](results/local_quality.json).
