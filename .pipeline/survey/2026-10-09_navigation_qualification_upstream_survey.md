# Navigation qualification against 18 upstream repositories

Date: 2026-10-09. Stage: experiment + analysis. Evidence status: **surveyed**.

## Revised assessment

The evidence does **not** support a universal rule that a system is unqualified
if any local solve fails, any round exceeds 60 ms, or trajectory updates are
below 30 Hz. Published systems use different planning horizons, controllers,
task difficulties and evaluation definitions. Their numerical results are not
interchangeable acceptance thresholds.

Our current system is an implemented research prototype with measured
millisecond-scale nominal planning and a demonstrated complete navigation run,
plus a later failed run. Its **comparative mission reliability remains ungraded**.
The failed episode and search/freshness coupling remain real defects to
investigate, but do not establish a ranking below other open-source projects.
The previously stated blanket external verdict was too strong. The project's
own sustained-30-Hz acceptance remains unmet; this survey does not change it.

## Coverage and evidence quality

Inspected **18 public repositories**, with 63 selected README/license/source/
configuration/test files checked against recorded hashes: 15 implementations or
frameworks, plus 3 benchmarks. SCAN, EGO and EGO-v2 have related algorithmic
lineage; Nav2 contains multiple plugins. They are not 18 independent equivalent
baselines. PCT is a global-planning reference, and aerial systems provide
architectural comparisons, not direct quadruped performance rankings.

The implementation set is SCAN, PCT, ArtPlanner, CMU Go2, ViPlanner, FDM,
SanD-Planner, field_local_planner, EGO, EGO-v2, Fast-Planner, FASTER, TEB,
Nav2 and ROS navigation/DWA. The benchmarks are Arena-Bench, the BARN challenge
runner and FlightBench. Each has a source-linked observation in the
[18-row comparison](../../references/upstream/2026-10-09_navigation_qualification/comparison.md).

[Inventory](../../references/upstream/2026-10-09_navigation_qualification/inventory.json)
records canonical URL, inspected commit, branch, API license detection,
maintenance metadata, platform/interface, original README command excerpts,
source links and inspection limits. API `NOASSERTION`/missing licenses are
retained as uncertainty. Current Nav2 main is a comparison reference; our runtime
continues to use Foxy 0.4.7, pinned separately at
`a947ab5656e46ae3aa1afdf95e1706a16e478974`.

Primary papers and the FlightBench results site were inspected for the numbers
below. Issues were not used as qualification thresholds. None of the 18 systems
was newly built or run here; no weights, datasets or simulator assets were
downloaded. Source retrieval is not a reproduction.

## What the comparisons actually show

