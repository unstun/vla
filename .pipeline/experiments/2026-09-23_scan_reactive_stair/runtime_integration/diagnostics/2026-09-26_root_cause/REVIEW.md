# Stair failure: independent review and recorded-input diagnosis

Stage: experiment and analysis. Dr Sun requested a careful cause review and
authorized one subagent. The primary agent audited sensing, tracking and goal
timing; one read-only reviewer independently audited native planning and then
cross-checked the new diagnostic evidence. No existing live configuration,
collision rule, tracker source, or accepted build was modified. A separate
logging-only native build was executed without the simulator or controller.

## Conclusions

The recordings establish an initial planning failure, not successful pedestrian
avoidance. Two concrete defects now have runtime or replay evidence: native
search drops candidates that its collision checker accepts, and the tracker
silently discards almost all returns around the right-side actor because its
ground model includes only robot-traversable PCT cells. Neither the first
Unknown warning nor repeated search failure proves that the physical stair has
no feasible route. A successful repair has not yet been demonstrated.

## 1. A* bookkeeping loses accepted candidates

The search marks a neighbor with the current search round **before** checking
collision. If that direction is blocked, the node is not initialized or queued.
When another direction later passes, the node appears already explored, so it
does not enter the new-node enqueue branch. This matters because the footprint
collision query depends on approach yaw. A second defect sets the nominal
infinite initial cost to `1 >> 20`, which is zero. Fixing the constant alone
does not fix the absent enqueue.

Source anchors under
`.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution/builds/`:

- `scan_19/src/path_searching/src/dyn_a_star.cpp:236`: premature round mark;
  lines 241, 250 and 259: collision return, fresh-node enqueue and update-only branch.
- `scan_19/src/path_searching/include/path_searching/dyn_a_star.h:11`: zero `inf`;
  line 38: initial scores.
- The same bookkeeping pattern exists in the live `scan_13` source at
  `path_searching/src/dyn_a_star.cpp:253,256,265`.

The isolated `scan19_audit_trace` changes only `dyn_a_star.cpp`, adding observer
variables and first-search logs. The reviewer confirmed unchanged occupancy
query count/order, queue operations and search decisions. Its real Foxy build
passed; source hashes matched before and after, and 454 installed files were
captured. The CPU replay used the recorded `walk_v4_ego` inputs, with the already
declared delayed 5 s goal and a shortened suffix. This is the later `scan_19`
candidate, not a new scan_13 live episode.

`replay_result/scan.log:169` records the first native search:

| Measurement | Result |
|---|---:|
| Nodes pushed / popped | 851 / 851 |
| Neighbor occupancy calls | 16,248 |
| Calls returning free | 5,917 |
| Previously rejected candidate later returning free | 2,472 encounters |
| Free candidate that had never entered the queue | **982 encounters** |
| Remaining queue at failure | 0 |
| Elapsed time / cap | **5.36 ms / 200 ms** |

The 982 count is not a count of unique cells. Samples at lines 170–189 show
`state=3, prior_g=0, explored=1, ever_pushed=0` after a free collision result.
Some samples reach y=4.698 m, so exploration was not entirely confined to the
robot's immediate blind region. Logging overhead did not cause the time cap.
This establishes actual occurrence of the defect in the candidate replay;
only a corrected same-input comparison can establish its effect on final route
success. The four-cell behavioral reduction in
`search_bookkeeping_counterexample.py` also reproduces the omission. It is
explicitly not a substitute for a native integration test.

## 2. Right-side actor returns are filtered by an inappropriate ground mask

The captured scan_13 tracker uses `terrain_from_pct_records()` to keep only
PCT cells with traversability cost <=20. `shape_candidates()` then drops every
point for which `ground_below()` returns None. These are robot traversability
cells, not a complete physical floor model. The actual Building mesh supports
the right-side placement even where this selected mask has no floor cell.

Source anchors in `scan_13/src/scan_reactive_tracker/scan_reactive_tracker/`:
`io.py` (`terrain_from_pct_records`) and `core.py:142–144` (point rejection).

`audit_tracker_and_timing.py` imports the hash-verified captured core, uses the
same pinned map, and replays only cloud timestamps actually recorded at the
ROS boundary. Actor truth is consumed after tracking solely to define a
posthoc spatial region (radius 0.32 m, height 0.45–1.70 m above the actor root's
ground reference). The region is not RTX object-ID attribution.

| Measurement | Original center position | Right-side position |
|---|---:|---:|
| Replayed recorded cloud frames | 280 | 282 |
| Live / replay nonempty track frames | 190 / 190 | 0 / 0 |
| Positive-track timestamp disagreement | 0 | 0 |
| Returns in actor spatial region | 22,111 | 21,954 |
| Rejected for absent selected ground | 0 | **21,927 (99.88%)** |
| Passing that point filter | 22,111 | 27 |

At 10.82 s, all 62 right-side region returns lack selected ground and no shape
candidate remains. At the original position, all 74 region returns pass and
the tracker forms an 83-point shape candidate.

