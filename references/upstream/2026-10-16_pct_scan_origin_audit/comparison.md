---
origin: ai_only
reviewed: false
status: surveyed
date: 2026-10-16
---

# PCT–SCAN stair failures: original algorithms, imported integration, and Lite3 changes

**Assessment: the evidence does not support rejecting PCT and SCAN as inherently
unsuitable for stairs. The recent regressions have concrete local integration
and locomotion-transition causes. The remaining geometric failures require
separating genuine collision/support limits from false rejection by the modified
map and planner. Reverting everything to upstream is not an established remedy.**

## Scope and source identity

Three different sources must not be collapsed into “the original”:

| Source | Fixed commit | Role |
|---|---|---|
| `byangw/PCT_planner` | `35cd73fd82bcd51bc538429294af7646b2a09815` | Author's tomography, multi-layer global search and trajectory optimization |
| `wuyi2121/SCAN-Planner` | `348e8a590a50a5a6bbab8d8c6dcfd171f009be26` | Author's route-guided quadruped local planning |
| `yagami-light7/PCT-SCAN-ROS2` | `1cf45a1c12ca785ce533293302be09d51daf0ccb` | Community ROS 2 integration actually used as our import source |

All three remote default heads matched these pins when acquired. Read-only
sparse checkouts and hashes are in [source inventory](source_inventory.json).
No upstream build, navigation run or new physical experiment was performed.

The existing import's 65 base/ported files match their recorded hashes; 61 also
match freshly acquired canonical files. Four sparse omissions are two RViz
configurations and two ROS message definitions. Eight initial Foxy-adapted files
contain recorded dependency/header/callback changes and body-to-world odometry
velocity conversion. This is not evidence of an initial optimizer rewrite.
See [import verification](initial_import_verification.json).

The current accepted source pointer is v219, with v220 as display. **Earlier
discussion ending at v208 is superseded by v210–v219 records.** The v219 build
receipt resolves 136 selected planner, mapping and PCT source/config files to
byte-identical local frozen files; see [resolution](local_source_resolution.json).
This prevents accidentally reviewing an old header as the current implementation.

## 1. Original algorithms do address stairs, within specific assumptions

PCT's original `tomography/config/scene_building.py:13` includes headroom, slope,
step and standable-neighborhood settings. `tomography/scripts/kernels.py` uses
these to assign terrain cost; `planner/lib/src/a_star/a_star_search.cc` searches
height-associated layers. Its Building example explicitly includes stairs,
slopes and overhangs. This is not an ordinary planar planner accidentally assigned
a stair task.

SCAN's original `scan_replan_fsm.cpp:357` accepts a spatial reference path and
adds configured body height to input ground-route points. Its projected A-star
and B-spline planning preserve a supplied vertical trend while avoiding obstacles.
`bspline_optimizer.cpp:1154,1182` explicitly zeros the z-gradient. Its README
documents multi-floor/keypoint and reference-route modes and instructs users to
check body/keypoint/path height when stair climbing fails. The paper reports
stair and cross-floor Go2 experiments.

These are real stair-oriented design choices, but neither algorithm provides
Lite3's joint-level stepping, contact stabilization or a guarantee that every
geometrically feasible path is physically executable. SCAN's dependence on
reference height also limits how it can repair a wrong vertical route: horizontal
deformation cannot always solve a vertical collision. “Whole-body collision” in
this implementation refers to the yaw-aware twin-cylinder model, not a rollout
of every leg and foot contact.

## 2. The imported integration was a weaker baseline than a physical stair system

The community integration changes more than ROS syntax. Its reference processing
uses distance/RDP simplification and a piecewise-linear global reference instead
of the author's minimum-snap global reference; its native local B-spline still
does the smoothing. This can preserve stair corridors and is not by itself a bug.
Source diffs are in `raw_logs/diffs/author_to_community/` and the index is
[SCAN source comparison](scan_source_comparison.json).

More decisively, the community Building launch defaults
`enable_local_sensing=false`:

- `src/integration/pct_scan_bridge/launch/building_pct_scan.launch.py:36`.
- The warning at lines 130–137 says enabling sensing is experimental because
  dense stair points can trigger SCAN inflation and emergency stop.
- `src/planner/plan_manage/launch/simulator.launch.py:80` actually guards creation
  of the local sensing node with that flag.
- `README.md:217` states that the video mode omits sensing to avoid this conflict.

This does **not** disable sensing in the author's SCAN release or in our current
Lite3 experiments. It means the imported integration's stair animation did not
establish complete sensor-driven, physical stair navigation. Some later work is
closing an inherited integration gap, not breaking a previously proven system.

## 3. Dataflow differences in the current Lite3 implementation

