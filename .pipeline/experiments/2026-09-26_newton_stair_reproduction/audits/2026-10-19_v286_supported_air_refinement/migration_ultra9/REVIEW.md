# v286 evidence interpretation

The complete ultra9 offline gate passes, but the physical candidate is not validated. Keep the frozen source and each single attempt; do not use a targeted counter improvement as a substitute for arrival and measured geometry.

## Unknown is not the inflation bit

In frozenv285 `reactiveOccupancy`, the test `occupancy_buffer_[address] < clamp_min_log_ - 1e-3` precedes the inflation-buffer branch. A queried cell can therefore be logged as `UnknownObstacle(6), voxel=Unknown(0)` even when `occupancy_buffer_inflate_[address] != 0`. The log pair alone does not establish uninflated air. v286 checks the inflation bit first, then runs raw-contributor classification. Some label changes from6:0 to7:2 can be classification-order changes, rather than newly created obstacles or eliminated physical false rejections.

The supported-air relaxation intentionally requires zero inflation and complete support/freshness/source checks. It does not waive7:2. New A04/G05 logs have zero6:0 and zero pool exhaustion, but still contain7:2 and fail with native controller exit-11. CU06 still fails progress and publishes no-executable events. The final bill must preserve all these channels and compare full terminal outcomes. A7:2 return means an observed/inflated point-cloud decision, not independently proven wall collision; compare its contributor provenance with actual static/source/raw geometry before attributing a cause.

Sources: frozen `versions/v285/src/plan_env/include/plan_env/scan_reactive_grid_methods.inc` and `versions/v286/src/plan_env/include/plan_env/scan_reactive_grid_methods.inc`, plus the actual new recorded `nav2.log` streams. No coordinate-based interpretation is needed.

## Native exit is an unresolved failure

A04/G05 have positive recorded physical steps followed by `native_process_exit:controller_server:exit_code=-11`. These are failed physical attempts. There is no returned core/backtrace for these exits; `/proc/sys/kernel/core_pattern` delegates to Apport and `/var/crash` contains no corresponding controller record. A particular C++ root cause is therefore not established. Do not claim all four requested causes were sufficient or that the remaining failure is only progress timeout.

## Controls and host limits

All329 native sources and20 frozen bridge sources match pinned local inventories. All11 core fields and3 publisher metadata hashes match the prior geometry. The actual new S04 SCAN YAML is byte-identical to the returnedv285 generated hash (`3fcb4706e21cdb79aed98d0760bb75681ae9008cdad50b13710795418a39b048`); PCT parameters compare equal. Its actual paced navigationRTF is0.9999615. No radius, scanner period or scalar goal gate was relaxed. The CPU, rebuilt executable bytes and ROS image differ from the inaccessible9700x execution, so cross-version physical results are not a controlled same-host causal experiment.

## Retention is separate from navigation

The inherited managed runner reports retention exit2 after `lsof` emits warnings for unrelated inaccessible shared/NFS/nsfs mounts. Original run files are retained. The process result, recorded terminal and positive physics-step proof remain authoritative; exit2 is not itself a nav2 terminal classification. Postprocessing uses the existing verified non-pruning snapshot path and keeps original files. No physical rerun is permitted to regenerate an archive or video.

## The optimizer error is not a direct measured-body collision test

Frozen `bspline_optimizer.cpp` emits "The robot is inside an obstacle" at lines794-807 when its backward search finds no control point for which the Boolean `getInflateOccupancy` is free. The adjacent forward search can then emit "Trajectory terminal point is in an obstacle; skip this plan" at lines810-826. The first message alone does not identify the measured trunk or the FSM start point, nor does it retain a typed reason (geometry, stale/missing evidence, height or observed occupancy). A04/CU06 contain these optimizer messages without an `initial_spline_collision` FSM witness. Do not equate their counts.

The additional `initial_collision_witness_audit.json` audits only actual logged FSM initial-point diagnostics with explicitXYZ/yaw. Those are a different event stream. The source-clear totals cannot be attached to optimizer messages that lack those coordinates. Some following forced diagnostics already reportFree, indicating that input/snapshot timing must be retained in a replay diagnosis. New S04 input-refresh logs include cloudage0.6903s and a roughly590ms rebound round; exact per-event evidence is required before assigning an observed-obstacle cause. A specific static/live disagreement was not established by the initial witness stream alone.

## Diagnostic-name correction after callsite review

`logInitialSplineCollision` is invoked unconditionally within a recovery-candidate diagnostic window (candidate_t0.9..1.2), twice for the start and a+0.05m X probe. It is not necessarily called because that position was refused. Its filename/logger name cannot establish a collision event. The numeric point audits are retained, with primaryJSON marked diagnostic_only=true and collision_event_proven=false; the first interpretation is preserved remotely and superseded byinitial_point_diagnostic_semantics02.json. Do not use those counts as optimizer collision witnesses.

Verdict7 is the shared StaticObstacle enum: it may result from Occupied voxel2 or from the source-solid check during Unknown-air normalization (including voxel0). The final bill has197verdict7mentions:177withvoxel2 and20withvoxel0. They are not all observed-hit events. Typed original arguments are needed to localize the source of each Boolean refusal.
