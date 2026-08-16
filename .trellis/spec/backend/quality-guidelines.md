# Quality Guidelines

> Code quality standards for navigation integration and evidence-producing runtimes.

---

## Overview

Navigation integration crosses binary transport, ROS messages, simulator state,
and evaluation artifacts. A passing unit test at one layer is not enough: the
serialized value must be checked at the next consumer and its physical effect
must be checked at runtime.

## Forbidden Patterns

- Passing network-order numeric payload bytes directly to a host-native ROS or
  PCL message. Convert byte order explicitly and test known float values.
- Classifying a simulated sensor hit only by a loose bounding box when another
  surface can occupy the same projection. Require a discriminating condition
  and retain raw hit counts.
- Treating sensor configuration as proof that every named mesh is in the actual
  ray-cast acceleration structure. Inspect runtime mesh-load evidence and prove
  non-ground returns.
- Relaxing planner collision thresholds to hide malformed clouds or frame
  errors.
- Promoting a transport, sensor, planner, or policy preflight into a closed-loop
  validation claim.

## Required Patterns

- Include frame, unit, numeric encoding, byte order, timestamp, and ownership in
  every cross-process sensor contract.
- Hash perception preprocessing settings into the run identity. Keep raw and
  filtered counts so filtering remains auditable.
- Fail closed on command drift, malformed payloads, non-finite values, stale
  commands, disconnects, collisions, and resets.
- Freeze acceptance thresholds after dry runs and before the acceptance run.
- Preserve failed runs unchanged and distinguish instrumentation failures from
  algorithm failures.

## Testing Requirements

- Protocol tests cover framing, partial reads, CRC, limits, timestamps,
  sequences, invalid numeric data, reconnects, saturation, and watchdog stop.
- Numeric boundary tests verify the exact bytes consumed downstream, not only
  encode/decode symmetry inside one module.
- Sensor gates distinguish traversable-floor returns from obstacle-surface
  returns and prove pose-dependent geometry.
- Full integration records planner output, commands, policy observation,
  physical motion and contacts, rendered sensing, and feedback in one run.

## Code Review Checklist

- Does each claim identify `surveyed`, `reproduced`, `integrated`, or
  `validated` evidence?
- Is every binary or frame conversion explicit and covered downstream?
- Can ground, robot self-returns, or stale frames masquerade as obstacles?
- Does a physical obstacle appear to both sensing and collision systems?
- Are source, checkpoint, config, logs, metrics, ROS recording, and video
  synchronized locally and hash-verified?

## Scenario: Articulated Locomotion Follows a Perception-Replanned Trajectory

### 1. Scope / Trigger

Use this contract when a local planner advances a time-parameterized trajectory
for a policy-controlled articulated robot, especially when the occupancy map
is built from surface-only LiDAR returns. A kinematic follower's wall-clock
assumptions do not transfer automatically to a locomotion policy.

### 2. Signatures

- Trajectory progress decision:

  ```cpp
  TrajectoryProgressDecision decideTrajectoryProgress(
      double current_time,
      double dt,
      double duration,
      const Eigen::Vector2d &current_position,
      const Eigen::Vector2d &candidate_position,
      double max_tracking_error);
  ```

- Occlusion shadow projection:

  ```cpp
  std::vector<Eigen::Vector3d> occlusionShadowPoints(
      const Eigen::Vector3d &sensor_position,
      const Eigen::Vector3d &hit_position,
      double shadow_length,
      double resolution);
  ```

- Scenario parameters:

  ```yaml
  grid_map.double_cylinder_radius: <metres>
  grid_map.double_cylinder_offset: <metres>
  grid_map.occlusion_shadow_length: <metres, 0 disables>
  fsm.periodic_replan_enabled: <boolean>
  closed_loop_controller.max_tracking_error: <metres>
  ```

### 3. Contracts

- Evaluate trajectory progress against the candidate point at `current_time +
  dt`. If its planar distance from measured body pose exceeds
  `max_tracking_error`, keep the current trajectory time and publish the frozen
  state to the planner; continue commanding toward the current trajectory
  point rather than jumping ahead.
- Match planner and controller speed limits to the velocity-policy response
  demonstrated by the qualification gate. Transport saturation may be wider,
  but the trajectory generator and follower must share the accepted limit.
- Inflate physical obstacle hits by the declared robot proxy. When a sensor
  initially exposes only a surface, optionally mark points behind the hit along
  the same physical ray at voxel resolution; do not manufacture points in
  front of the hit or use scene-truth obstacle bounds as planner input.
- If distance-only periodic replanning is disabled, a separately timed safety
  callback must continue checking the active trajectory and must replan or
  fail closed when new occupancy invalidates it.
- Stop live command and telemetry transport at the simulation-time boundary
  before video encoding or slow simulator teardown. Post-run packaging must
  not consume queued commands or alter live transport statistics.
