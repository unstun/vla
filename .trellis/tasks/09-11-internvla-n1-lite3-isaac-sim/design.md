# Design: InternVLA-N1 driving a Lite3 in Isaac Sim

## The loop

    instruction (text, fixed per episode)
        |
    InternVLA-N1  <-- RGB (rendered, robot-mounted) + depth + pose + intrinsics
        |  System 2 (Qwen2.5-VL) -> pixel goal / text arrow
        |  System 1 (nextdit_async) -> trajectory in the robot frame
        v
    trajectory_tovw()  ->  (v, omega), clipped 0.5 m/s and 0.5 rad/s upstream
        |
    bridge clamp + 250 ms watchdog  ->  CMD_VEL_V1  ->  (vx, vy, wz)
        v
    command_term.commands[:, 0:3]  ->  V12 actor (450-dim obs) -> 12 joint targets @ 50 Hz
        v
    PhysX  ->  body state, contacts  ->  back up as pose, and RGB re-rendered

Only the two middle boxes are new. The bottom half exists and has walked 74 m; the top half exists and has run 45 times.

## Decision 1: drop ROS 2 Foxy

The Foxy container exists to host the SCAN planner. InternVLA-N1 replaces the planner, so nothing in the loop needs ROS.
The bridge's wire protocol (`protocol.py`, `command_state.py`) is pure standard-library Python and usable without ROS.

Chosen: a non-ROS Python client in THIS repository that speaks `CMD_VEL_V1` to the existing Isaac adapter. This keeps the
clamp, the 250 ms watchdog, the contact guard and the fail-closed checkpoint gate — the parts that make the loop safe and
auditable — while removing an entire Ubuntu 20.04 container, a Python 3.8 constraint and a ROS domain from the stack.

Rejected: driving `command_term.commands` in-process from the VLA process. It would be fewer moving parts but discards the
safety and evidence layer, and it forces Isaac Sim's Python 3.11 and pinned torch into the same interpreter as the VLA.

## Decision 2: how rendered images reach the VLA

The telemetry protocol carries point clouds, body state and status. It has no image message, and the accepted adapter has no
robot-mounted colour camera at all: the only on-robot sensor is `MultiMeshRayCasterCameraCfg` (ray-cast depth, no colour),
and every RGB path is `raw_env.render()` from a third-person chase pose used for video.

Chosen: add an `IMAGE_FRAME_V1` message to a COPY of the protocol owned by this task, carrying a frame id, simulation time,
camera name, width, height, pixel format and raw bytes, alongside the existing body state. At 640x480x3 and a VLA decision
rate of a few hertz this is under 3 MB/s over loopback. Two processes, so the VLA keeps its own Python environment and the
Isaac side keeps Isaac Lab's.

Consequence: the Isaac adapter must launch with `enable_cameras=True`, which every accepted run so far has set to False.
That is the cost measured in AC4 and it is the go/no-go for the whole task.

## Decision 3: which camera geometry, and when

Two configurations, staged:

1. **Single evaluation camera** for Milestones A-C: one RTX camera at the head pose, 640x480, HFOV 79, the geometry the
   Habitat conditions used. Fewest moving parts; isolates "does the VLA drive a walking robot" from "does the fusion hold up".
2. **The real two-mount configuration** afterwards: head 1280x720 HFOV 105 at +16.7 deg, D435i 1280x720 HFOV 69 colour plus
   aligned depth at 20 deg down, fused by the existing `fused_camera.py` into the virtual evaluation camera. That module is
   already validated and is byte-identical across the c7, c8 and c9 Habitat conditions, so it can be reused unmodified.

AC4 measures the render cost of BOTH, because configuration 2 is three rendered streams at 720p instead of one at 480p and
may not be affordable even if configuration 1 is.

## Decision 4: control rate, and why the command lag stops mattering

The policy runs at 50 Hz; the actor observation carries a 10-frame command history, so a new command is fully represented
after 0.2 s. System 2 is a 2B-class VLM and System 1 a diffusion sampler: a VLA decision costs hundreds of milliseconds, so
the loop runs at roughly 2-5 Hz with the velocity held between updates. The lag is then a fraction of one decision period
rather than a control problem. This must be measured, not assumed, and it is what AC7 checks.

