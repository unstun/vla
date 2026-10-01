# Upstream basis and local adaptation boundary

The clean PCT-SCAN baseline is pinned at
`1cf45a1c12ca785ce533293302be09d51daf0ccb`. Its project-local copy
`references/upstream/2026-09-16_lite3_isaac_harness_backend/source/pct_scan_base/src/plan_env/include/plan_env/grid_map.h`
lines 371–379 uses the two cylinder centers for inflated occupancy. It has no
per-cylinder body-clearance terrain gate. The selected baseline and license
are recorded in that acquisition directory's `native_planner_acquisition.json`.

The same upstream PCT optimizer samples terrain at the trajectory center XY,
adds the reference height, then smooths the height:
[gpmp_optimizer.cc, lines 193–200](https://github.com/yagami-light7/PCT-SCAN-ROS2/blob/1cf45a1c12ca785ce533293302be09d51daf0ccb/src/pct/pct_planner/lib/src/trajectory_optimization/gpmp_optimizer/gpmp_optimizer.cc#L193).
The committed blob was independently verified as SHA-256
`3a2a6d0f0efe8eaa6b3348fc5c8000b6bd0d9d32e46390ca11c35c93fde59036`.

The pinned ETH implementation evaluates footprint XY traversability from its
terrain filters. Robot height in the circular footprint routine is used for
polygon visualization. Its StepFilter scores local terrain height differences.
Source and BSD-3-Clause notice are retained under
`references/upstream/2026-09-27_eth_footprint_support` and the existing
`2026-09-23_eth_stepfilter_reference`; both pin
`14d24c059e1c43466aadf328280adf6394d78039`.

v24 repairs the local connection between the existing multi-floor support
adapter and the original footprint occupancy query. It reuses the existing
layer association and scored support; it does not import a new planner or
claim exact ETH/ROS 1 behavior. No upstream runtime was reproduced here.