- Once trajectory time reaches its duration and measured pose first enters the
  declared finish tolerance, latch zero command until a new trajectory arrives.
  Do not let post-goal physical drift reopen a completed trajectory and create
  low-speed endpoint hunting.
- A formal run records hashes for the acceptance file, scenario configs,
  relevant source, executed binaries/libraries, container image, checkpoint,
  and policy source. Preserve every failed frozen run.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Candidate trajectory point exceeds tracking-error bound | Freeze trajectory time; do not skip ahead |
| Non-finite or non-positive shadow length/resolution | Disable shadow projection or reject configuration before runtime |
| Sensor origin equals hit point | Return no shadow points |
| Active trajectory intersects new inflated occupancy | Safety callback replans; imminent failure triggers emergency stop |
| Replacement candidate fails while active trajectory is still safe | Keep the active trajectory; never promote the failed candidate |
| Command frame is stale during live simulation | Reject it and fail closed |
| Simulation stepping has ended | Close transport before packaging; shutdown backlog is not a live protocol error |
| Frozen run fails collision, planning, transport, or goal gate | Preserve it unchanged and return to the owning phase |

### 5. Good / Base / Bad Cases

- **Good:** policy-qualified speed, measured-pose time freeze, conservative
  surface occlusion, event-driven safety replanning, zero collision, and an
  input hash manifest.
- **Base:** kinematic simulation may advance by trajectory time directly, but
  it cannot be promoted into the articulated physical-simulation claim.
- **Bad:** the desired trajectory is collision-free while the slower robot cuts
  the corner; the evaluator is then weakened to hide the contact.

### 6. Tests Required

- Unit-test the exact captured corner-cut positions: a candidate more than the
  tracking bound away must freeze, while a near candidate advances and clamps
  at duration.
- Unit-test the terminal latch: it remains false before trajectory duration or
  outside tolerance, becomes true at the first in-tolerance endpoint sample,
  and remains true after later pose drift until a new trajectory resets it.
- Unit-test shadow sample count, first/last sample position, disabled values,
  and degenerate rays.
- Run the full fixed-course loop at least twice with identical input hashes
  before a new formal acceptance run after a non-deterministic planning fix.
- Assert zero planner failures, zero origin-occupancy errors, zero protocol
  errors, zero watchdog events, physical detour, no non-foot collision, stopped
  command, and goal tolerance.
- Compare local and remote hashes for raw metrics, ROS bag, logs, MP4, configs,
  source, binaries/libraries, and image identity.

### 7. Wrong vs Correct

#### Wrong

```cpp
trajectory_time += wall_clock_dt;
```

```text
LiDAR surface hit -> mark one surface voxel -> treat all occluded volume free
```

#### Correct

```cpp
const auto progress = decideTrajectoryProgress(
    trajectory_time, dt, duration, measured_xy, candidate_xy,
    max_tracking_error);
trajectory_time = progress.next_time;
```

```text
physical LiDAR hit -> optional bounded shadow at voxel resolution
                   -> physical robot-envelope inflation
                   -> independently timed trajectory safety check
```

## Scenario: Compose a Pinned Locomotion Policy with a Sensor-Rig URDF

### 1. Scope / Trigger

Use this contract when an existing policy-qualified robot runtime is moved to a
new URDF that adds payload, collision geometry, fixed sensor frames, or live
simulated sensors. A source URDF hash or successful import alone does not prove
that the policy contract, physical composition, or sensor data path is valid.

### 2. Signatures

- V3 asset override:

  ```text
  --robot-asset <Isaac-safe URDF>
  --canonical-robot-asset <canonical URDF>
  ```

- Required runtime evidence:

  ```text
  runtime_composition.json
  run_identity.json
  sensor_metrics.jsonl
  depth_metrics.jsonl
  qualification_report.json
  ```

- Sensor-frame contract:

  ```text
  MID-360-like point stream -> mid360_scan_frame -> SCAN
  D435i-like depth stream   -> d435i_depth_optical_frame -> evidence only
  ```

### 3. Contracts

- Treat the policy/controller and robot asset as separate immutable identities.
  Hash the checkpoint, policy source, observation dimension, action ordering,
  default pose, actuator configuration, timing, seed, command schedule,
  canonical URDF, Isaac-safe URDF, and referenced meshes.
- Change only the spawn asset and fixed-joint import setting for the
  single-variable qualification. Reject accidental changes to the 450-value
  observation, 12-action contract, command limits, or watchdog.
- Preserve fixed sensor-frame joints and read back bodies, joints, masses,
  inertias, collision prims, and named sensor frames from the instantiated USD
  stage. Explicit tiny inertials used only for fixed frame bodies must be
  declared; silent importer default mass is forbidden.
- Bind sensors to the imported named frames. A task-relative transform or a
  visible sensor mesh without live data does not satisfy the contract.