## Decision 5 (Dr Sun, 2026-09-14): latency-faithful lockstep with 10 Hz control ticks

Phase B measured the simulator at RTF 0.17 while it shares the GPU with the VLA, and a VLA decision at 0.3-2.5 s. If the
simulator ran freely, the VLA would look about six times faster relative to the robot than on real hardware. So the
simulator runs only when the client asks it to:

- Each request carries one `CMD_VEL_V1` and advances simulated time by one 0.1 s control tick (5 policy steps). An image
  is returned only when the client asks for one.
- While the VLA is thinking, the simulator is paused. Afterwards the client plays the previous plan's controller for
  exactly the measured inference time, rounded to ticks and never less than upstream's 0.3 s planning period. Only then
  does the new plan take effect, which is when a real robot would have received it.
- Commands reach the policy through the bridge's `LatestCommandState` clamp and watchdog, driven by the simulated clock.
  Commands arriving every 100 ms simulated keep the 250 ms watchdog meaningful: it trips only if the client stops
  commanding.
- Every latency is logged, so an episode can be replayed with fixed-period timing.

## Decision 6 (Dr Sun, 2026-09-14): upstream's real-robot controllers, not `trajectory_tovw`

Upstream's quadruped deployment (`scripts/realworld/http_internvla_client.py`, a Unitree Go2 node) never calls
`trajectory_tovw`. Its planning thread does two things with each answer:
- A trajectory is transformed into the world frame with odometry from the image timestamp, skipping the first three
  points, and fed to a CasADi MPC (`controllers.py`: N=20, T=0.1 s, v_max 0.4, w_max 0.4, desired_v 0.3).
- Arrow actions move an incremental goal (0.25 m forward, ±15° turns) that a PD controller tracks.

Its control thread runs whichever controller is active at 10 Hz and publishes `(v, 0, w)`. The Phase C client
reproduces those two threads on the lockstep clock, with the pinned `controllers.py` unmodified. CasADi 3.7.2 is
installed with `pip --target` into this task's run root, never into another task's environment
(`setup/phase_c_pydeps.json`). Odometry is simulator truth from `BODY_STATE_V2`.

`trajectory_tovw` is evaluated and logged, but it cannot produce a value. The shipped real-world agent returns a
(T+1, 2) trajectory of x, y points (`vln_utils.traj_to_actions`), and `trajectory_tovw` reads `subgoal[2]`, so it
raises IndexError. That confirms it is dead code upstream, not a comparison baseline.

Timing, taken from `planning_thread`: measured from each image capture, a response is applied after the inference
latency L, and the next image is captured max(L + 0.05, 0.3) s later. Both round up to the 0.1 s tick grid, so a plan
is never applied early.

Two deviations are forced by the simulator and logged:
- Before the first plan the robot holds (0, 0); upstream publishes nothing.
- A failed MPC solve sends (0, 0) for that tick; upstream's control thread would die, and the robot's own command
  timeout would stop it.

## Decision 7 (Dr Sun, 2026-09-14): Phase C scene is the flat course plus coloured landmarks

Phase C adds two or three coloured primitive boxes to the Phase A/B flat course, so an instruction can name a visible
target and success is a measured distance. The furnished interior remains Phase D.

## Decision 8 (Dr Sun, 2026-09-14): measure first, then Nav2 `collision_monitor` for the body margin

Phase C's green episode put the hip into a box corner while the MPC tracked a point robot. The survey
(`.pipeline/survey/2026-09-14_body_clearance_margin_upstream_survey.md`) found no single repository that both sees
flank obstacles and enforces a footprint. Dr Sun chose this order:

1. **Measure before adding anything.**
   - Ground-truth footprint clearance for the six Phase C runs, computed offline from logged base poses and the pinned
     URDF footprint.
   - A comparison of following the upstream mean of 32 System 1 samples against following a single sample, so that
     planner averaging and missing body geometry are not confused.
