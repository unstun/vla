# v27 optimizer crash: saved-input stack and isolation

Stage: experiment + analysis. Completed 2026-09-28 (America/Los_Angeles) in the
local pinned image `sha256:f7363cc3…` (ROS 2 Humble, GCC 11.4, glibc 2.35).
All attempts replay the captured seeds and sensor inputs from
`v27_historical_full01` against the unchanged v27 native sources
(`runtime/scan59_seed_shortcut_v27`). None of them is a new physical trial.

## Attempts

| Attempt | What changed | Outcome |
|---|---|---|
| root (`request.json`) | ASAN/UBSAN | Stopped in prebuilt ROS initialization (`new-delete-type-mismatch`) before optimizer code |
| `attempt02_bounds` | UBSAN + `_GLIBCXX_ASSERTIONS` | Abort (exit 134) at seed 269, fixed-height mode; no message or stack |
| `attempt03_stack` | + crash-time backtrace, line-buffered stdout | Compiler killed at 4 GiB/`-j3`; no replay (see `attempt03_stack/OUTCOME.md`) |
| `attempt04_stack` | same probe at 6 GiB/`-j2` | Abort at seed 269 with assertion text and a symbolized stack |
| `attempt05_trace` | attempt04 + stderr tracing in a diagnostic copy of the optimizer | Same abort; per-point rebound state recorded |

attempt02 lost the assertion text because GCC 11's `std::__replacement_assert`
prints with `printf` to stdout. With stdout redirected to a file, the text sat
in the stdio buffer, and `abort()` discarded it. attempt04 line-buffers stdout
and flushes it in a SIGABRT/SIGSEGV handler.

attempts 02, 04 and 05 return identical results for the 31 seeds before seed
269 (all `ok=0`). The tracing therefore did not change replay behavior.

## Stack (attempt04_stack/stack.txt)

```
Assertion '!this->empty()' failed: std::vector<Eigen::Vector3d>::back()   stl_vector.h:1145
check_collision_and_rebound()      bspline_optimizer.cpp:930
calcDistanceCostRebound()          bspline_optimizer.cpp:418
combineCostRebound()               bspline_optimizer.cpp:1166
costFunctionRebound()              bspline_optimizer.cpp:390
lbfgs::line_search_morethuente()   lbfgs.hpp:828
lbfgs::lbfgs_optimize()            lbfgs.hpp:1187
rebound_optimize()                 bspline_optimizer.cpp:1005
BsplineOptimizeTrajRebound()       bspline_optimizer.cpp:949
```

Line 930 is step 3's backward propagation,
`cps_.base_point[j].push_back(cps_.base_point[j + 1].back())`.

## Per-point state (attempt05_trace/replay.log, seed 269)

The first rebound call reports "The robot is inside an obstacle" (`in_id = 0`)
and one collision segment `[0, 4]` with a 17-point A* path:

| Point | Crossing | Length (m) | Flag | Stored pairs | Anchor after |
|---|---|---|---|---|---|
| 1 | no | – | 0 | 0 | -1 |
| 2 | yes | 0 | 1 | 0 | -1 |
| 3 | yes | 0.0448 | 1 | 1 | 3 |

Backward propagation from anchor 3 skips point 2, because it is flagged, then
reads `point 2.back()` for point 1: `[EMPTY-NEIGHBOR] j=1 neighbor=2 got=3 flag_neighbor=1`.
v27 sets the flag before checking the intersection length. Its zero-length branch
then resets the anchor but leaves the flag set with no stored pair.

This is exactly the deterministic counterexample `zero_then_valid_empty` in
`constraint_contract/` (exit -6 on v27). In a release build, `back()` on an
empty vector that was never allocated reads just below a null pointer. That is
consistent with the live segmentation fault (ros2run exit 245), but the live
process's own stack was not captured, and replay uses the final map with a fresh
clock rather than the live asynchronous schedule.

## Why the guard was missing

`p2b_execution/reactive_stair/materialize_scan_27.py` fixed this class on
2026-09-26 (flag only after a finite paired write, fresh-pair propagation,
`STOP_FOR_ERROR` when nothing is committed). The Newton generic materializer's
`--native-optimizer` option later copied the pinned `scan_04` optimizer file over
the scan33 lineage. `candidate_reachable_goal_identity_v9.json` records that
restore. The helper header survived, but no source called it. v28 restores the
guard; see `versions/v28/`.
