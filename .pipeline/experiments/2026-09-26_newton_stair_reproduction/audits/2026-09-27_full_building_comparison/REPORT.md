# Historical full Building success versus Newton v7

Stage: experiment + analysis. Diagnostic review requested by Dr Sun.

## Finding

The historical success is real. The current failure has a reproduced planning
block before cruise retiming, followed by an unreported native planner stop.
The current system is a substantially changed planning/input/control integration;
it is not the old successful configuration with only a simulator replacement.

No production source, frozen version, original run, or sibling file was changed.
No new physics episode was run. This review does not validate a repair.

## Identity and conditions

The historical workspace matches all 65 upstream-manifest entries and all 62
selected source files present in the successful run's executed-source manifest.
All 205 current source/configuration files and their v7 frozen copies match the
v7 manifest. The difference is not an unexplained file corruption.

| Item | Historical `native_full02` | Current `v7_building_route01` |
|---|---|---|
| Physical execution | Isaac Sim / PhysX | Newton / MuJoCo-Warp on CPU |
| Building and PCT map | Original Building bytes | Same source hashes |
| PCT route | 631 points, 73.2373 m XY | 46 points, 5.0011 m XY |
| Goal ground XYZ | `[1.9547,-2.9868,4.5330]` | `[-5.3,1.0,0.8765]` |
| Start XY / yaw | `[-5.5453,6.0132] / -1.3258` | `[-5.42,6.0132] / -1.5708` before factory startup |
| Native planner | Pinned PCT-SCAN-ROS2 `1cf45a1c` plus documented ports | Reactive/P2B lineage from archived scan28, later native candidates, local v3-v7 |
| LiDAR pattern | 2,880 rays, 16 regular vertical channels | 20,000 Livox-pattern rays per scan |
| First returned points | 1,699 | 9,448; different pose/time, not a paired sensor ablation |
| Reference body height | 0.35 m | 0.30 m; spawn remains 0.35 m |
| Cylinder radius / offset | 0.25 / 0.18 m | 0.35 / 0.18 m |
| Vertical inflation up / down | 0.10 / 0.10 m | 0.55 / 0.35 m |
| Controller limits | X 1.0, Y 0.35, yaw 1.0 | Same |
| Controller lookahead / gains | 0.8 s / position 0.8 / yaw 1.5 | Same; P2B ownership interface added |
| Robot URDF mass sum | 11.9376 kg | 13.2818 kg, including additional fixed rig/interface links |
| Policy | V12 `model_149999` checkpoint | ONNX export traces to the same checkpoint SHA |
| Physics / policy step | 0.005 / 0.020 s | 0.001 / 0.020 s |
| Startup and stop ownership | Original V12 runtime | Factory PD startup and PD/RL state transitions |

URDF sums are source-level measurements, not independently measured simulator
effective mass. A common checkpoint does not prove equivalent observations,
actuator delay, contacts or dynamics. The old runtime declares actuator delay
0-4; the current adapter directly applies saturated PD torque each substep.
These differences need separate physical controls if dynamics becomes the
remaining blocker. They do not explain away the native planning rejection
reproduced here without running physics.

Seventeen shared native files differ and 35 native files have been added.
`comparison.json` records the per-file differences and YAML key differences.
Missing YAML keys are not automatically changed effective defaults.

## 1. The route is shortened by the current collision/support decision

The first historical published moving curve is 3.7033 m long, lasts 5.76 s,
and reaches 0.9953 m/s planned XY speed. The complete run publishes 74 moving
curves and records 74.0629 m of actual XY travel, ending 0.03768 m from the goal.

Current v7 publishes only three moving curves, with XY lengths
0.56725, 0.23680 and 0.16990 m. Each is a short acceleration/braking segment
with zero cruise samples. No minimum-cruise rejection is logged. Raising a
speed setting cannot make these blocked planning windows longer.

The recorded sequence is:

1. A 5 m PCT route is accepted at simulation time 12.1913 s.
2. Collision checks force the first local curve down to a short prefix.
3. The safety check interrupts the first curve; subsequent retries produce
   two shorter curves.
4. At about 17.712 s the selected free frontier is at route time 0.3479057,
   effectively the previous curve's endpoint. Continued target selection fails.
5. After 1,000 failed replanning rounds, SCAN transitions through emergency
   stop into `WAIT_TARGET`, around 21.9945 s.

### Native reproduction

The existing v6 frontier diagnostic was reused with **the original 66 recorded
scans, their paired poses, the latest recorded body message, the original PCT
route, spline 4 and the original v7 YAML**. The PCT ground payload hash is
checked against the actual v7 publisher log. The native source and installed
libraries are mounted read-only.

Both independent replay processes return exactly the same result and query
CSV bytes:

- Current time: `17.711894989 s`.
- Free frontier: `[-5.442933631046, 5.673399323463, 0.432716154793]`.
- Proposed displacement from the previous spline: `1.97e-8 m`.
- `getLocalTarget=false`, `hasLocalTranslation=false`,
  `planFromCurrentTraj=false`.
- No continuation reaches the optimizer or speed-floor evaluation.

