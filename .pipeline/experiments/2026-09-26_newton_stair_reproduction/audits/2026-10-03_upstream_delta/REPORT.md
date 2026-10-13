# Current implementation versus upstream PCT + SCAN

Stage: experiment + analysis, 2026-10-03. Source comparison only; no production change or new run.

The current tested development version is **v59**. v48 remains the runnable experimental reference; v60/v61 change video presentation only. PCD denotes the point-cloud map; PCT is the global planner that uses its tomogram.

**The architecture remains PCT global planning followed by SCAN B-spline local planning and velocity control. The current local planner is a substantial derivative, not a faithful upstream reproduction or merely a simulator port.**

## Exact comparison boundary

The executable import came from `yagami-light7/PCT-SCAN-ROS2`, commit `1cf45a1c12ca785ce533293302be09d51daf0ccb`. Its 65 imported source/notice hashes were reverified against the acquisition manifest. That ROS2 code is the appropriate denominator for changes made after our import. The separately inspected original SCAN manager is from `wuyi2121/SCAN-Planner`, commit `348e8a590a50a5a6bbab8d8c6dcfd171f009be26`; its saved file hash matches the v48 upstream receipt. These two upstream levels must not be conflated.

For the same six native packages, excluding the external bridge, backend, PCT worker, simulator and locomotion:

| File comparison | Count |
|---|---:|
| Original files under the six package directories | 62 |
| Current files in those same directories | 87 |
| Original files still byte-identical | 43 |
| Original files modified | 19 |
| New files | 25 |
| Original files removed | 0 |
| Original C++/header/Python/include-fragment code files | 41 |
| Those original code files modified | 14 |
| New code files | 18 |

The other original files are build definitions, messages and resources. The new code files contain 1,974 lines, including comments and diagnostic/profile helpers. Counts include some inactive files and exclude two added auxiliary packages (`geometry_probe` and `scan_reactive_tracker`). The complete native source tree contains 101 files. These are reproducible source counts, **not percentages of algorithmic behavior**. [Per-file hashes and counts](comparison.json).

Major source sizes illustrate where the changes concentrate (line endings normalized):

| File | Imported base lines | v59 lines |
|---|---:|---:|
| planner_manager.cpp | 510 | 804 |
| scan_replan_fsm.cpp | 1,097 | 1,786 |
| closed_loop_controller.cpp | 188 | 423 |
| dyn_a_star.cpp | 309 | 469 |
| grid_map.cpp | 1,181 | 1,362 |
| bspline_optimizer.cpp | 1,201 | 1,217 |

The map also includes newly added support/collision helper files. The optimizer's similar line count does not establish identical behavior; changed predicates and inputs materially affect its existing search loop.

## What remains upstream, and what we changed

