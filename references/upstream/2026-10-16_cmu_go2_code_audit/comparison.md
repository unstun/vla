---
origin: ai_only
reviewed: false
status: surveyed
date: 2026-10-16
---

# CMU Go2 navigation: public implementation and Lite3 migration assessment

**Decision: retain the current stair-navigation baseline. CMU is a credible,
comparatively simple navigation baseline to evaluate on Lite3, but its public
release does not establish a cheaper or more reliable replacement for the
current PCT–SCAN stair and multi-floor task.**

The inspected navigation chain is substantially complete above the body-velocity
interface. Its hardware execution ends at Unitree Sport API requests. Go2's
balance, stepping, contact response and locomotion controller are supplied by
the robot, not by this repository. This boundary is compatible with using an
existing Lite3 velocity-following controller; it does not transfer Go2's terrain
capability to Lite3.

## Scope and provenance

- Repository: <https://github.com/jizhang-cmu/autonomy_stack_go2>.
- Inspected default branch: `foxy-humble`; only one public branch returned.
- Fixed commit: `43d5f54b389b251713f0097893c30fa76c870d54`.
- Commit date: 2026-02-18; message: `update download link`. This is not evidence
  of an algorithm revision on that date.
- Acquired a clean, read-only sparse reference: 435 Git tree entries, 417
  materialized files, 23 ROS packages. Media, large path/map assets and external
  Unity downloads were not acquired. The path generator and small path tables
  were inspected.
- [Manifest](repository_manifest.yaml), [source hashes](source_inventory.json),
  [package inventory](package_inventory.json), [configuration facts](source_facts.json).
- No dependency installation, ROS build, upstream navigation run, physics run,
  or Lite3 integration was performed. This is source assessment, not reproduction.

## 1. Actual data flow

References below are relative to `source/autonomy_stack_go2/` at the fixed commit.

| Stage | Public implementation | Evidence and transfer implication |
|---|---|---|
| Sensor preparation | Go2 L1 cloud and IMU transformation, calibration and Point-LIO | `src/utilities/transform_sensors/transform_sensors/transform_everything.py:22`; `src/slam/point_lio_unilidar/launch/mapping_utlidar.launch:23`. Produces registered cloud and state estimate. Sensor extrinsics, timing and frame assumptions are platform-specific. Existing compatible Lite3 odometry/cloud can replace this front end. |
| Terrain analysis | Ground-height estimation and relative point-height encoding, including a missing-ground obstacle mechanism | `src/base_autonomy/terrain_analysis/src/terrainAnalysis.cpp:606`. Point intensity becomes height above estimated local ground, not lidar reflectivity. |
| Global route | FAR visibility graph and waypoint generation, with terrain-height handling | `src/route_planner/far_planner/launch/far_planner.launch`; `src/route_planner/far_planner/src/far_planner.cpp:721`. The implementation is present, not an external planner placeholder. |
| Local avoidance | Precomputed curved paths, obstacle/path correspondence lookup, scoring and path selection | `src/base_autonomy/local_planner/src/localPlanner.cpp:775`. Nearby terrain points filter candidate paths. The supplied 343 path endpoints form seven groups; candidates are considered at multiple yaw rotations. |
| Tracking | Body-frame path tracking, speed ramping, slowdown and yaw control | `src/base_autonomy/local_planner/src/pathFollower.cpp:318`. Publishes `TwistStamped` on `/cmd_vel`. |
| Robot command | Sends the same body velocity to Go2 Sport API | `src/base_autonomy/local_planner/src/pathFollower.cpp:429`. Zero command invokes `StopMove`; otherwise invokes `Move(vx, vy, vyaw)` on `/api/sport/request`. |
| Leg execution | External Go2 capability | `src/utilities/unitree_pkgs/go2_sport_api/src/common/ros2_sport_client.cpp:43` serializes a request; it does not implement a joint controller or learned locomotion policy. |

The real-robot route launch explicitly brings these components together:
`src/base_autonomy/vehicle_simulator/launch/system_real_robot_with_route_planner.launch`.
Thus it is fair to call the navigation implementation available and connected
in source. Buildability and hardware behavior were not independently tested.

## 2. What the stair claim does and does not support

### Planar local motion delegates stepping to the robot

`local_planner/paths/path_generator.m:36,53` generates zero-z curves.
The acquired `startPaths.ply` has 707 points with z=0; `pathList.ply` has
343 endpoints with z=0. `localPlanner.cpp:248` uses only goal x/y in the local
goal handler. The active follower sends body velocity, not footholds, body-height
trajectories or stair-specific locomotion actions.