The direct target check uses a heading from actual body position to the target;
the frontier scan uses the reference tangent. At this almost-zero continuation,
these headings differ substantially. One orientation is collision-free and the
other places a cylinder center in an unknown-support cell. Changing heading
alone would not create forward progress: the selected endpoint is already used.

## 2. Two concrete added terrain rules participate in the block

### A. Existing terrain is turned into unknown support

At the rejected target's front cylinder query, the raw native occupancy is
known and the inflation buffer is **zero**. A ground surface at **0.193115 m**
exists in that cell, but its adapted step score is unknown (`known=0`,
`first_height=NaN`). The added collision layer returns verdict 8,
`UnknownSupport`, and blocks it.

The local `eth_step_score_adaptation.h` requires complete, unambiguous same-layer
neighbors in both scoring passes. A missing neighbor invalidates the window.
The pinned ETH `StepFilter.cpp` instead skips invalid neighbors in each pass
(lines 126-127 and 159-160). This strict completeness behavior is a **local
adaptation**, not unchanged upstream behavior. Sparse cost-selected PCT cells
and that rule must be evaluated together. It would be unsafe to infer that
every unknown cell should simply become free.

### B. A retained nonterrain label blocks currently supported terrain

Just ahead on the original reference (`t=0.40`, body reference approximately
`[-5.44258,5.62252,0.44390]`), the front support is valid. Native inflation has
two raw occupied contributors. One is classified terrain only; the other,
voxel center **`[-5.575,5.125,0.175]`**, has these flags:

`confirmed terrain=1, current nonterrain=0, historical nonterrain=1`.

The actual `mayWaiveRawContributor` contract refuses to waive that contributor
because historical nonterrain takes precedence. The voxel center itself passes
the current terrain-return classifier. Farther reference samples have multiple
such mixed/retained classifications. These are actual native map observations,
not an object-class assumption about pedestrians.

The historical label is cleared when occupancy falls below occupied or the map
cell is reset; it is **not permanently immortal**, and current terrain evidence
alone does not clear it. That distinction matters for any repair. The broad
vertical inflation also makes low stair returns relevant to a body-height
collision query. See `details/replay.log` for source contributions and scores.

An additional single-label diagnostic temporarily removes only this one history
entry from a disposable map, queries the identical point, then restores the
entry. The result is **blocked -> free -> blocked** (`1 -> 0 -> 1`). This
isolates that label as the cause of this particular native collision verdict;
it does not isolate every blocked point on the route. Its result is recorded in
`counterfactual/one_label_counterfactual.json`; it is not a proposed production
change and does not demonstrate a safe full-route repair.

## 3. Native failure is not reported to the task owner

`SCANReplanFSM::finishProcess()` handles the 1,000-failure limit by setting
emergency-stop flags, but publishes no P2B failure/stop admission. The subsequent
emergency exit clears the native target and switches to `WAIT_TARGET`.

The actual admission log contains a controller acceptance of stop spline 5 at
21.9945 s, but no failed/stopped admission then. The backend therefore retains
an accepted owner and an open gate while the native planner waits for a new
target. No new target is submitted. The first stopped admission occurs only at
89.9622 s, during end-of-episode odometry shutdown. No terminal result file is
produced. This explains the long apparent hang after physical progress ends;
it is distinct from the collision decision that first prevented progress.

## Repair order recommended by this audit

1. Preserve the historical full route and exact old stack as a control; preserve
   v7. Fix the terrain/obstacle evidence seam using the recorded first blocked
   stair input. Inspect the pinned upstream terrain/map handling before choosing
   an implementation. Do not delete history or weaken unknown-space handling
   globally. Retain box, wall, thin-object and person negatives.
2. Separately propagate native replan exhaustion to the owning P2B task so that
   it reports failure and a confirmed stop instead of remaining accepted.
3. Repeat the short stair case, then the actual 73 m historical route with
   measured speed and terminal stop. Only then vary robot/sensor/dynamics
   conditions one at a time if failures remain.

Each production behavior/configuration change requires its own next version;
this diagnostic review does not create v8. Increasing the speed floor or changing
the entire system back at once would not isolate the verified blocking cases.

## Evidence and reproduction

- `comparison.json`: original-record measurements, configuration/source checks,
  source hashes, admissions and repeated native results.
- `replay01.json`, `replay02.json`, associated logs/CSV: original-input native
  target-selection failure with exact repeated results.
- `details/replay.log`: native terrain/support/occupancy contributors.
- `counterfactual/`: isolated one-label diagnostic, explicitly not navigation.
- `request.json`, `execution.json` and per-probe equivalents: pinned Docker
  image, read-only mounts, no-network execution and bounded process outcomes.
- `LOCAL_ONLY_BYTES.json`: generated input/build file hashes and regeneration
  commands. Only these narrow derived paths are ignored; original evidence and
  review outputs remain tracked or explicitly indexed.

The full original sensor stream has not been run through both historical and
current complete stacks in this audit. No claim follows that one parameter is
the sole cause of every earlier stair failure, or that the old success proves
the newer sensor-driven obstacle-generalization requirement.
