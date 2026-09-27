# Upstream references for short local translation

Status: surveyed references; no new planner/package/runtime imported.

- SCAN-Planner `348e8a590a50a5a6bbab8d8c6dcfd171f009be26`, Apache-2.0:
  https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/planner_manager.cpp
  Original `reboundReplan` rejects distances below 0.2 m. Its existing sampler
  already increases sample density until there are at least seven spline points.
  The local partial-reference-window integration inherits that close-goal guard.
- Nav2 `3c3db59d6969d8ecee8e68468693d006397f4a0c`, Smac source Apache-2.0:
  https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_smac_planner/src/smac_planner_2d.cpp#L213
  Converts endpoints into map cells, handles the same-cell case separately,
  and runs its regular A* for distinct cells. Its root LICENSE directs readers
  to package/file licensing; the retained source header specifies Apache-2.0.

Exact downloaded files, URLs and hashes are under
`references/2026-09-27_short_frontier/source.json`. The local adaptation uses
SCAN's existing GridMap conversion and additionally requires one full map
resolution of XY translation to reject tiny cross-boundary movements. This is
an adaptation of resolution/cell-aware progress, not a reproduction of the full
Nav2 global planner or a claim that Nav2 supplies a SCAN spline fix.

Runtime/build dependencies remain the pinned ROS Humble image and existing
SCAN packages. Build via `repairs/2026-09-26_generic_occupancy/build_candidate.py`
after the source snapshot is frozen. Nav2 sources are reference-only; no Nav2
build command or package is executed in v6. Original Nav2 build instructions
remain in its pinned repository README.