| Stage | Original / imported behavior | Local behavior and interpretation |
|---|---|---|
| PCT terrain | Original Building example: step limit 0.17 m, standable ratio 0.20, interval-free 0.65 m | Historical map generation used 0.30 m, 0.50 and 0.50 m respectively, plus changed inflation/margin. These are different terrain assumptions, not automatically an improvement or a bug. |
| PCT map | Tomography cost/height/ceiling layers | Current map additionally applies physical-support coverage vetoes: preserved elevations, no lowered costs, 3,219 previously traversable cells newly blocked in the recorded coverage derivation. |
| PCT native core | Multi-layer A-star and optional GPMP optimization | 63 of 77 compared native source/header files are byte-identical to the author. Differences include dependency/API compatibility and actual fixes such as resetting A-star state after failed/empty-result searches. This count is not proof of end-to-end parity. |
| Route height | SCAN original adds 0.4 m to supplied ground-route z | Archived current planner configuration has `grid_map.body_height=0`; the local PCT wrapper/profile supplies the body reference. A difference in this parameter alone is not evidence of a missing or duplicated 0.4 m offset. |
| Local collision | Inflated occupancy at two body-relative cylinder centers | Local `reactiveOccupancy` also checks input validity/age, unknown occupancy, terrain support, nearest floor association and footprint support. Unknown uninflated cells can pass the original buffer query but be rejected locally. |
| Collision geometry | Original radius 0.25 m, cylinder offset 0.18 m, vertical inflation 0.1/0.1 m | All four inspected v210/v212/v217/v219 runtime configurations use radius 0.35 m, offset 0.18 m, vertical inflation 0.55/0.35 m. This materially changes feasible clearance and depends on correct terrain separation. It does not alone establish excessive conservatism. |
| Terrain separation | Original scan occupancy has no matching local support-classification layer | Local code classifies terrain returns using selected PCT/physical surfaces and an ETH-style step adaptation, with a 0.26 m local hard height parameter. PCT's 0.30 m setting and this parameter use different neighborhood tests; they must not be equated to identical certified riser limits. |
| Trajectory acceptance | Native optimization and collision checks | Added boundary-PVA checks, final full-curve checks and a 0.6 m/s minimum-cruise criterion outside acceleration/deceleration boundary regions. Re-timing that violates dynamic limits is rejected. This is not a downstream command-floor clamp. |
| Replanning | Original SCAN is state/displacement/collision triggered | Local system added nominal 30 Hz rounds, Nav2 ownership/retries, route revisions, and then event-triggered PCT refresh. These interactions need their own correctness checks. |
| Execution | Original controller outputs body velocity, including zero commands | Lite3 additionally has RL-to-PD standing transfer and a measured physical goal-completion contract. A temporary zero command can therefore cause an extra control-mode transition absent from the original navigation code. |

Local anchors are resolved in `local_source_resolution.json`, notably v196
`plan_env/include/plan_env/scan_reactive_grid_methods.inc:417`,
`reactive_collision.h:115`, `eth_step_score_adaptation.h:25`, and v202
`plan_manage/src/planner_manager.cpp:521,793`. Runtime parameter files were read
from the archived original trials, not inferred from package defaults.

The known-footprint exception only converts unknown, uninflated queries inside
the measured current footprint to free. It does not erase observed obstacles or
clear arbitrary space ahead. Removing every such adaptation is not necessarily
a faithful or useful recovery strategy.

## 4. Failures that can be attributed to local integration

### Event-triggered global planning omitted a necessary failure signal

The v212 change replaced periodic global refresh with goal-change/recovery
triggers. It preserved PCT/SCAN/Tracker geometry and locomotion. In the same first
54.14 s, observed route deliveries fell from 39 to one; the trial fell after
persistent local failure and an intermediate stop.

The interface defect is concrete: the global owner lacked the native local
planning-result signal, and an expired braking trajectory could still satisfy
`haveTrajectory()`. v217 exposed expiry starvation and requested recovery only
after braking; it remained upright but exhausted six route retries on the stair.

v219 adds boolean local-result reporting, bound to route generation/revision,
and requests global replanning after 0.75 s of continuous failures while retaining
a usable curve. The route owner processes only matching current-route requests.
The native callback-removal hash check confirms that this change does not edit
the parent's SCAN geometry, search or optimizer. One complete route then passed.

Sources: v212/RESULTS.md; v217/RESULTS.md; v219/RESULTS.md;
v219 `src/scan_nav2_controller/include/scan_nav2_controller/motion_exchange.hpp:42`;
`src/lite3_nav2_plugins/include/lite3_nav2_plugins/plan_on_goal_change.hpp:47`;
`native_geometry_equivalence.json`.

This establishes an integration weakness and a successful repair condition. It
does not prove that every preceding collision rejection was false, or establish
a statistically measured reliability improvement from these individual runs.

### Standing-transfer defects belong to our execution layer