| Area | Retained foundation | Current local differences |
|---|---|---|
| PCT global planning | All ten runtime PCT Python files compare byte-identical with the pinned PCT source, including `plan.py` and `planner_wrapper.py` | Custom request worker, route identity/protocol, selected layer handling, native-height extraction, body-reference height and periodic integration. Map/support exports are custom; this is not an unmodified upstream end-to-end run. This audit does not equate source matching with a newly reproduced native binary build. |
| SCAN mathematical machinery | Uniform cubic B-splines, L-BFGS, smoothness/collision/feasibility objectives, refinement, grid A* and the two-cylinder footprint | Added hard endpoint PVA fitting, complete sampled curve checks, stronger boundary/dynamics admission, explicit height optimization and fixed-height recovery, and minimum planned cruise checks. |
| Terrain and collision | Native live LiDAR raycasting, occupancy buffers and footprint queries | Added selected navigation support, separate raw-surface evidence and physical-floor presence, ETH-style step scoring, drop guards, floor/riser classification, body/footprint height association, measured-trunk unknown handling and caches. These change which states and edges are admitted. |
| Seed generation | Upstream remaining-trajectory reuse and arc-length sampling provided patterns | Original polynomial/remaining-curve initialization with linear-Z rewriting was replaced by current validated remaining-curve seeds or mandatory collision-checked graph seeds. Our warm binding, invalidation, straight target connector, hard PVA fit and rejection reasons are local. |
| Target and recovery | Global-reference following and the native optimizer's retry framework | Added reachable frontier/goal-neighborhood handling, feasible-window reuse, shared shorter-target proposals, fixed-height retry, route-refresh continuity and fresh-input handling. Multiple additions interact in the same nominal round. |
| A* details | Original grid search structure and configured search plane | Corrected queue bookkeeping/grid alignment, checked every edge and exact endpoint connector, added reachable goal proposals and necessary goal-region/endpoint-evidence rejection. This is more than wrapping the original search call. |
| Scheduling | Original FSM and controller structure | Original local replanning follows progress/state conditions; its timer is not proof of a successful planning rate. We impose periodic 30 Hz local scheduling, 30 Hz control and 1 Hz global requests, plus simulation/host clock integration and in-solve input refresh. |
| Goal/control/stop integration | Feedforward plus position feedback, heading look-ahead, heading-based translation freeze and native stopping concepts | Added global XYZ/final-yaw completion, generation/owner identity, admission/cancellation protocol, backend freshness/heartbeat gates and v59 receipt-time initialization. These already differed from upstream before the recent performance repairs. |
| Physical execution | Planner output remains body velocity commands | Lite3 policy and PD startup/hold, Newton dynamics, geometric LiDAR, simulator localization, bridge/clock/transport and recorded-state video are our integration, not the original upstream demonstration stack. |

“Preserve goal, yaw, dynamics and safety rules” in recent repair requests means preserve the **existing local parent contract** (for example v48 or v57). It does not mean those rules are identical to untouched upstream SCAN. The current contract had already changed substantially before v47–v59.

## Attribution of the current failure

- The ETH-style support/drop guard, checked straight warm connector, warm-binding invalidation, feasible-window recovery and fixed-height expansion of the recovery chain are local additions/adaptations. The exact v59 combination is not upstream behavior.
- The basic three-restart optimizer loop and the path-vector return after a failed obstacle-repair search are present in the pinned ROS2 base. Our more restrictive/different collision and support predicates expose that inherited weak failure handling, and our added recovery branches multiply its cost. Blaming this entire episode on either upstream or our new code alone would be inaccurate.
- The sampled-origin loss after the old curve expires during chained retries is a defect in our v59 modification. The direct timing tests did not cover it. [Native diagnosis](../2026-10-03_v59_cold_recovery/REPORT.md).
- v49's 20 ms abort approach is excluded from the current lineage. The original per-A* 0.2 s limit is a different, retained mechanism; it is not a whole-chain 30 Hz guarantee.

The current evidence supports describing this as **an upstream-based PCT/SCAN integration with substantial custom local-planning and execution behavior**. It does not establish unchanged upstream equivalence, successful complete-route reproduction or sustained 30 Hz.

## Source anchors

- [Pinned native import and eight original port adaptations](../../../../../references/upstream/2026-09-16_lite3_isaac_harness_backend/SOURCE.md).
- [Imported manager](../../../../../references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_base/src/plan_manage/src/planner_manager.cpp), [current manager](../../runtime/scan80_trajectory_epoch_v59/src/plan_manage/src/planner_manager.cpp).
- [Imported optimizer](../../../../../references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_base/src/bspline_opt/src/bspline_optimizer.cpp), [current optimizer](../../runtime/scan80_trajectory_epoch_v59/src/bspline_opt/src/bspline_optimizer.cpp).
- [Current native launch graph](../../versions/v59/native_graph.py), [PCT request adapter](../../runtime_sources/backend_adapter/backend_adapter/pct_worker.py), [runtime configuration](../../versions/v59/building_planner.yaml).
- [Version-by-version change record](../../versions/README.md), [warm-start upstream receipt](../../versions/v48/upstream_identity.json).
