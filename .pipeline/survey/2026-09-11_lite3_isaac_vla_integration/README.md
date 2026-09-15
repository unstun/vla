---
origin: ai+subagent_survey, lead-verified in part
date: 2026-09-11
label: surveyed
scope: what exists for driving a Lite3 in Isaac Sim from InternVLA-N1
---

# Lite3 in Isaac Sim, driven by a VLA: what exists and what is missing

Purpose: Dr Sun chose (2026-09-11) to close the simulation gap while the robot is unavailable, specifically a Lite3 body in
Isaac Sim executing InternVLA-N1's output. This records what the sibling repositories already provide, so a task plans an
integration instead of rebuilding.

Sources: `/Users/sun/tongbu/study/phdproject/machine-dog` and `/Users/sun/tongbu/study/phdproject/machine-dog-nav`, both
READ-ONLY references for VLA work (AGENTS.md). Body of findings from an Explore subagent; the five claims the plan rests on
were re-read by the lead and are marked **[lead-verified]**. Everything else is **[subagent, unverified]** and must be
re-checked before it is relied on.

## The interface matches, and that is the main finding

**[lead-verified]** The Lite3 locomotion policy takes a 3-vector body-frame velocity command, not a waypoint:
`machine-dog/2_experiment/baseline_rebuild/go2_rl_robotlab_lite3_v17a77/source/robot_lab/robot_lab/tasks/go2/mdp/commands.py:58`

    self.commands = torch.zeros(self.num_envs, 3, dtype=torch.float, device=self.device)  # [lin_vel_x, lin_vel_y, ang_vel_yaw]

and it enters the actor observation as the `velocity_commands` ObsTerm in
`.../tasks/lite3/env_cfg.py:219`.

**[lead-verified]** InternVLA-N1's own non-Habitat agent emits exactly that form. In the pinned upstream,
`references/upstream/2026-09-08_dualvln/source/InternNav/internnav/agent/internvla_n1_agent_realworld.py`:

    def trajectory_tovw(self, trajectory, kp=1.0):
        subgoal = trajectory[-1]
        linear_vel, angular_vel = kp * np.linalg.norm(subgoal[:2]), kp * subgoal[2]
        linear_vel  = np.clip(linear_vel, 0, 0.5)
        angular_vel = np.clip(angular_vel, -0.5, 0.5)

So System 1 produces a trajectory, upstream already reduces it to (v, omega), and the locomotion policy consumes (vx, vy, wz).
The VLA-to-locomotion contract needs adapting, not inventing. Note the Habitat action space (discrete 0.25 m steps, 15 deg
turns) is a Habitat artifact and is NOT what the model natively produces.

## What already works

**[subagent, unverified]** A Lite3 has walked in Isaac Sim under navigation control. The best recorded run,
`machine-dog-nav/.pipeline/experiments/2026-09-11_pct_scan_upstream_baseline/`, reports `native_full02`: 98.08 s,
74.063 m travelled, final XY error 3.77 cm, goal reached and stopped, zero non-foot contact, zero watchdog events, through a
multi-floor building with stairs. Earlier: `2026-08-13_scan_foxy_isaac_closed_loop` passed 71 frozen acceptance checks on a
flat course.

**[subagent, unverified]** The stack: Isaac Sim 5.1.0 (image digest `sha256:f3563cb2...`), Isaac Lab 2.3.2.post1,
PyTorch 2.7.0+cu128, Python 3.11 on the sim side; ROS 2 Foxy / Python 3.8 in a Podman container on the planner side; a
bespoke localhost TCP protocol between them, NOT the NVIDIA ROS bridge.

**[subagent, unverified]** `machine-dog-nav/integration/lite3_sim_bridge/` is a real ament_python package with a framed TCP
protocol (`CMD_VEL_V1` in, sensor/status frames out), a 250 ms command watchdog, per-axis and horizontal-norm clamps, contact
guards, and pinned checkpoint/policy SHA gates that fail closed. The Isaac side is
`run_isaac_v12_fallback.py`, which writes the command straight into `command_term.commands[:, 0:3]`.

