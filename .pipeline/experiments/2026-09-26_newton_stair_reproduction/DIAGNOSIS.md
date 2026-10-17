---
origin: ai_only
reviewed: false
date: 2026-09-26
---

# Why the displayed trajectory stops or disappears

Stage: **experiment + analysis**. This is a diagnosis of the immutable
`stair_native_walk_v2` run, not a navigation repair or a new successful run.
Production tracker/planner thresholds, the native build and old evidence are
unchanged. Remote Isaac remains stopped.

The planner did publish two moving curves. A short perception interruption
replaced the first with a stop curve. The next moving curve had a 34.250 s
duration; the execution ended in `command_timeout` before it could finish.
The final stop messages have coincident control points, which explains why
the displayed curve collapses to a point. These are separate mechanisms.

## 1. Reproducible perception failure

`diagnose_tracker_replay.py` feeds all 280 saved measured clouds, received ROS
poses and the hash-verified physical-ground payload through the unchanged
`StaticForegroundTracker`. Both repeated runs match all 280 live snapshots
in completeness, count, IDs and centers (within 1e-6 m). Their complete replay
JSON files are byte-identical. The local replay uses NumPy 2.5.3 / SciPy 1.18.1;
matching outputs establish this replay's observed parity, not general parity
with the original container's SciPy 1.8.1 environment.

The ranked hypotheses were: (1) partial shape rejected by existing size gates;
(2) background subtraction removes the human; (3) association fails despite
valid candidates; (4) path geometry causes global timing expansion. The first
three were tested against the captured failure frames before any repair.

| Scan time (s) | Human ray hits, scoring only | Foreground points | Points after height filter | Candidate height span (m) | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| 12.801543 | 172 | 168 | 149 | 0.9069 | Candidate accepted |
| 12.901584 | 55 | 49 | 17 | 0.1281 | Vertical-span gate fails |
| 13.001624 | 75 | 63 | 47 | 0.1968 | Vertical-span gate fails |
| 13.101665 | 150 | 150 | 126 | 1.3145 | Candidate accepted again |

The gate requires a height span of at least **0.45 m**. Tracing locals in the
original `shape_candidates` function shows that the failing components pass
the point-count and horizontal-span gates and fail only the vertical-span
gate. No candidate reaches association. The confirmed track then yields
`complete=false`, `tracks=[]`, reason `unresolved_or_lost_cluster`.

At 12.962 s, `scan.log:241` reports `reactive_collision_blocked verdict=3`.
In the native `plan_env/reactive_collision.h`, verdict 3 is **MissingInput**.
The subsequent generic “Target is occupied” text does not establish that the
human physically blocked that target. The tracker watchdog's later
`missing_or_stale_paired_sweep` message follows the failed update; it is not
evidence that transport caused these two measured-cloud failures.

Removing static background subtraction does not restore a valid person:
the components merge with static geometry and fail horizontal-span limits.
This counterfactual is diagnostic, not an accepted replacement input.

## 2. Why those scans lose vertical coverage

Frozen-state Newton raycasting reproduces both saved clouds bit-for-bit,
without advancing physics. The same original human animation, triangle scene,
sensor-owner exclusion and Livox scan windows are used. Truth ray labels remain
scoring outputs and are never passed to the tracker.

Each control replaces only the named input with its value from scan 127:

| Control | Scan 128 detections | Scan 129 detections |
| --- | ---: | ---: |
| Recorded state | 0 | 0 |
| Previous scan pattern only | 0 | 0 |
| Previous robot pose only | 1 | 1 |
| Previous sensor position only, current robot geometry | 0 | 0 |
| Previous sensor orientation only, current robot geometry | 1 | 1 |
| Previous roll only | 0 | 0 |
| Previous pitch only | 1 | 0 |
| Previous yaw only | 1 | 0 |
| Exclude four authored-invisible human meshes only | 0 | 0 |

Orientation-only controls restore height spans of **0.973 m** and **0.860 m**.
The failure is sensitive to combined sensor orientation and resulting ray
coverage in this scene. Pitch alone is not a complete explanation. These
artificial ray-pose controls do not establish a correct alternative mount,
calibration, hardware behavior or Isaac sensor equivalence.

The nine-mesh versus five-visible-mesh sensor limitation remains open, but
that change produces identical candidate geometry in these two failing frames;
it does not explain this particular interruption.

## 3. Why the generated curve takes so long

The native logs establish the following initialization timing:

