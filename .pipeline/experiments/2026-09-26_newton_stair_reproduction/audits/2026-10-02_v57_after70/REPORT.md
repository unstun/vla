# v57 post-70-second anomaly

Stage: experiment + analysis, 2026-10-02. Scope: the two frozen v57 recordings.
Times below are simulation time on the planning plots, not elapsed MP4 time.
No planner/controller edits, new physics runs or new runtime version were made.

**The slowdown starts when the start–final-goal pair fits A*'s fixed search
pool. Every local round then performs an unsuccessful goal-neighborhood search
before warm initialization. The reachable search region grows as the robot
moves, raising this repeated cost. Occasional cloud processing adds a second
latency band. Longer solves also expose an inherited trajectory timestamp
problem: a starting state sampled before solving is published with a later
start time. The robot gets ahead of that reference, and position feedback
reduces its commanded speed.**

[Diagnostic figure](after70_diagnosis.png), [PDF](after70_diagnosis.pdf),
[verification](verification.json), [native probe](attempt01/result.json).

## 1. The trigger is spatial, not a 70-second timer

The first expensive goal searches after 65 s occur at different times but at
nearly the same corridor position:

| Run | Onset | Planned start Y | Final-goal Y | Y separation |
|---|---:|---:|---:|---:|
| Trial01 | 72.796623 s | 1.958819 m | -2.986811 m | 4.945630 m |
| Trial02 | 69.333527 s | 1.947426 m | -2.986811 m | 4.934237 m |

The native A* pool is 100×100×100 at 0.05 m resolution, with its center aligned
to the start near the start–goal midpoint. Thus it spans about 5 m per axis;
it is separate from the 10×10×5 m rolling occupancy map and 3.5 m local planning
horizon. Before the onset, coordinate conversion returns `INIT_ERR`: the log
reports `Ran out of pool`. Around this position, the pair fits the pool and
full A* expansion begins. This explains the abrupt onset and the 3.46 s offset
between the two recordings.

Source: `planner_manager.cpp:63`, `dyn_a_star.cpp:166–191`,
`dyn_a_star.h:145–160`, and `astar_grid_coordinates.h`. Runtime configuration
is frozen in `versions/v57/building_planner.yaml`.

## 2. The repeated work is before the successful warm start

The actual call order is:

```text
planFromCurrentTraj: sample start PVA from the executing curve
  getLocalTarget
    adjustGlobalTargetIfOccupied: refresh inputs and query final endpoint
      findGoalNeighborhoodPath -> AstarSearch -> empty path
    select a supported frontier on the existing reference
  setWarmStartContext
  reboundReplan: accepted warm guess, optimizer, dynamics and full-curve checks
  updateTrajInfo: assign the current clock as the new trajectory start
```

The final endpoint is still rejected by the current native occupancy model.
Across 70–90 s, no nominal round selects a `reference_goal_neighbor`. The
planner instead falls through to reference-frontier selection and usually
succeeds locally. Warm acceptance remains 464/471 rounds in trial01 and
390/395 in trial02, about 98.5% and 98.7%.

Representative original trial02 rounds demonstrate where the time goes:

| Simulation time | Complete round | Goal search | Cloud callback | Warm-seed scope |
|---|---:|---:|---:|---:|
| 69.993 s | 9.504 ms | 7.675 ms | 0 | 0.502 ms |
| 74.990 s | 20.937 ms | 19.758 ms | 0 | 0.310 ms |
| 80.008 s | 31.458 ms | 29.520 ms | 0 | 0.646 ms |
| 84.985 s | 39.407 ms | 37.481 ms | 0 | 0.810 ms |
| 89.003 s | 82.307 ms | 52.714 ms | 27.152 ms | 1.070 ms |

These are full original rounds, not inferred timings. Inclusive profile scopes
overlap; they must not be summed in general. In particular, cloud draining
inside warm validation can make the warm-seed scope appear slow without a slow
fit or optimizer. See the line-addressed [trial02 evidence](v57_realtime_trial02_evidence.json).