| Source | Verified evaluation or behavior | Consequence for this assessment |
|---|---|---|
| [SCAN paper, VI-A and Table II](https://arxiv.org/html/2606.19555v1#S6) | 50 independent trials per scene; 120 s timeout; Intel i9-14900K; SR, collision rate and SPL. Dense-obstacle SR: SCAN 100%, EGO-2D 96%, CMU 92%. These are the SCAN authors' configurations/results. | Judge complete tasks under a declared protocol. The paper does not establish a universal 30 Hz or 60 ms rule. |
| [ArtPlanner paper, 2.1 and 3.1.5](https://arxiv.org/html/2303.01420) | Deployment target 0.5 Hz; target update time met in 75% of cases. Maximum planning time 4.65 s; the scenario-derived real-time threshold was 4.44 s. The released YAML separately defaults to 1 Hz. | Planning rate depends on map extent, travel speed and path-following architecture. This does not make a 4 s delay acceptable for our short-lived local curve. |
| [FDM paper, Table III](https://arxiv.org/html/2504.19322v1#S6) | MPPI with learned FDM reports 88.33% success in 2D and 73.75% in 3D; the 3D heuristic baseline reaches 33.13%. | Research comparisons include unsuccessful missions. Less than 100% alone does not invalidate a research contribution; difficulty and baselines matter. |
| [SanD-Planner paper, V-B](https://arxiv.org/html/2602.00923v1#S5) | 2020 ClutteredEnv episodes and 4040 InternScenes episodes; SR 90.1% and 72.0%, respectively, with SPL also reported. | Thousands of episodes support a generalization claim; our two observed outcomes cannot provide comparable statistical evidence. |
| [ViPlanner paper, VI-A](https://arxiv.org/html/2310.00982#S6) | 500 random start-goal paths per environment; goal attainment tolerance 0.5 m. Semantics-model goal attainment varies by environment; the paper also describes a 10 Hz planner with slower asynchronous semantics. | Predicted-path attainment and full physical mission success are different metrics. Neither implies a universal 30 Hz requirement. |
| [FlightBench paper, IV](https://arxiv.org/html/2406.05687v3#S4) and [results website](https://thu-uav.github.io/FlightBench/#additional-simulation-results) | Ten independent runs per metric, i9-11900K/RTX3090 simulation. In the hard maze, EGO SR is 20% and Fast is 60%; EGO reaches 100% in the reported forest case. The website's maze-test-3 average planning times are EGO 3.552 ms and Fast 8.918 ms. | One algorithm's success changes sharply with difficulty. Millisecond planning and low mission success can coexist. These are different robots/hardware/scenes from ours. |
| [Arena-Bench paper, III-C / IV-B](https://arxiv.org/html/2206.05728) | 15 repeats per planner/scenario in simulation and reality; collision, duration, path length and smoothness metrics. Its table defines success using fewer than two collisions. | Even the word “success” is not standardized. Do not equate this definition with a zero-collision mission. |
| [BARN runner](https://github.com/SlyPredator/the-barn-challenge/blob/7c720261eecb41f92994ec0f208f5e25b9b37ac8/run.py) | The inspected runner records collision, timeout and arrival separately; goal distance 1 m and timeout 100 s after movement starts. | Whole-task outcome and traversal efficiency drive scoring. Goal tolerances, startup accounting and scoring implementation must be matched before comparing. |

The BARN organizer page could not be fully fetched during this audit (web
timeout and local certificate-chain error); no leaderboard rank is used. The
runner above is the inspected repository, not a claim that its implementation
exactly matches every current organizer rule. `run.py` and `report_test.py` also
use different score clipping constants in this pin, so no score was calculated.

## Failure and recovery patterns verified in code

- SCAN/EGO retry initialization and have explicit failure/emergency states.
  EGO-v2 and Fast-Planner likewise retry after unsuccessful generation.
- CMU reduces path scale/range; exhausted candidates produce a one-point path.
- TEB rejects infeasible output, resets, and can use a shorter horizon.
- Current-main Nav2 MPPI resets/retries before reporting `NoValidControl`;
  Nav2's system test ultimately checks the navigation action's success.
- ROS navigation/DWA can reject every candidate and stops on stale costmap data.
- ArtPlanner separates invalid input and no-solution feedback from solved paths.
- FDM separates planning from faster path-following; ViPlanner exposes risk
  status and timing; field_local_planner makes output validity explicit.

Each statement links to the pinned code in the inventory. These mechanisms
demonstrate anticipated failures, not a measured upstream failure frequency.

[FASTER's paper, III-E](https://arxiv.org/html/2001.04420#S3), is especially relevant:
under its free-space and committed-trajectory assumptions, infeasible or late
replanning keeps the previous committed trajectory, which includes a safe stop.
Its code returns before replacing the committed plan when JPS or either
optimization fails. This is an architectural reference, not permission to keep
executing our curve after its current collision/freshness proof expires.

## Our measured evidence, kept on its original denominator

Source: [v116 attempt02 metrics](../experiments/2026-09-26_newton_stair_reproduction/versions/v116/analysis/attempt02/metrics.json)
and [six-spike attribution](../experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-09_over60ms_diagnosis/REPORT.md).

| Metric | Measured value | Interpretation |
|---|---:|---|
| Completed ordinary planning rounds | 900 | All timings included, including failed rounds. |
| Successful rounds | 895 / 900 = 99.44% | Correlated rounds inside one mission, not 900 independent navigation tests. |
| Mean / median solve | 2.632 / 1.580 ms | Millisecond-scale complete native round; does not include all sensing/mapping latency. |
| P95 / P99 solve | 4.081 / 17.652 ms | Describes the ordinary round distribution, not mission reliability. |
| Maximum solve | 138.782 ms | Six rounds exceed 60 ms (0.667%); three exceed 100 ms. |
| Successful rounds / total navigation wall time | 16.726 Hz | Whole-window rate includes stops and recovery periods; not active-loop scheduling frequency. |
| Latest mission | FAILED | 23.561 m measured travel, no fall recorded, longest pause 10.494 s. No-fall does not establish collision safety. |
| Earlier native-v114 mission | Arrived and measured stop | One success exists; subsequent recorder/version context differs, so do not publish a pooled “50% success rate”. |

The earlier outcome is documented in the
[v114 runtime report](../experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-08_nav2_sim_repair/REPORT.md).

Relative to the reviewed evidence:

1. **Computational scale:** not sufficient evidence to call our nominal solver
   abnormally slow. Its values share the millisecond scale of some external
   results. Different scopes/hardware prohibit claiming that we outperform them.
2. **Handling unsuccessful candidates:** retries and protected stops are standard
   design patterns in the inspected sources. Their existence is not itself a
   defect. Unnecessary retries and delayed sensor ingress/adoption remain a
   measured concern in our implementation.
3. **Mission reliability:** unresolved statistically, with a concrete failed
   episode. Replacing task SR with 99.44% round acceptance would be invalid.
4. **Research evaluation quality:** insufficient for a comparative reliability
   claim. We need repeated complete trials over declared scenarios and common
   baselines, rather than an anecdotal success or failure.
5. **Deployment qualification:** not established; no Jetson/real-robot result is
   added by this survey.

## Appropriate next comparison

First replay the failed search inputs against pinned upstream SCAN and our
version, preserving map/start/target/clock semantics. Then use a prospective
scenario suite with repeated complete tasks, including the current route,
corner/narrow passage, obstacles, recovery, and stairs. Record task SR,
collisions/falls, timeout/abort, SPL or relative path length, completion time,
stop duration, and compute/freshness distributions together.

Choose baseline interfaces that actually support each scenario: original SCAN
is the closest comparison; CMU is a useful ground-navigation control. A planar
Nav2 controller may be compared on the common flat subset, not penalized for an
unsupported 3D stair task. Keep robot, locomotion, sensing, map availability,
hardware, start/goal and tuning budget common. Retain every failure and report
uncertainty over independent missions. There is no evidence here for inventing
a universal 95% threshold or requiring every research trial to succeed.

No implementation, benchmark run or acceptance relaxation was performed.

## Audit artifacts

- [Pin/source manifest](../../references/upstream/2026-10-09_navigation_qualification/repository_manifest.yaml)
- [Hash and scope checks](../../references/upstream/2026-10-09_navigation_qualification/quality.json)
- [Collection / inventory scripts](2026-10-09_navigation_qualification_sources/)

All downloaded code remains a reference; no upstream source was executed.