Planar steering can still take a capable legged controller over slopes or steps.
Therefore zero-z paths do **not** prove stair climbing impossible. They establish
that the local planner does not itself solve foot placement or verify whether
Lite3 can physically execute a particular stair transition. The active command
path does not invoke the SDK's gait or foot-height setters either.

### Different default terrain thresholds need reconciliation

The real launch enables terrain analysis. Its defaults and consumers are:

| Consumer | Shipped setting and predicate | Result for the same terrain point with intensity 0.18 m |
|---|---|---|
| Local planner | `obstacleHeightThre=0.3`, `useCost=false`; retains nearby points only when intensity exceeds the threshold | Not retained as a local obstacle point |
| FAR | `util/terrain_free_Z=0.15`; intensity below the threshold is free, otherwise obstacle | Classified as an obstacle point |

Anchors: `local_planner/launch/local_planner.launch:29,33`,
`local_planner/src/localPlanner.cpp:204`,
`far_planner/config/default.yaml:35`, `far_planner/src/utility.cpp:205`.
The extended terrain module copies nearby local terrain points into its output
(`terrain_analysis_ext/src/terrainAnalysisExt.cpp:542`), so this is not merely a
comparison of unrelated parameter names.

The 0.18 m example is a **terrain-relative point value**, not a guaranteed
measurement of an 18 cm stair riser. Ground estimation, scan visibility,
voxel filtering, obstacle distribution and graph connectivity also affect the
route. The mismatch is evidence of different traversability assumptions to
reconcile, not proof that every stair is blocked or every low obstacle is hit.
The 0.3 m threshold is not a certified maximum climb height.

The upstream README's Notes explicitly attributes poor low-obstacle separation
to L1 lidar noise and expects obstacles above 0.3 m. This is a limitation of the
published sensor/configuration combination, not an intrinsic FAR limit or a
permanent limitation after replacing the sensor and recalibrating perception.

### Downstairs have some negative-obstacle handling, not a supplied descent skill

`terrain_analysis/launch/terrain_analysis.launch` sets `considerDrop=false`,
but also `noDataObstacle=true` and `maxElevBelowVeh=-0.6`.
`terrainAnalysis.cpp:624` gates a missing-ground check; lines 635–638 mark cells
in a configured forward window when ground samples are sparse or too far below
the robot. Later code inserts obstacle points. It would be incorrect to claim
that the release has no drop handling.

This logic can prevent driving into missing floor; it does not establish which
visible descending stairs Lite3 can negotiate. Its behavior depends on sensor
coverage, robot/sensor height, initialization and the terrain parameters. A
descending stair may require different treatment from a hole or ledge, while
the physical descent still depends on the locomotion controller.

### Multi-floor support is not established by the default Go2 setup

FAR includes 3D nodes, terrain connectivity and code conditional on multi-layer
mode. Do not describe the whole planner as purely 2D. However the Go2 release
sets `is_multi_layer=false` (`far_planner/config/default.yaml:13`). In that mode,
the target z is associated with nearby terrain
(`far_planner/src/graph_planner.cpp:349`). Changing this flag is not a demonstrated
solution for stacked floors, stair landings, floor identity and return routes.

The author development website includes multi-level garage examples using slopes;
that evidence must not be relabeled as a staircase ascent/descent benchmark.
The inspected public release did not provide a repeated stair ascent/descent,
landing-turn and multi-floor acceptance result that can be transferred to Lite3.

### The exposed simulator does not test legged stair execution

`vehicle_simulator/src/vehicleSimulator.cpp:285` integrates yaw and x/y from
commanded body velocity and sets z from terrain height plus a configured offset.
It then sends model poses to Unity. Optional terrain-height/inclination adjustment
can help navigation development, but this exposed control loop does not simulate
the joint controller, foot contacts, slip and support transitions of the actual
Go2 or Lite3. A successful run there would not establish physical stair ability.
External Unity executables are separately distributed; they were not acquired
or executed in this audit.

## 3. Lite3 work that remains