The v208 standing implementation admitted quiet body/joint states without
requiring support under all four feet for the dwell, and did not immediately
abort disturbed transitions. v212's physical fall occurred after an intermediate
stop and entry into that transition. v216 adds supported admission and immediate
transition abort; these mechanisms are outside the original PCT/SCAN planners.

This audit reran the **existing** 14-test v216 behavior suite against both actual
implementations, without a simulator or policy inference:

| Implementation | Tests | Failed assertions/subtests | Errors |
|---|---:|---:|---:|
| v208 | 14 | 35 | 0 |
| v216 | 14 | 0 | 0 |

See [replay result](transfer_replay.json) and preserved raw logs. This is direct
component-level evidence of the local behavior defect, not a replay proving
that one condition exclusively caused the entire physical fall.

The final v219 run also experienced a recovered fixed-stand disturbance on the
stair. It must not be described as uninterrupted stable stair standing.

## 5. What archived logs establish, and what remains unresolved

The audit read archived v210/v212/v217/v219 `nav2.log` and `planner.yaml` on
gpu5070ti, returning compact extracts and hashes. No remote source was changed
and no experiment started. [Failure evidence](failure_evidence.json) retains
the exact messages. Counts below are log occurrences in the interval associated
with planning-round start times 45–55 s, **not independent failed rounds**.
Diagnostics may be throttled; absence is not proof a branch never mattered.

- v212 and v217 contain occupied-space decisions and failed A-star guidance.
  Their sampled windows contain zero `minimum_cruise_dynamic_limit_rejected`
  messages. It is not supported to name the minimum-speed gate as the dominant
  cause of those two failures.
- v219 has three such minimum-cruise dynamic-limit rejection messages in that
  window, and v210 has five. The added speed requirement does reject candidates,
  including in successful runs. Its reliability contribution needs a controlled
  same-input comparison.
- v217 records `local_trajectory_starvation` at 0.769577 s against the 0.75 s
  limit; v219 records one at 0.754585 s. Replanning improvements did not remove
  every pause.
- PCT/SCAN's original optimizer can reject an initial trajectory in occupied
  space. The existence of such a message does not identify whether the obstacle
  came from real geometry, the wider body envelope, ground classification,
  missing coverage, or a changed initialization. These must be distinguished
  with the exact query and map state.

Recorded completed local-round counts in the 45–55 s interval are 250/253 for
v210, 29/137 for v212, 2/181 for v217 and 118/208 for v219. The runs pass through
different physical states/times; these are descriptive trial measurements,
not matched-state algorithm success rates. v219 passed one full route in
123.564 s with 9.39 cm final XY error and 4.338 s final fixed PD; its current
record does not establish repeated reliability.

## 6. Engineering judgment and the next useful discriminator

1. Do not replace PCT–SCAN on the premise that stairs are outside its design.
   The source and author evidence contradict that premise.
2. Treat recent global/local failure notification and standing transfer as
   implementation responsibilities. Their defects are independently reviewable.
3. Keep the remaining geometric attribution open. The local executable is
   substantially modified; “SCAN rejected it” no longer uniquely identifies an
   original SCAN limitation.
4. The next discriminating test should feed the same captured stair points,
   body pose and reference to the original collision query and the local
   query, then identify the exact added predicate responsible for each different
   decision. Compare terrain/unknown/support, geometry and speed requirements
   separately. A candidate passing the original query still needs physical
   feasibility checking before calling the local rejection wrong.

That same-input replay is proposed, not claimed executed here. The current
review completes source comparison, archived-log inspection and the standing
component replay; it does not change navigation code, frozen versions, physics,
acceptance thresholds or the adopted baseline.

## Primary sources

- [PCT author code](https://github.com/byangw/PCT_planner/tree/35cd73fd82bcd51bc538429294af7646b2a09815)
- [PCT Building settings](https://github.com/byangw/PCT_planner/blob/35cd73fd82bcd51bc538429294af7646b2a09815/tomography/config/scene_building.py#L13)
- [SCAN author code](https://github.com/wuyi2121/SCAN-Planner/tree/348e8a590a50a5a6bbab8d8c6dcfd171f009be26)
- [SCAN path height contract](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_manage/src/scan_replan_fsm.cpp#L357)
- [SCAN occupancy query](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/plan_env/include/plan_env/grid_map.h#L365)
- [SCAN z-gradient suppression](https://github.com/wuyi2121/SCAN-Planner/blob/348e8a590a50a5a6bbab8d8c6dcfd171f009be26/src/planner/bspline_opt/src/bspline_optimizer.cpp#L1154)
- [SCAN paper](https://arxiv.org/html/2606.19555v1)
- [Community Building sensing warning](https://github.com/yagami-light7/PCT-SCAN-ROS2/blob/1cf45a1c12ca785ce533293302be09d51daf0ccb/src/integration/pct_scan_bridge/launch/building_pct_scan.launch.py#L130)