- For rig self-occlusion, ray-cast against the moving visual surface that
  represents the blocker. Broad collision proxies may be used for physics but
  must not silently replace visual geometry in the optical mask. A self hit
  blocks the environmental ray; it must not be removed and allowed to pass
  through the robot.
- Record sensor backend, FOV, range, rate, sample grid/resolution, transforms,
  filtering, self-occlusion counts, finite/nonempty counts, timestamps, and
  pose-dependent change. Declare simulator-truth pose explicitly.
- When a hardware-specific RTX profile is absent or its creation/output/
  teardown lifecycle does not complete, preserve the probe and use a named
  geometric fallback. Do not substitute another vendor profile or claim
  hardware parity.
- Run at least two identical-input passing dry runs before freezing a new
  acceptance configuration. Preserve earlier failures and do not relax a
  physical or sensor threshold after observing the formal result.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Canonical or Isaac URDF hash differs | Stop before simulator import |
| Policy/checkpoint/observation/action invariant differs | Reject the comparison as multi-variable |
| Fixed sensor frame is merged or absent at runtime | Fail asset qualification |
| Runtime body receives undeclared default mass | Fail asset qualification |
| Collision-proxy self mask removes all environmental rays | Preserve failed preflight; switch only to declared visual-surface occlusion |
| Sensor stream is empty, non-finite, static in time, or task-relative | Fail sensor qualification |
| D435i intrinsics lack depth-camera calibration evidence | Label provisional; do not claim hardware parity |
| RTX profile or teardown probe is incomplete | Reject RTX backend for the declared run and record the geometric fallback |
| A/B locomotion candidate terminates, loses support, or hits non-foot geometry | Stop before closed-loop integration; do not train or retune inside the gate |
| Local/remote artifact hashes differ | Do not promote or report the remote result |

### 5. Good / Base / Bad Cases

- **Good:** pinned policy and two URDF hashes, runtime topology/mass/collision
  readback, same-input old/new asset qualification, live data at both imported
  sensor frames, visual-surface self-occlusion, two passing dry runs, frozen
  gate, and local/remote evidence parity.
- **Base:** a legacy asset with a task-mounted ray caster can remain a clearly
  labeled baseline, but it cannot satisfy a sensor-rig acceptance criterion.
- **Bad:** show a new URDF in a viewer while the closed loop still spawns the
  old asset, publishes a hard-coded torso-relative scan, or treats a static
  depth image as a live D435i stream.

### 6. Tests Required

- Unit-test exact checkpoint/URDF/config hashes, required frame names, topology
  counts, mass tolerance, absence of missing/default-mass bodies, sensor
  settings, depth artifact hashes, invalid data, and identity serialization.
- Run the same zero/forward/lateral/yaw/zero/watchdog schedule on old and new
  assets with identical policy inputs. Assert finite state, response direction,
  support, no termination, no non-foot collision, and watchdog zeroing.
- Assert LiDAR and depth timestamps advance, data are finite and nonempty,
  scene obstacle evidence appears, poses change, and self-occlusion counts are
  recorded.
- Re-evaluate the copied formal artifacts locally with the frozen config,
  decode the MP4, parse JSON/JSONL/YAML, load the depth array, inspect ROS bag
  payload presence, and compare local/remote hashes.
- Leave the human acceptance criterion unchecked until the named reviewer
  records an explicit decision after watching the full video.

### 7. Wrong vs Correct

#### Wrong

```text
new URDF exists -> reuse old runtime PASS -> call the sensor rig validated
```

```text
collision proxy blocks ray -> delete self hit -> ray reaches obstacle behind robot
```

#### Correct

```text
pin policy + canonical URDF + Isaac URDF
  -> runtime readback
  -> same-input locomotion A/B
  -> live dual-sensor gate
  -> two passing dry runs
  -> frozen formal run
  -> local parity check
  -> human review
```

```text
visual rig surface blocks ray -> record self-occlusion -> no environmental hit
```

## Scenario: Qualify a Pinned Locomotion Policy on Procedural Forest Terrain

### 1. Scope / Trigger

Use this scenario when an already-qualified locomotion policy and robot asset
are exercised on imported or procedurally generated terrain, especially when
the run must also prove live simulated LiDAR/depth response and deliver a video
for human review. This scenario is an experiment gate, not a training or
planner-integration gate.

### 2. Signatures

- The runtime must expose an explicit forest course and immutable run inputs:

  ```text
  --course forest_gen
  --seed <integer>
  --checkpoint <pinned file>
  --canonical-urdf <pinned file>
  --isaac-urdf <pinned file>
  --output-dir <run-owned directory>
  [--record-video]
  ```

- The run bundle must contain at least:

  ```text
  qualification_report.json
  run_identity.json
  runtime_composition.json
  policy_metrics.jsonl
  sensor_metrics.jsonl
  depth_metrics.jsonl
  output_sha256.txt
  forest_lite3_v12.mp4       # when video is requested
  ```

  The generated terrain identity and static proxy audit may be embedded in
  `run_identity.json`, `runtime_composition.json`, and
  `qualification_report.json`; they do not require duplicate sidecar files.