## 3. Why the goal search keeps getting slower

The unchanged native AStar and GridMap libraries were probed at ten captured
states per recording, twice each. All 40 results repeat exactly in outcome and
reached-node counts. The early pool rejections explore zero nodes. Later
searches expand a growing reachable corridor region and return `SEARCH_ERR`.

| Trial02 recorded state | Expanded nodes | Offline search time, first repetition | Returned path |
|---|---:|---:|---|
| 65.001 s | 0 | 0.053 ms | Empty; pool rejection |
| 69.993 s | 106 | 7.929 ms | Empty |
| 71.997 s | 228 | 14.166 ms | Empty |
| 74.990 s | 359 | 19.505 ms | Empty |
| 80.008 s | 534 | 29.158 ms | Empty |
| 84.985 s | 653 | 36.185 ms | Empty |
| 89.003 s | 691 | 43.672 ms | Empty |

Trial01 independently grows to 615 expanded nodes and a 36.815 ms replay
search. At the final sampled trial02 state, reached nodes span Z=3.360–3.460 m,
while the goal is at Z=4.831 m. The closest reached node remains 4.606 m from
the goal, well outside the 1 m neighborhood. A* has not found the upstairs
connection; it repeatedly exhausts the locally reachable region. The
50-iteration goal-approach phase cannot help when no reached node enters that
neighborhood.

After graph exhaustion, the same exact-endpoint search also sorts the reached
terminal candidates and tries direct connectors to the final goal. This is
additional work inside the same `goal_search` scope, potentially one connector
test per reached candidate. The current profiling does not separate graph
expansion from that terminal-recovery sweep; the measured cost is their combined
native call. Both use the original collision checks and inherited 200 ms search
limit, not a v49 timeout.

The v50 geometric precheck still behaves conservatively. The goal's tolerance
region can intersect its necessary map/lattice bounds, so it cannot certify an
empty region and retains native search. Bounds eligibility is not reachability
or clearance. No precheck rejection occurs in these late live rounds or sampled
native searches. This is a remaining case beyond that optimization's proof,
not evidence that the guard stopped running or changed the final goal.

The probe uses exact logged initial seed positions and the latest observed
route endpoints, original point arrays, original callbacks, and fixed clocks.
It does not reproduce live DDS batching or mid-solve arrivals. Its times are
component measurements; the live table above remains the performance evidence.

## 4. Why there are two latency bands

In the final 85–90 s interval:

| Measurement | Trial01 | Trial02 |
|---|---:|---:|
| Median complete round | 40.696 ms | 50.816 ms |
| Median goal search | 34.194 ms | 44.041 ms |
| Median warm-success round without an in-round cloud | 39.525 ms | 46.565 ms |
| Median warm-success round with an in-round cloud | 65.515 ms | 72.325 ms |
| Median cost per in-round cloud callback | 28.314 ms | 27.205 ms |

Cloud callbacks were already about 30–34 ms before the slowdown. What increases
is their incidence inside measured planning rounds: approximately 3–6% at
65–70 s versus 36–45% at 85–90 s. Longer calls overlap incoming 10 Hz clouds
more often. Some input work also occurs in the executor's entry drain outside
the measured nominal round, so low earlier per-round input averages were not
proof that cloud processing itself was cheap.

The final interval has at most one cloud callback per nominal round. Logged
cloud age remains at or below about 0.20 s before draining and 0.15 s afterward,
inside the unchanged 0.25 s contract. This evidence does not support an
unbounded input backlog or stale-input rejection as the cause.

Goal-search thread CPU time is 99.98%/99.65% of wall time in this interval.
The main delay is CPU computation. GPU utilization, rendering and disk packing
do not explain it: these recordings used the CPU planner, and rendering/packing
occurred after physics. The single-threaded planner skips missed nominal slots
instead of issuing catch-up solves.

## 5. The latency also creates a trajectory-phase problem

