# v212: event planning implemented; physical trial failed

**Do not replace accepted v210 with this candidate.** Two affected packages
built on gpu5070ti; all 51 targeted cases pass, including 9 installed-plugin
event/cancel/retry cases. One original-start physical trial was executed, with
no moving retry or navigation tuning afterward.

| Evidence | v210 baseline | v212 candidate |
|---|---:|---:|
| Original full-route gate | Passed | Failed: physical fall |
| Physical duration | 137.005 s | 54.142 s, stopped early |
| Route deliveries in the same first 54.14 s | 39 | 1 |
| Final fixed PD hold | 4.351 s | None at destination; destination not reached |

Route deliveries are observed `/pct_path` outputs, not an instrumented count of
internal PCT solver calls. Different run lengths prevent a completion-time or
whole-route efficiency comparison. Native local planning continues in v212.
The trigger behavior works; the physical acceptance does not.

## Observed failure sequence

At about 52 s, while still en route at roughly (7.8,-3.9,1.85) m, zero command
causes v208 to enter STAND_TRANSITION. Tilt then grows. The controller returns
to RL with `fixed_stand_disturbance:tilt`, and the original fall detector stops
physics at 54.141872 s: base_up_z
0.446535, tilt 63.48 degrees.
This is an intermediate-stop/transfer failure, not terminal stand timeout.
It does not alone establish whether route history, the intermediate support
pose, locomotion transfer, or their interaction is the root cause.

The physical fall occurred before Nav2 wrote a finish request. The shared-state
terminal witness therefore fails, and the outer process exits 1. The raw result
explicitly says fallen=true. No terminal success or PD completion is invented.
The display analysis records shared_state_verified=false while deriving timing
and curves from the closed archive. The original full-route checker stays failed.

## Exact change and checks

Production changes are one BT decorator, its registration, and navigate.xml.
It plans on first/new goal, frame/pose change, and ordinary recovery reset;
stamp-only updates do not replan. Running old-goal planning is canceled before
replacement. The successful-plan cache resets when PipelineSequence sets it
IDLE, as well as on explicit halt. The regression caught and fixed that detail
before the physical run. No deviation threshold or dynamic blockage mask exists.

Six ordinary retries, Wait 1 s, terminal-timeout no-retry, PCT/SCAN/Tracker,
endpoint rules, V12 policy and v208 locomotion are preserved. Same-host archived
request/scenario/planner/parameter comparison passes; generated behavior trees
differ only in RateController versus PlanOnGoalChange. The unrelated 1 Hz
costmap lifecycle update and planner timing diagnostic remain unchanged.

The first component pass exposed the cache reset bug and missing writable ROS
logging directories. The next pass left one obsolete 1 Hz assertion; a focused
recheck initially lacked TERRAIN_TEST_MANIFEST. Those failures are retained.
Final eight test suites contain 51 unique passing cases, no failures/skips.
A 12-second ROS graph preflight and source/binary checks also passed.

[Comparison](results/comparison_v210.json) · [Fall samples](results/fall_evidence.json) ·
[Original gate](results/full_route_verification.json) ·
[Build receipt](verification/remote/receipt.json) · [Frozen source](manifest.json).

Local VLA is authoritative; remote execution copy and build:
`/data/sun/vla_mppi_20261009/repo` and
`/data/sun/vla_mppi_20261009/event_replan_v212`. Original raw archive remains:
`/data/sun/vla_mppi_20261009/trials/v212_linux_full_attempt01/runs/v212_linux_full_attempt01/raw_capture.zip`, 122,148,704 bytes,
SHA-256 `a01ee20ec618fa619fd7000d6bb832ff21d94bf2fb71a1b57c7dfa2db3fc8f5a`, all 435 members verified.
`v212/launch.py` refuses an existing trial output. Reproduce read-only analysis
with `v212/analyze_full.py`, `v215/analyze_failure.py`, and `v212/compare_v210.py`
on gpu5070ti. Full video: v215 (v213/v214 preparation attempts preserved).