- The launcher exit contract is independent of simulator shutdown behavior:

  ```text
  missing qualification_report.json -> exit 90
  qualification_report.status != PASS -> exit 91
  PASS report and complete artifacts -> exit 0
  ```

### 3. Contracts

- Verify the forest-source commits, checkpoint hash, canonical URDF hash, and
  Isaac-safe URDF hash before starting the simulator. Record the exact policy,
  robot, terrain, command schedule, sensor, physics, and seed identities.
- Do not infer determinism from an upstream `seed` parameter. Inspect every
  random-number source used by terrain and asset population. Either route the
  declared seed into all of them or freeze and compare the generated geometry
  hash across identical-input runs.
- Normalize upstream mesh visual types only when required by the simulator
  importer. Preserve the source vertices and faces, and record the resulting
  mesh hash so a rendering compatibility conversion cannot silently change the
  terrain.
- Every route-relevant tree or rock needs a visible source asset plus a
  registered collision/sensor proxy targeted by both the MID-360-like and
  D435i-like sensor queries. The simplified proxy may be hidden in the final
  review render only when runtime evidence records the visual/proxy pairing,
  bounds, transform, collision API, sensor targets, and hidden render state. A
  decorative asset beside an unrelated invisible collider does not satisfy
  this contract.
- Seat irregular source meshes from an actual low-surface datum or real mesh
  support vertices. A full axis-aligned box corner may contain no geometry and
  can make a non-penetrating asset visibly float on sloped terrain. Preserve
  the failed placement, record the chosen support points and clearance, and
  keep human appearance review separate from the numerical contact audit.
- Bind the policy command terrain key to the declared course without changing
  the pinned observation/action contract. The recorded command tensor, not
  only the requested schedule, is the evidence that zero/forward/yaw/stop
  reached the policy.
- Treat the machine-readable qualification report as the launcher truth
  source. Some simulator shutdown paths can swallow the Python process return
  code, so a shell exit code alone must never promote a run.
- Keep automated qualification and human visual acceptance separate. A
  decoded video can pass instrumentation while an occluding camera makes it
  unusable for review; preserve that run as superseded and record a new camera
  run without changing the experiment inputs.
- Preserve failed attempts, copy complete artifacts back to the local source
  of truth, and prove local/remote hash parity before reporting a run as ready
  for review.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Forest source commit, checkpoint, or URDF hash differs | Stop before simulator import |
| Identical seed produces a different terrain geometry hash | Fail reproducibility; seed all hidden RNGs or freeze the generated asset |
| Upstream visual mesh types cannot be concatenated by the importer | Preserve failure; normalize visuals without changing vertices/faces |
| Forest course is absent from the policy command-terrain mapping | Fail before policy inference; add an explicit unchanged-contract binding |
| Source visual is absent, or paired proxy lacks collision or either sensor target | Fail static geometry qualification |
| Full-box seating passes numerically but the source mesh visibly floats | Preserve the preflight; switch to a recorded real-surface support datum and repeat human review |
| Qualification report is missing after simulator exit | Launcher exits 90 even if the simulator process returned zero |
| Qualification report status is not `PASS` | Launcher exits 91 and preserves the report and logs |
| Video cannot be decoded or the robot is materially occluded | Keep automated result; mark video superseded and leave human review pending |
| Local/remote artifact hashes differ | Do not present the local bundle as the executed evidence |

### 5. Good / Base / Bad Cases

- **Good:** pinned identities, repeated identical terrain hash, visible source
  assets with registered collidable/dual-sensor-targeted proxies, real-surface
  seating evidence, recorded policy response on uneven ground, launcher report
  enforcement, complete local hash parity, decoded unobstructed video, and a
  separate pending human decision.
- **Base:** a deterministic flat or obstacle course can validate the policy and
  sensors, but it cannot be promoted as forest-terrain evidence.
- **Bad:** launch a photorealistic forest backdrop with a flat invisible floor,
  let LiDAR query different geometry from physics, trust process exit zero, or
  call an occluded video human-approved.

### 6. Tests Required

- Unit-test forest report evaluation, missing/static proxy rejection, identity
  serialization, command scheduling, and the launcher exit mapping.
- Run at least two identical-input terrain generations and assert the complete
  mesh hash is identical. Record the seed and all upstream commit hashes.
- Inspect the instantiated stage and assert terrain plus every route-relevant
  source visual is visible; assert its paired proxy has the declared render
  state, collision API, transform/bounds agreement, and both sensor targets.
- Execute the pinned policy on the terrain and assert finite state/action,
  scheduled command visibility, nontrivial displacement, terrain-height
  variation, support/contact bounds, and no hidden reset or termination.
