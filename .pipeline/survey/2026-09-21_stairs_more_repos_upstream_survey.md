---
origin: ai+web
reviewed: false
date: 2026-09-21
stage: planning
status: surveyed
task: none
---

# More open-source references for stair local planning

**Question (Dr Sun, 2026-09-21).** Find more open-source repositories to reference for SCAN stair planning, beyond the 2026-09-17 SCAN/PCT census and the 2026-09-18 planner comparison.

**Status: `surveyed`.** Pages were read. Nothing was cloned, built, or imported. Commit SHAs were not pinned; the notes are branch heads as fetched on 2026-09-21.

## Already recorded, not repeated

SCAN-Planner and its forks, PCT stacks, ArtPlanner, CMU `autonomy_stack_go2`, dimos, FDM, SRU, SanD-Planner, ViPlanner, Spot, CyberDog2, Lite3_Navigation, TravExplorer (README only), and RAEM (no usable code). See `2026-09-17_scan_stairs_upstream_survey.md` and `2026-09-18_stairs_local_planner_upstream_survey.md`.

## New candidates

| Repository | License read | What it is | Stair content | Fit |
|---|---|---|---|---|
| [leggedrobotics/traversability_estimation](https://github.com/leggedrobotics/traversability_estimation) | BSD-3-Clause (`LICENSE`, ETH ASL, 2015) | ROS Noetic filters on an elevation map: slope, roughness, and a step filter | `StepFilter.cpp` scores step traversability per cell. Not a trajectory planner | Closest new piece. The step filter can be read as a rule for “this height change is a step,” then used inside a stair profile. ROS 1 |
| [leggedrobotics/elevation_mapping_cupy](https://github.com/leggedrobotics/elevation_mapping_cupy) | MIT (ETH, 2022) | GPU elevation map, plane segmentation, learning-based traversability | Stairs are terrain in the map, not a planner mode | Map layer a stair filter would sit on. Includes `plane_segmentation` |
| [ANYbotics/elevation_mapping](https://github.com/anybotics/elevation_mapping) | BSD-3-Clause (README) | CPU robot-centric elevation map | Same role as the GPU map | Older input used by ETH legged navigation. ROS 1 |
| [Quadruped-dyn-insp/Go2_planner_suite](https://github.com/Quadruped-dyn-insp/Go2_planner_suite) | Root `LICENSE` is MIT (2025). `terrain_analysis`, `terrain_analysis_ext`, `local_planner`, and `far_planner` `package.xml` each say BSD, maintainers Ji Zhang / Fan Yang (CMU) | ROS 2 Humble packaging of the CMU terrain stack plus FAR Planner, MOLA, and a Go2 Gazebo sim | No stair mode. Extended terrain launch sets `terrainConnThre` 0.8 m and `vehicleHeight` 0.5 m. Local-planner launch sets `useTerrainAnalysis` false and `obstacleHeightThre` 0.15 m. README examples (0.4 m / 0.3 m) are not these launch values | Same algorithm family as the already surveyed CMU stack. Copying the planner packages follows their BSD notices, not the root MIT file |
| [peter-nebe/stair-step-detector](https://github.com/peter-nebe/stair-step-detector) | GPL-3.0 | Depth-camera stair step measurement. ROS 2 wrapper is Galactic; detector is C++ | Measures step height and corners for ascent and descent. Tested on RealSense L515 | Detector only. GPL-3.0: do not copy into this repository |
| [ZWT006/agile_navigation](https://github.com/ZWT006/agile_navigation) | No `LICENSE` file in the tree | ROS Noetic kinodynamic planner for a quadruped (A1 in the launch files) | No stair mode in the README | Do not copy. Flat agile navigation, not stairs |

## What this adds

Still no repository that is a drop-in stair mode for SCAN. The new readable piece is ETH’s step filter on an elevation map (`traversability_estimation`, BSD-3-Clause), with `elevation_mapping_cupy` (MIT) as the map that can feed it. `Go2_planner_suite` is another packaging of the terrain-height local filter already considered via CMU, now on ROS 2 Humble and a Livox. The dedicated stair detector is GPL-3.0.

## Claim boundary

- `surveyed` only.
- Licenses are the files or README text fetched on 2026-09-21.
- No stair success numbers were re-measured.