| Work | Assessment relative to the current local stack |
|---|---|
| ROS and velocity adapter | Relatively direct. ROS 2 Foxy/Humble and body x/y/yaw velocity are closer to the existing Lite3 interface than UAS's public aerial local modules. Adapt `TwistStamped` to the local `Twist` contract, frames, limits and command ownership. Remove/bypass the active Go2 request path. |
| Sensors and state estimation | Reuse validated Lite3 state/cloud inputs where possible. Copying the Go2 L1 transforms and calibration would introduce wrong geometry. |
| Robot collision envelope | Retune FAR and local dimensions, sensor offsets and rotation behavior. The collision lookup is generated with a radius in `path_generator.m:114,143`; changing only YAML body dimensions is insufficient to establish the desired footprint. Path scaling also changes the effective geometry. |
| Traversability | Align terrain estimation, FAR's free/obstacle split, local filtering, missing-ground logic and Lite3's actual climb/descent capability. The default local configuration disables soft height cost and rotation-obstacle checking. |
| Completion and stopping | Preserve the current stricter local completion contract: pose/yaw, measured stopped state and confirmed standing. CMU's waypoint proximity and Sport `StopMove` request are not equivalent acceptance criteria. |
| Loss of input / cancellation | Integrate current cancellation, input freshness and command-owner behavior. The inspected CMU follower continues tracking stored path state and does not itself show an explicit path/odometry age deadline. This is not a claim about watchdog behavior inside Go2. |
| Stair and floor evaluation | Re-run physical ascent, descent, landing turns and repeated-floor routes. A geometric navigation demo cannot replace this evidence. |

The current local execution contract is documented in
`.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v206/src/scan_nav2_controller/README.md`.
This is implemented integration, not proof that all current routes work.
The v208 `results/physical_summary.json` records two initialized-state physical
pairs passing, with `new_full_route_runs=0`; do not describe the earlier stop
failure as completely untouched, or those two pairs as new complete-route success.

CMU's local planner removes the particular complexity of online B-spline
trajectory optimization: it mainly selects from precomputed candidates. That
is a real structural simplification, but neither a measured runtime advantage
nor a measured reliability gain. It can trade optimization failures for path
library coverage, geometric conservatism and threshold sensitivity.

## 4. Recommended comparison

Use CMU as a separate, bounded baseline on the **same Lite3 locomotion controller,
sensor inputs and completion criteria**. First compare flat corridors, turns,
narrow passages and low obstacles. Then separately compare uphill/downhill
stairs, landing turns, occluded descending ground and stacked-floor routing.
Record completion, intervention, collision/stall, body stability and stop quality,
not just whether a geometric waypoint was reached.

This proposal is not an executed experiment. For a flat-ground project the
public implementation is a reasonable first candidate. For the current stair
project, replacement now would discard working integration while retaining the
central terrain/controller matching problem. There is no matched evidence that
the replacement would be more reliable.

## 5. Packaging and license boundaries

Most base-autonomy/FAR package manifests declare BSD. Point-LIO's package manifest
declares BSD while its included LICENSE contains GPLv2. Several utility/Unitree
package manifests contain TODO license declarations; ROS-TCP-Endpoint has Apache
2.0. There is no repository-root LICENSE in this snapshot. Do not label the entire
bundle uniformly BSD; preserve component licenses and clarify ambiguous parts
before redistributing an adopted integration.

Original build and launch instructions are recorded in the manifest, not run.
The upstream README records external-computer data delay, occasional SLAM drift
and Unity bridge startup issues. These identify known integration conditions;
they are not a head-to-head reliability rate or proof that the source fails to
build. Tests found in the release do not constitute a stair-navigation regression
suite.

## Primary references

- [Fixed Go2 repository](https://github.com/jizhang-cmu/autonomy_stack_go2/tree/43d5f54b389b251713f0097893c30fa76c870d54)
- [Robot command path](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/base_autonomy/local_planner/src/pathFollower.cpp#L429)
- [Terrain encoding](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/base_autonomy/terrain_analysis/src/terrainAnalysis.cpp#L606)
- [Local defaults](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/base_autonomy/local_planner/launch/local_planner.launch#L25)
- [FAR defaults](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/route_planner/far_planner/config/default.yaml#L13)
- [Simulation integration](https://github.com/jizhang-cmu/autonomy_stack_go2/blob/43d5f54b389b251713f0097893c30fa76c870d54/src/base_autonomy/vehicle_simulator/src/vehicleSimulator.cpp#L285)
- [Author development environment](https://www.cmu-exploration.com/)
- [Underlying ground autonomy release](https://github.com/jizhang-cmu/ground_based_autonomy_basic)
- [FAR paper](https://arxiv.org/abs/2110.09460)
- [Author platform abstract](https://gfchen01.cc/publication/navplatform/NavPlatform.pdf)

## Verification performed

`inspect_source.py` checks the fixed commit and clean reference checkout, records
SHA-256 for materialized files, parses package and launch metadata, checks the
small path tables and illustrates the two source filtering predicates. It runs
no upstream navigation code. The report does not claim a ROS build, simulator
result, robot result, integration or accepted baseline change.