- Assert LiDAR/depth timestamps advance, outputs are finite and nonempty,
  obstacle returns exist, and readings change with pose.
- Decode the full video, inspect representative frames, parse JSON/JSONL,
  verify the recorded terrain identity, and compare remote/local SHA-256
  manifests.
- Leave human acceptance unchecked until the named reviewer watches the full
  video and records a decision.

### 7. Wrong vs Correct

#### Wrong

```text
upstream seed set + simulator exit 0 + MP4 exists -> forest run validated
```

```text
photorealistic tree visual + separate invisible box + sensor-only mesh -> same obstacle
```

#### Correct

```text
pin policy + URDFs + forest commits
  -> seed every RNG / compare terrain hash
  -> inspect visible-collision-sensor geometry
  -> run recorded policy schedule
  -> enforce qualification_report.status
  -> copy and hash-check artifacts
  -> decode unobstructed video
  -> human review remains a separate decision
```

```text
visible source asset + registered proxy -> PhysX collision + LiDAR target + depth target
```

## Scenario: Coalesce a Buffered Command Backlog Without Relaxing Freshness

### 1. Scope / Trigger

Use this contract when a simulator or another non-real-time producer can pause
wall-clock command consumption while physics is also paused. A local TCP sender
may continue placing 50 Hz command frames in the socket buffer. This is a
latest-wins backlog case, not permission to widen the real-robot watchdog.

### 2. Signatures

- Atomic state update:

  ```python
  LatestCommandState.update_batch(
      updates: Sequence[Tuple[CommandV1, int, int, int]]
  ) -> CommandSnapshot
  # tuple fields: command, sequence, source_timestamp_ns, received_monotonic_ns
  ```

- Transport evidence:

  ```python
  TransportStats.coalesced_frames: int
  ```

- The receiver may collect at most 256 complete command frames that are
  already readable with a zero-timeout socket readiness check. It must not wait
  for a future frame to make a stale latest frame appear fresh.

### 3. Contracts

- Decode and validate every complete buffered frame. Observe every command
  sequence in increasing order before applying state, so intentional
  coalescing is not reported as packet loss.
- Intermediate source-stale commands are never applied. Apply only the newest
  command, and only when that newest source timestamp satisfies the unchanged
  `max_source_age_ns` and future-skew limits.
- A non-increasing sequence, malformed payload, non-finite value, future-skewed
  timestamp, or stale newest command rejects the whole batch through the
  existing fail-closed path. Validation must be atomic: a rejected batch may
  not partially advance the state sequence.
- Keep `timeout_ns` and `max_source_age_ns` at the scenario's previously
  qualified values. Record `coalesced_frames` separately from true sequence
  gaps, watchdog events, protocol errors, and reconnects.
- The formal run must hash both Isaac-side and Foxy-side protocol, transport,
  and command-state sources. Both process copies must be byte-identical.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Stale intermediates followed by a fresh latest frame | Observe all sequences; apply only latest; increment `coalesced_frames` |
| Newest buffered frame is stale | Reject batch and fail closed |
| Any frame has future skew or invalid numeric data | Reject batch and fail closed |
| Duplicate or decreasing sequence occurs inside batch | Reject atomically; retain prior sequence/state |
| Sequence is missing from the buffered batch | Count a real sequence gap |
| More than 256 frames are immediately buffered | Process a bounded batch; never allocate an unbounded queue |
| Formal run reports watchdog, protocol error, or reconnect | Preserve failure and return to transport diagnosis |

### 5. Good / Base / Bad Cases

- **Good:** a 275 ms simulator sensor synchronization leaves several valid
  frames buffered; the receiver validates the batch, applies the fresh latest
  command, reports bounded coalescing, and records zero gaps/watchdogs/errors.
- **Base:** a single fresh command uses `update()`, which delegates to the same
  one-element atomic batch contract.
- **Bad:** disconnect on the first stale intermediate frame, discard fresher
  frames behind it, then increase the watchdog until the acceptance report
  turns green.

### 6. Tests Required

- Send one combined TCP write containing multiple stale command frames followed
  by a fresh latest frame. Assert the latest value is active, every sequence is
  observed, `coalesced_frames` equals the skipped intermediate count, and gaps,
  watchdog events, and protocol errors remain zero.
- Unit-test that a stale newest frame and a future-skewed frame are rejected.
- Unit-test that an internal duplicate sequence leaves the prior state and gap
  count unchanged.
- Re-run the full sensor/render workload with the original source-age and
  watchdog values. Require zero reconnects, gaps, watchdog events, and protocol
  errors, and record the bounded coalesced-frame count in acceptance evidence.

### 7. Wrong vs Correct

#### Wrong

```python
frame = recv_frame(connection)
state.update(decoded(frame))  # oldest buffered frame can be stale
# On error: disconnect and lose fresher frames already queued behind it.
```

```text
stale backlog observed -> increase watchdog/source-age threshold
```

#### Correct