2. **Then Nav2 `nav2_collision_monitor`, unmodified** (Apache-2.0, pinned `f31c7f49bf7afb9e32f4651ef91fb46f5636c88c`).
   - It runs in a ROS 2 Humble or Jazzy sidecar, between the MPC's (v, w) and the bridge.
   - Footprint polygon: the URDF footprint plus padding.
   - Source: a simulated 360° point cloud modelled on the real robot's MID-360. The head camera alone cannot see the
     flank.

Update (Dr Sun, 2026-09-14, PRD decision 7): D.0b, the single-sample against 32-sample-mean comparison, is dropped.
The model is not being fixed, so the margin must hold for any trajectory, averaged or not.

Consequences:
- Design Decision 1 (no ROS in the loop) is relaxed for this safety sidecar only. The lockstep must drive ROS time
  (`/clock`), and the monitor's stale-source behaviour must be shown to stop the robot.
- The real robot's Foxy baseline does not ship this package; deploying it on hardware is a separate question.
- Our code is limited to transport (clock, odometry, point cloud, command in and out) and configuration. The safety
  logic stays upstream's.

## Data contracts

| Field | Source | Note |
| --- | --- | --- |
| `rgb` | new RTX camera, robot-mounted | uint8 HxWx3; the model's only visual input |
| `depth` | existing ray-cast depth camera, or the D435i camera in configuration 2 | the shipped System 1 ignores it, but the agent signature takes it |
| `pose` | `BodyStateV2` position + orientation | simulator truth; no LIO, no drift |
| `intrinsic` | authored with the camera | we choose it, so it is exact |
| `instruction` | episode definition | fixed per episode |
| command out | upstream MPC (trajectory) or PD (arrow actions) at 10 Hz, per Decision 6 | (v, omega) -> (vx, vy=0, wz); vy stays 0, matching the hardware command schema; `trajectory_tovw` logged only |

## Pinning and provenance

- `machine-dog`: pin a clean commit for `robot_lab` and the Lite3 `ArticulationCfg` plus the URDF and meshes.
- `machine-dog-nav`: pin a clean commit for `integration/lite3_sim_bridge`.
- V12 `model_149999.pt` is gitignored upstream, so vendor the file with SHA-256 `a9d31dce...3d5450` recorded in this task's
  provenance and verified on both machines before every run.
- Both repositories are dirty today and the nav Isaac evidence is on a feature branch. Resolving the pin is the first step of
  Milestone A, and blocks it.

## Rollout and rollback

Each milestone is additive and lives entirely in this repository: a vendored import, a camera configuration, a protocol
copy, a client. Nothing modifies `machine-dog` or `machine-dog-nav`. Rollback at any point is deleting this task's
directory tree; the sibling repositories and the running Isaac container are never written to.

## Risks

1. **Render cost** is the schedule risk. If RTX cameras plus the VLA do not fit on one GPU, the fallbacks are lower
   resolution, a lower render rate, decoupling render from physics rate, or two GPUs.
2. **The Isaac container on the rented 4090 is unowned**, as far as either repository documents. Do not disturb it; establish
   identity first.
3. **The V12 policy is the only navigation-qualified one**, and its evidence is single-seed. Two runs on identical frozen
   inputs once disagreed, so repeatability is unestablished and must not be assumed.
4. **Furnished scenes are unproven**: the walkable building is bare, the furnished candidates have incomplete collision and a
   recorded performance wall. Language instructions need objects, so this gates Milestone D.
5. **Environment conflict** between the Isaac Python and the VLA Python is avoided by the two-process split. Checked
   statically 2026-09-11 and the risk is largely retired: `internvla_n1_agent_realworld.py` contains zero habitat
   references, and neither of its two internal imports (`internvla_n1.py`, `vln_utils.py`) does either. Its whole dependency
   surface is numpy, torch, transformers, diffusers and PIL. So the VLA side needs an ordinary ML environment, not the
   habitat-lab 0.2.4 stack the ablation required. A live import in a real environment still has to confirm it.