| Moving curve | Sample count | Seed duration (s) | Initialized / published duration (s) | Logged time scale |
| --- | ---: | ---: | ---: | ---: |
| First | 40 | 0.853333 | 8.116368 | 9.511369 |
| Second | 185 | 1.600000 | 34.250242 | 21.406401 |

The local `planner_manager.cpp:279` calls `initializeTimedCubic` before
geometry optimization at line 304. That local helper fits hard endpoint
position, velocity and acceleration constraints, checks native feasibility,
and enlarges the **whole uniform time interval** until feasible. After geometry
optimization, the later stage only lengthens timing if necessary; it does not
recover excess duration when the geometry becomes smoother.

This early expansion is a local addition. The inspected
[SCAN-Planner manager at 348e8a5](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/planner_manager.cpp)
parameterizes at line 249, optimizes at line 263, then checks and refines timing
at lines 276–287. Its source and Apache-2.0 license are pinned under
`references/2026-09-26_trajectory_diagnosis/`. The
[EGO-Planner feasibility implementation at bfda512](https://github.com/ZJU-FAST-Lab/ego-planner/blob/bfda51284c8c1b476043255a8145ef925a3778a5/src/planner/bspline_opt/src/uniform_bspline.cpp)
was also inspected and saved with its GPL-3.0 license; no source from it was
substituted into the implementation.

An isolated C++ probe compiles the unchanged native `UniformBspline.cpp` in
the cached ROS image, with no ROS graph or network. Both published curves pass
the native feasibility check. Compressing their **final optimized geometry**
back into the logged seed duration fails that same check:

| Curve / condition | Maximum velocity-control component (m/s) | Maximum acceleration-control component (m/s²) |
| --- | ---: | ---: |
| First, published timing | 0.126908 | 0.287438 |
| First, final geometry compressed to 0.853333 s | 1.207069 | 26.003418 |
| Second, published timing | 0.101842 | 0.231524 |
| Second, final geometry compressed to 1.6 s | 2.180069 | 106.092177 |

This proves the short timing is incompatible with the recorded final geometry
under the native calculation. It also confirms that the post-optimization
curve retains the early expanded duration. It does **not** reproduce the exact
21.4064 initialization ratio: the original seed point array was not recorded,
and the final optimized control points are different input. The ratio obtained
from the second compressed final curve is 14.5665, not 21.4064. On already
feasible curves, the native ratio output is unused and must not be interpreted
as a required expansion; the probe's raw JSON preserves that value.

Only about 8.4 more physics seconds elapsed after the second curve arrived
before cancellation. The original 35-wall-second execution timeout, CPU
simulation rate and remaining command reconnects are separate limitations.
No evidence here proves that simply extending the timeout would complete
stairs or avoid the human.

## 4. Next work, one change at a time

1. Use these exact two clouds as the regression input. Inspect upstream
   implementations for partial current-observation association and sensor
   coverage handling before selecting a change. Preserve the distinction
   between a new full-shape candidate and an already tracked object that is
   only partly visible. Do not inject predicted positions, use actor truth,
   or treat an unresolved person as clear space. Verify visibility selection
   separately before any sensor parity claim.
2. Capture the exact initializer samples, endpoint derivatives, interval and
   per-iteration velocity/acceleration bounds in a separate diagnostic build.
   Replay the exact 21.4064 expansion, then assess an upstream-backed
   geometry-optimization / time-allocation order while preserving hard endpoint
   PVA, collision checks and native limits. A simple global speed-up is not an
   accepted fix.
3. After those targeted gates pass, run a fresh bounded continuous local loop.
   Separate simulation progress from wall-time transport freshness. Keep the
   original live result failed, and keep Isaac A4 open until independently met.

## Evidence and reproduction

The scripts are in `scripts/diagnose_tracker_replay.py`,
`diagnose_tracker_gates.py`, `diagnose_ray_coverage.py`,
`diagnose_ray_orientation.py`, `diagnose_spline.cpp` and
`diagnose_spline_timing.py`. Each run has a recorded command, deadline, process
result and raw outputs under `runs/`. Run them via `scripts/run_bounded.py`
with a new unique run ID; the old directories reject reuse.

Use the qualified interpreter at
`../2026-09-26_newton_macos_policy/runtime/.venv/bin/python` for replay/rays.
The native timing driver uses the existing pinned Docker image. The optional
summary plot uses a separate environment; its packages do not alter the
physics or replay interpreter. `summarize_trajectory_diagnosis.py` performs
scoped source and artifact verification and writes `tracking_coverage.png`
from actual saved candidate points.

The final review result is linked from `RESULTS.md`. Its pass status applies
to diagnostic evidence only; navigation remains unvalidated.