```python
frames = receive_complete_frames_already_buffered(limit=256)
updates = [decode_and_validate(frame) for frame in frames]
state.update_batch(updates)  # observes all; applies only fresh latest
```

```text
stale intermediates + fresh latest -> bounded atomic coalesce
stale latest / malformed batch     -> unchanged fail-closed path
```

## Scenario: React to a Moving Obstacle with a Policy-Controlled Robot

### 1. Scope / Trigger

Use this contract when a moving simulator body updates a SCAN-style occupancy
map and can invalidate the active B-spline while an articulated locomotion
policy lags or starts behind a replacement trajectory. It is a reactive
moving-occupancy contract, not velocity prediction or intention modeling.

### 2. Signatures

```yaml
grid_map.occupied_decay_updates: <complete cloud updates; 0 disables>
closed_loop_controller.max_tracking_error: <strict metres>
closed_loop_controller.replan_catchup_max_error: <fail-closed metres>
closed_loop_controller.replan_catchup_min_speed: <catch-up-only m/s>
```

```text
planning/go2_execution_frozen  # trajectory-time alignment only
planning/go2_catchup_active    # collision-replan backpressure only
```

```cpp
TrajectoryCatchupState classifyTrajectoryCatchup(
    double start_error, double strict_error, double maximum_catchup_error);
Eigen::Vector2d boundedCatchupVelocity(
    const Eigen::Vector2d &position_error, double gain,
    double minimum_speed, double maximum_speed);
bool shouldDeferCollisionReplan(bool catchup_active);
```

### 3. Contracts

- A dynamic body is one visible, collidable, terrain-seated prim tracked by
  every declared simulated sensor. A command-relative schedule may begin only
  after the first accepted nonzero robot command so simulator startup latency
  cannot decide the collision outcome.
- SCAN receives rendered point geometry only. Dynamic-body truth may classify
  sensor hits, compare scheduled/readback poses, compute synchronized
  clearance, and draw evidence; it may not inject or remove planner points,
  generate a trajectory, or steer the robot.
- Occupied-source freshness is disabled by default. When enabled, each
  occupied source voxel records the most recent complete cloud update that hit
  it. Expiry removes the source occupancy and its reference-counted inflation
  contribution only after the full configured age. Continuously observed
  static geometry refreshes its age.
- A replacement trajectory inside the strict tracking window starts normal
  B-spline execution. A larger mismatch up to the maximum enters bounded
  position-only catch-up with B-spline time frozen. A larger mismatch is
  rejected and stopped. A minimum catch-up speed may clear a measured policy
  deadband, but applies only in `CATCHUP` and remains below the unchanged
  policy maximum.
- `go2_execution_frozen` may freeze SCAN trajectory time for heading, tracking,
  or catch-up alignment. It must never suppress collision checking by itself.
  Only the separately published `go2_catchup_active` state may defer another
  optimizer call, and collision checking resumes immediately on `TRACKING` or
  `REJECTED`.
- Goal success for a locomotion policy requires a continuous in-tolerance
  stopped window. Later zero-command stance drift is recorded and bounded
  separately; shortening a run to hide drift is forbidden.
- Freeze thresholds only after two passing same-source/config dry runs. A
  post-candidate safety review can supersede an automated PASS; preserve it and
  requalify the changed code before naming another review candidate.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Freshness parameter is zero | Preserve legacy occupancy behavior |
| Occupied source is hit again | Refresh age; retain occupancy and inflation |
| Source exceeds full update age | Remove its occupancy and one paired inflation contribution |
| Replacement start error is within strict bound | Track normally; catch-up inactive |
| Start error is between strict and maximum bounds | Freeze B-spline time; command only toward the received start |
| Catch-up proportional command falls inside the measured policy deadband | Apply the frozen catch-up-only minimum norm |
| Start error exceeds maximum | Reject, publish zero command, keep collision checking active |
| Heading or ordinary tracking freezes execution time | Keep collision checking active |
| Catch-up is active | Defer only another collision optimizer call; continue pose/cloud callbacks |
| Dynamic body contacts a non-foot link or triggers reset | Preserve FAIL; do not retime or shrink the obstacle after the frozen run |
| Robot reaches and stops, then drifts | Report stable-arrival event and bounded later drift separately |

### 5. Good / Base / Bad Cases

- **Good:** command-relative collidable body, transform-tracked dual sensing,
  rendered-only planner input, default-off freshness, bounded catch-up with a
  dedicated backpressure state, live collision checks outside catch-up, two
  same-input dry runs, frozen candidate, local hash parity, and human review.
- **Base:** a static blocker can validate the geometric closed loop, but cannot
  support a moving-obstacle claim.
- **Bad:** animate a collision-disabled visual, classify truth bounds into the
  planner cloud, reuse a broad execution-frozen signal to suppress collision
  checks, widen normal tracking to absorb mismatch, or rerun a startup-timed
  crossing until one attempt happens not to collide.