The inherited code evaluates the old curve at the beginning of the planning
round, retains that start PVA through the solve, then assigns `node_->now()` in
`updateTrajInfo` after solving. The controller resets `exec_time_` to zero on
each received curve. These four relevant function bodies are byte-identical
to v48: [inheritance evidence](timing_inheritance.json).

We matched consecutive native trajectory IDs to original nominal completion
times and required the new starting position to agree with the old curve at
the round's sampling time within 20 micrometers. There are 604/529 matched
transitions over 65–90 s. In the final 85–90 s subset:

| Observed curve-transition measurement | Trial01 | Trial02 |
|---|---:|---:|
| Matched transitions | 94 | 73 |
| Median sample-to-new-start timestamp delay | 39.978 ms | 59.967 ms |
| Median backward reference-position step at that timestamp | 3.338 cm | 4.868 cm |
| Largest backward reference-position step | 7.058 cm | 8.089 cm |

The fixed-input PVA check still passes: the new curve begins at the requested
old sampled state. But at the later publication timestamp, the previous curve
has advanced. Continuity against an earlier sample does not establish
continuity at the actual time of switching. This is a concrete timing gap,
not a reason to loosen PVA, occupancy or dynamics checks.

The earlier corner-continuity result was bounded to the 39–55 s passage and
observed progress. It did not validate this later time-aligned tracking behavior.

The physical measurements show the associated tracking problem. At 85–90 s,
the median robot lead over the planned starting position is 0.933/0.972 m,
mostly along the direction of travel. Planned initial speed remains about
0.817/0.813 m/s. The controller uses

`v_command_world = v_trajectory + 0.8 * (p_trajectory - p_robot)`.

Consequently its position correction opposes forward travel by roughly
0.747/0.778 m/s at these sampled states. The independently recorded median raw
command speeds are only 0.138/0.086 m/s, while median measured body speeds are
0.217/0.173 m/s. Raw commands continue at 30.001/30.001 Hz, with no zero-
translation commands in that final interval. The planned 0.6 m/s cruise rule
does not impose a minimum on feedback-corrected commands or measured speed.

The phase steps are measured directly from transmitted curve geometry and
timestamps. The position-feedback decomposition uses original seed PVA and
body positions interpolated between 10 Hz samples; it explains sign and scale,
but does not reconstruct the controller's exact internal callback state or
establish the outcome of a repaired closed-loop run.

Sources: `scan_replan_fsm.cpp:1177`, `planner_manager.cpp:519,673`, and
`closed_loop_controller.cpp:283,358–364`. See [motion measurements](v57_realtime_trial02_motion.json)
and [phase-transition measurements](v57_realtime_trial02_phase_lag.json).

## 6. Repair targets and claim boundary

The first target is avoidable final-goal search on the local critical path.
A future repair should prove when this work cannot change the current local
window, or reuse/incrementally maintain properly invalidated search evidence.
It must still reconsider changed goal/owner/map/input conditions and execute
the existing final-goal, yaw, occupancy and support checks when relevant.
Skipping all goal checks or caching a safety verdict is not justified.

The second target is the time alignment of the planned boundary and actual
handover. Tests should compare the old and new PVA at the same handover time,
not only compare the new curve with a state sampled before computation.
Measure physical tracking error and command speed alongside successful Hz.
Do not mask the lag by lowering position gain, forcing a speed floor, widening
goal tolerances, or restoring v49's hard abort/stop approach.

Neither repair is implemented here. Goal, yaw, dynamics, safety and stop rules
remain unchanged. All 7,408 frozen source and 519 installed-file hashes pass.
The native diagnostic completed in 55.865 s under a 300 s external supervisor;
its 20 cases/40 repetitions used fresh recorded inputs and unchanged native
libraries. There were zero physics runs. Raw logs, event streams and build
files remain on gpu5070ti; only compact diagnostic evidence returned locally.

The principal finding is established by both live traces and unchanged-native
replay. Whether a proposed repair restores 30 Hz and tight physical tracking
requires separate implementation and bounded validation.
