# Repair evidence and change boundary

Read-only inspection, 2026-10-02. No product/native source modified.

- Frozen v52 native diagnostic and original run: E2/audits/2026-10-02_v52_corner_43s.
- Existing requested goal identity: versions/v52/backend_ros/p2b_backend_ros/node.py
  lines 145–170 caches requested XYZ/yaw per full command identity; P2BRoute.msg
  separates has_goal_pose/goal_pose from its snapped path endpoint. Controller
  lines 87–106 retains the initial goal pose/latch across periodic refresh.
- Native local invalidation: scan_replan_fsm.cpp:251–254, planner_manager.cpp:99–128.
- Prefix admission/drain gap: scan_replan_fsm.cpp:1287–1317; native freshness
  predicate reactive_collision.h:135–139 and cloud default grid_map.cpp:72.
- Missing front support and guarded fill: scan_reactive_grid_methods.inc:79–93,
  187–237 and evidence_floor_fill.h:76–111. New cost/layer inspection is pct_layers.json.

Design responsibilities are described in parent design.md. Final goal/controller,
stop protocol, physics/PD/RL and all numeric safety limits remain outside edits.
New physical-floor input is geometry only, never positive obstacle classification
or permission to traverse cost-rejected cells. Source-role, negative fixtures and
full-manager admission are mandatory, not a point-intersection shortcut.