**[subagent, unverified]** Robot model: `LITE3_CFG_V12` / `LITE3_CFG_V17` in
`machine-dog/.../robot_lab/assets/deeprobotics.py`, spawned URDF-to-USD at runtime from
`resources/lite3/urdf/lite3.urdf`. An official Lite3 USD is vendored but is not on the training/inference path.
`artifacts/elmap_isaaclab_asset` is a Unitree Go1 backpack and is irrelevant.

**[subagent, unverified]** Policy: **V12 `model_149999`** is the only one qualified for navigation; it is what every
successful run uses. The V17 line is not navigation-ready: V17.74 drifts +4.31 m laterally and +36.2 deg in heading over
12.5 m of straight commanded walking, and a V17 E3 candidate was explicitly rejected by the closed loop's command-response
gate.

## The gap that decides the schedule: no robot-mounted RGB

**[lead-verified]** The accepted Isaac adapter has no colour camera on the robot. The only scene camera is
`run_isaac_v12_fallback.py:2259`, `env_cfg.scene.navigation_depth_camera = MultiMeshRayCasterCameraCfg(...)` — a ray-cast
DEPTH camera, which cannot produce colour. Every RGB path in that file is `raw_env.render()` with
`render_mode="rgb_array"`, a third-person chase view used only for MP4 recording (line 3454 labels it
`"render_modality": "simulated_rgb_from_preserved_chase_pose"`).

InternVLA-N1 needs robot-mounted RGB. For the fused camera it needs two: head 1280x720 and D435i colour+aligned depth.
That means adding an RTX-rendered `CameraCfg`/`TiledCameraCfg` at the measured mounts and turning on camera rendering
(`AppLauncher(enable_cameras=True)`), which the current adapter deliberately leaves off. This changes the performance
profile of the whole loop and is the main technical risk, not the locomotion.

## Other gaps

1. **No furnished interior with validated collision that a Lite3 has walked in.** The Building mesh is bare architecture;
   NVIDIA Office has a floors-only collision wrapper, no locomotion evidence, and would not render a first frame at full
   materials on a 5070 Ti. This matters more than it looks: a VLN instruction such as "stop near the high-backed chairs
   between the windows" needs semantic landmarks, so scene choice gates the language evaluation, not just the walking.
2. **No VLA-to-Isaac command path.** A `tic-vla-lite3.body-command.v1` UDP schema (vx/vy/wz) exists in the HARDWARE deploy
   tree only; nothing wires it to `CMD_VEL_V1`. Small, but absent.
3. **Command lag.** The actor observation carries a 10-frame command history at 50 Hz, so a new command is fully represented
   only after 10 steps (0.2 s). A control-rate constraint for the VLA. **[subagent, unverified]**
4. **Pose is simulator truth** in every recorded run. No LIO, no drift. Acceptable for a first loop; not a localisation result.
5. **Repeatability is unestablished** — headline results are single-seed, single-run, and two runs on identical frozen inputs
   once disagreed. **[subagent, unverified]**

## Provenance problem for importing

**[lead-verified]** The V12 checkpoint is NOT in git: `git check-ignore -v` returns
`references/locomotion/.gitignore:1:**/source/` for
`references/locomotion/2026-08-13_v12_model149999/source/checkpoint/model_149999.pt` (26,367,345 bytes). Pinning a commit
does not reproduce the weights; they must be vendored by SHA-256.

**[subagent, unverified]** Both repositories are dirty (machine-dog ~1,074 entries, machine-dog-nav ~585) and
machine-dog-nav's HEAD is on branch `codex/scan-foxy-isaac`, not main, with the Isaac evidence on that branch. A VLA import
needs either a clean commit in those repos first, or file-level vendoring by hash. Per AGENTS.md this VLA task must not edit
either repository.

## Remote

**[lead-verified]** A headless Isaac Sim is running now on the rented 4090: `/isaac-sim/runheadless.sh` with
`isaacsim.exp.full.streaming.kit`, root `/home/ubuntu/docker/isaac-sim`. **[subagent, unverified]** Neither repository
documents that path or that kit file; `machine-dog/artifacts/2026-09-05_e01_rented4090_environment/` documents a rented 4090
whose pre-existing `isaac-sim` container was preserved, which is a plausible but unconfirmed match. Identity must be
established before anything is run there, and the container must not be disturbed.