### 6. Tests Required

- Unit-test wait/cross/hold/cross/park schedule boundaries, invalid dimensions,
  hold fraction, terrain seating, pose readback, and signed circle clearance.
- Unit-test occupied-age boundary behavior with disabled, unobserved,
  refreshed, exact-age, and expired sources; integration evidence must retain
  a static blocker after departed-body cells expire.
- Unit-test `TRACKING`, `CATCHUP`, and `REJECTED`; prove the minimum catch-up
  speed clears a small request, maximum speed still saturates, and zero error
  stays zero.
- Assert collision replanning defers for `CATCHUP` only, not tracking, heading
  alignment, ordinary time freeze, or rejected trajectory state.
- Run a physical dry run that actually exercises a large bounded mismatch and
  another same-input run through normal tracking before freezing.
- In the frozen run, assert command-relative trigger evidence, all motion
  phases, dual-sensor multi-pose detections, a causally later SCAN plan,
  positive synchronized clearance, zero non-foot collision, stable goal stop,
  bounded later drift, decoded raw/overlay videos, ROS bag integrity, and
  local/remote SHA-256 parity.

### 7. Wrong vs Correct

#### Wrong

```cpp
if (go2_execution_frozen)
  return;  // also hides collisions during heading and ordinary tracking freeze
```

```text
dynamic truth bounds -> synthetic planner points -> apparent replan
```

#### Correct

```cpp
if (go2_catchup_active)
  return;  // optimizer backpressure only during bounded start catch-up
// heading/tracking/rejected states still execute collision checking
```

```text
command-relative PhysX body -> transform-tracked sensor hits -> SCAN occupancy
  -> reactive B-spline -> bounded catch-up if needed -> articulated motion
  -> synchronized clearance/contact evidence
```

## Scenario: Replace a Dynamic Primitive with an Official Animated Human

### 1. Scope / Trigger

Use this contract when a previously qualified cylinder or box is replaced by a
ready-made vendor human asset while keeping the same reactive planner,
schedule, policy, robot, sensors, and physical-clearance claim. A recognizable
render alone is insufficient: the surfaces seen by planning must be
commensurate with the physical collision envelope.

### 2. Signatures

```python
def expand_isaac_env_regex_ns(prim_expr: str) -> str: ...
```

```text
visible asset: versioned official Isaac character URL under a visual-only root
animation: official Biped AnimationGraph retarget output, cached outside Direct GPU
physical proxy: one hidden capsule under a separate kinematic root
registration: common schedule time/XY/heading with explicit vertical datums
sensor contract: conservative co-moving capsule proxy
```

### 3. Contracts

- Pin the official asset URL and runtime version. Record source metadata,
  readable hashes, extension versions, license boundary, collision path, and
  animation identity. Never vendor or redistribute restricted vendor content.
- Keep the collision capsule hidden but collidable. Register its dedicated root
  and the visual root to the same schedule time, XY, and heading; compare the
  capsule-centre and shoe-sole vertical datums instead of equating root Z.
- Use the official Biped AnimationGraph and its ControlRig retarget output for
  visible gait. If Direct GPU cannot host the graph, generate a run-owned cache
  in a separate bounded Isaac process, validate exact joint order and non-static
  poses, and replay it without the graph. Do not implement a local procedural gait.
- The rendered body surface must be commensurate with the declared capsule at
  the sensor-facing planes. Compare early-route rendered hit counts and physical
  clearance against the primitive baseline. A sparse cosmetic body inside a
  broad collision capsule is a sensor/physics mismatch, not a planner failure.
- Normalize `{ENV_REGEX_NS}` to `/World/envs/env_.*` before comparing declared
  target expressions with Isaac's runtime target records.
- Human part identity, truth pose, capsule bounds, and gait angles are evidence
  only. SCAN receives rendered geometry; no semantic label, truth point,
  predicted velocity, or scripted avoidance command may enter planning.
- Preserve a collision-producing geometry run. Fix the owning representation
  layer, re-run a no-contact preflight and two same-input full dry runs, then
  freeze a new human-asset hash and acceptance file before a review candidate.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Official asset URL/version or readable hash differs | Stop or fail acceptance before promoting the run |
| Official character or animation fails to load | Fail the visual preflight |
| Capsule is visible, non-collidable, or registration error exceeds tolerance | Fail the physics gate |
| Cache joint order differs from the official character skeleton | Fail before scene startup |
| Walk or idle cache is static or contains invalid quaternions | Fail the visual preflight |
| A visible part lacks transform tracking in either sensor | Fail the sensor gate |
| Runtime target uses expanded environment regex | Normalize then compare exact expressions |
| Local procedural gait drives the visible human | Reject as out of scope |
| Visible surface is too sparse for its collision envelope | Preserve collision/clearance failure; enlarge or correct the rendered body |
| Human truth is used to add/remove planner points or steer | Reject the run as non-causal |
| Automated candidate passes but video is unreviewed | Keep task and manifest at human-review pending |