The live right-side messages are 281 complete-empty batches and one incomplete
empty batch. Producer `complete` guarantees input checks and resolution of
existing shape candidates, not floor coverage throughout the field of view.
The consumer accepts a complete empty batch as the current person list
(`reactive_collision.h:72–73,128–130,165–178`). This is a coverage-contract gap:
absence from the Person layer cannot establish an empty scene. Raw LiDAR
occupancy remains independent, and this episode issued no nonzero command.

Replay limitations: archived points are rounded to four decimals; replay uses
now=cloud stamp and therefore excludes live transport waits. Agreement of
positive-track timestamps is not bitwise parity of positions, radii, complete
flags or live scheduling. In particular replay has 282 complete-empty batches
while live has 281. Neither claim requires feeding actor truth to tracking.

## 3. Failure occurs before the pedestrian begins moving

The live right-side timeline (`goal_timeline.json`) is:

1. 1.68 s: goal requested while the body is in STAND_TRANSITION.
2. 1.70 s: the planner FSM accepts the route.
3. 2.16 s: no matching-generation controller heartbeat has arrived; the backend
   cancels the generation with `initial_heartbeat_missing`.
4. Two six-point constant-position splines are emitted as stop/hold output;
   the controller rejects them as `generation_cancelled_before_spline`.
5. 3.22 s: the polling journal first observes the completed failure/stop result.
6. 10.02 s: the actor begins moving, long after this navigation attempt stopped.

None of 6,548 raw command records carries the original goal identity, and all
1,454 admitted robot commands are zero. The backend timeout is a downstream
symptom of absent usable trajectory/control output. Early goal dispatch is an
experimental weakness, but previously delayed native replays and the new
5 s replay still fail; it is not an established sole cause.

Source: live package `backend_ros/p2b_backend_ros/node.py:238–256` and
`returned_artifacts/reactive_observations.jsonl`. Both live runs' controller
stop times and identity counts are captured in `goal_timeline.json`.

## 4. Additional verified rejection mechanisms and prior overinterpretation

- **First Unknown warning checks the distant goal.**
  `scan_13/src/plan_manage/src/scan_replan_fsm.cpp:323–345` then retreats along
  the global trajectory. Right-side `scan_planner_node.log:8–9` moves the target
  from approximately (-5.35,1.01,1.24) to (-5.41,3.81,0.78). That warning alone
  cannot locate the start failure. Lines 132–147 contain the actual failed
  optimization/initial-control-point chain.
- **Height assumptions conflict with stairs in scan_13.** Its A* fixes candidate
  height to endpoint interpolation, and the optimizer zeroes both Z gradients
  (`dyn_a_star.cpp:169–179`, `bspline_optimizer.cpp:1169,1197`). A logged query
  (-5.40706,5.74804,0.36579) has known free occupancy but lies 0.151 m below its
  PCT ground-plus-0.35 m body target, beyond the 0.12 m tolerance. scan14/15
  remove these restrictions but still fail, so they are not the sole cause.
- **Multilevel support can be mislabeled as a tall step.** At the logged
  (-5.59778,5.82081,0.40454), three adjacent PCT cells supply only a ~6.082 m
  upper-floor surface beside the ~0.058 m lower floor. The nearest-height
  neighbor selector has no same-level distance bound, producing a 6.023987 m
  support-height range (`eth_step_score_adaptation.h:51–66,178`). Keeping missing
  same-level support blocked is consistent with the conservative contract;
  calling it an actual six-meter stair is not.
- **The 120 near-sensor diagnostics are a capped sample.** scan19's 36 Free,
  64 Unknown, 18 Unsupported and 2 WrongHeight records are neither the whole
  search distribution nor proof of physical infeasibility. Unknown is returned
  before support checks, so one verdict can mask other conditions.

## Next controlled repair order

1. Repair A* discovery/enqueue and score initialization in a separate candidate;
   retain the current collision rules. Test the four-cell pattern and the same
   recorded inputs. Separately inspect heading-dependent state representation
   and priority-queue score updates before claiming a complete search.
2. Give tracking a physically meaningful ground-coverage contract independent
   of the robot's traversability cost mask; explicitly represent unobserved
   coverage. A map/input contract change requires its own reviewed candidate.
3. Keep same-level support association, stair Z consistency and start settling
   separate in subsequent comparisons. First demonstrate an accepted moving
   trajectory; only then evaluate the moving-human scenario and render video.

No safety threshold relaxation, blind-volume clearing or physical-route success
claim follows from this review. No live repair was applied in this audit.

## Evidence and rerun entry points

- `tracker_and_timing.json`: source/input hashes and per-frame tracker audit.
- `goal_timeline.json`: live admission/stop chronology and identity counts.
- `native_search_review.json`: first-search counts and log identity.
- `execution_result.json`: bounded CPU invocation and returned source/log hashes.
- `replay_result/`: native output; preserved unmodified.
- `materialize_search_trace.py`, `run_search_trace.py`: isolated trace recipe;
  immutable-output guards require fresh paths for any subsequent run.
- `search_bookkeeping_counterexample.py`: reviewer-provided behavioral reduction;
  all four expected outcomes passed.

The reviewer cross-checked the source diff, quaternion conversion, exact source
map hashes, truth separation, timestamp-match limitation and native trace.
One subagent was used; it made no file changes or remote executions.