### 5. Good / Base / Bad Cases

- **Good:** versioned official animated human, hidden stable capsule, audited
  dual-sensor occupancy, comparable sensing/physics
  envelopes, positive clearance, frozen candidate, and pending human review.
- **Base:** the original cylinder remains a valid reactive-obstacle baseline but
  cannot satisfy human recognizability or gait evidence.
- **Bad:** draw a person around the old cylinder while sensors still target only
  the cylinder, or use a thin visible mannequin inside a broad capsule and
  blame SCAN after the robot contacts the unseen envelope.

### 6. Tests Required

- Unit-test official asset selection, phase-to-animation state, invalid phase,
  and environment-regex expansion.
- Assert the official asset/animation identity, one hidden collision prim,
  initialized synchronized roots, and no visible primitive fallback.
- Assert the declared official-mesh or proxy sensor targets are present in both
  runtime target lists and detected at multiple actor poses.
- Record early-route human hit counts, synchronized physical clearance, non-foot
  contact, causally later SCAN trajectories, goal stop, and overlay identity.
- Require a no-contact preflight, two same-effective-input full passes, one
  frozen run, local acceptance parity, ROS bag integrity, MP4 decode, and
  local/remote SHA-256 parity.

### 7. Wrong vs Correct

#### Wrong

```text
unverified downloaded model + broad hidden capsule
  -> sparse sensor returns -> late replan -> collision with unseen envelope
```

```python
expected = "{ENV_REGEX_NS}/DynamicObstacle/Visual/Head"
assert expected in runtime_targets  # Isaac has already expanded the token
```

#### Correct

```text
visible body commensurate with physical capsule
  -> transform-tracked rendered hits -> SCAN occupancy -> physical clearance
```

```python
expected = expand_isaac_env_regex_ns(
    "{ENV_REGEX_NS}/DynamicObstacle/Visual/Head"
)
assert expected in runtime_targets
```

## Scenario: Start Preset Navigation Only After Occupancy Is Ready

### 1. Scope / Trigger

Use this contract whenever SCAN preset-waypoint mode starts automatically from
simulated odometry and point-cloud streams. The first odometry callback may run
before the map has processed its first cloud; renderer or sensor workload can
change that ordering without changing any frozen experiment input.

### 2. Signatures

```cpp
bool GridMap::hasOccupancyObservation();
```

```cpp
if (navi_mode_ == NAVI_MODE::PRESET_TARGET && !preset_started_ &&
    planner_manager_->grid_map_->hasOccupancyObservation()) {
  preset_started_ = true;
  planGlobalTrajbyGivenWps();
}
```

### 3. Contracts

- `hasOccupancyObservation()` becomes true only after at least one processed
  occupancy update, not merely after cloud receipt, sensor pose, or odometry.
- Preset mode may record odometry and publish its robot envelope while waiting,
  but it must not create or publish a trajectory from an empty map.
- The readiness gate must not inject points, delay the dynamic actor schedule,
  alter planner/controller limits, or script robot motion.
- Log both the waiting state and the transition that starts preset planning so
  the launch order is auditable from the run evidence.
- After this race is fixed, preserve the collision-producing run and obtain a
  no-contact preflight plus two identical-input full passes before promotion.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| Odometry arrives before any processed occupancy update | Keep preset mode unstarted and command zero |
| First occupancy update completes | Start the preset target exactly once |
| A rendered-load change alters callback timing | Inputs and behavior remain valid; no empty-map plan |
| Readiness never arrives | Remain fail-closed and fail the bounded run |
| Frozen collision run already exists | Preserve it and document the causal readiness fix |

### 5. Good / Base / Bad Cases

- **Good:** odometry is live, one occupancy update completes, the preset plan
  starts once, and later dynamic occupancy causes safety replanning.
- **Base:** manual goal mode may remain human-triggered after map inspection;
  it does not prove automatic preset readiness.
- **Bad:** start from the first odometry callback and rely on thread timing or
  renderer speed to make a cloud win the race.

### 6. Tests Required

- Build and run the `plan_env` and `scan_planner` test suites after changing
  the readiness API or preset start condition.
- Runtime logs must contain the wait and start messages in order, one initial
  plan only after readiness, and a causally later safety replan when the moving
  obstacle invalidates that plan.
- Require positive physical clearance, zero non-foot collision, goal or safe
  stop, and two passing identical-effective-input full runs.

### 7. Wrong vs Correct

#### Wrong

```cpp
have_odom_ = true;
if (!preset_started_) planGlobalTrajbyGivenWps();
```

#### Correct

```cpp
have_odom_ = true;
if (!preset_started_ && grid_map->hasOccupancyObservation()) {
  preset_started_ = true;
  planGlobalTrajbyGivenWps();
}
```
