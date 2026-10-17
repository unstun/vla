---
origin: ai+web
reviewed: false
date: 2026-09-26
---

# Isaac Lab and macOS policy evaluation

Read-only web/source survey requested by Dr Sun after the stair experiment was
archived at server shutdown. Label: surveyed. No source snapshot imported,
package installed, checkpoint converted or simulator executed. Main-session
research follows the active inline instruction; no search subagent was used.

## Findings

1. [IsaacLab-MLX](https://github.com/RobotFlow-Labs/IsaacLab-mlx) is a community
   Apple Silicon fork with MLX and a narrow `mac-sim` backend. Its current README
   documents cartpole, cart-double-pendulum and quadcopter task slices, checkpoint
   save/load and replay scripts. It explicitly excludes full Isaac Sim, RTX
   sensors/camera pipelines and full task coverage. General articulation and
   locomotion support remain roadmap items. This is a candidate for supported
   demonstrations, not evidence that our Lite3 checkpoint or stair task runs.
   The documented MLX cartpole checkpoint is `.npz`; compatibility with our
   existing policy has not been established. A direct web fetch of the linked
   play script returned a cache miss; no code-level or runtime claim follows.
2. [mjlab](https://github.com/mujocolab/mjlab) combines Isaac Lab's manager API
   style with MuJoCo Warp. Its [installation guide](https://mujocolab.github.io/mjlab/main/source/installation.html)
   explicitly includes macOS evaluation. The [versioned FAQ](https://mujocolab.github.io/mjlab/v1.6.0/source/faq.html)
   says macOS uses CPU execution, evaluation works with lower performance, and
   training is not recommended there. It is a separate framework, not an
   official Isaac Lab macOS binary. Robot, observations, action ordering,
   control periods, contact and terrain still require an explicit port.
3. Official [Isaac Lab quickstart](https://isaac-sim.github.io/IsaacLab/develop/source/setup/quickstart.html)
   now offers Newton/MJWarp without the full Isaac Sim application. However,
   the current [official tutorial](https://isaac-sim.github.io/IsaacLab/develop/source/setup/tutorial.html)
   still requires an NVIDIA GPU for that workflow. The [installation guide](https://isaac-sim.github.io/IsaacLab/develop/source/setup/installation/index.html)
   specifies Linux/Windows and NVIDIA requirements for full Isaac Sim use.
   Kit-less by itself is not evidence of supported Apple Silicon execution.

## Relevance to this repository

The already present source
`../experiments/2026-09-10_x_navdp_lite3_rented4090/lib/robots/lite3.py`
loads a pinned V12 ONNX policy through `CPUExecutionProvider`, checks its
float32 `[1,450] -> [1,12]` interface and uses real MuJoCo stepping/contact data.
This local source inspection demonstrates that the policy inference code path
is already separate from Isaac Sim. It does not establish that all assets and
dependencies are ready on this Mac or that the current stair/RTX scenario is
portable without changes.

Assessment: for a Mac policy-plus-physics pilot, first validate the existing
MuJoCo/ONNX adapter or mjlab's documented CPU evaluation path. IsaacLab-MLX is
worth evaluating for its supported tasks, but its documented current scope
does not justify choosing it as a drop-in Lite3 stair simulator. Preserve the
existing Isaac RTX/official animated-human experiment as a separate condition.

The current machine was independently inspected earlier in this session as
Apple M5/32GB/Darwin arm64. Neither inspected interpreter contained MuJoCo.
Performance, policy parity and a complete Mac stair run remain untested.

## Second search: stronger native CPU and deployment leads

Dr Sun requested a wider search. The following adds evidence beyond the initial
MLX/mjlab summary; no installation or runtime claim is added.

- **Newton's official project supports macOS CPU.** The current
  [upstream README](https://github.com/newton-physics/newton#requirements)
  explicitly lists macOS as CPU-only and documents `--device cpu` for examples.
  Its [robot policy example source](https://raw.githubusercontent.com/newton-physics/newton/main/newton/examples/robot/example_robot_policy.py)
  runs ONNX policies pretrained in Isaac Lab, with Go2, ANYmal and G1 entries.
  It performs observation construction, joint-order mapping, inference,
  position-target application and actual solver stepping; it is not just a
  playback of recorded poses. The inspected example requires an observation
  width of `12 + 3*num_dofs` (48 for12DOF), so our450-input Lite3 policy cannot
  simply replace the policy file. It uses Warp-NN, and its current solver setup
  sets `use_mujoco_cpu` from a false member. General macOS support and CPU-aware
  graph code do not prove that this exact example/dependency set runs unchanged
  on our Mac. Treat it as a concrete first runtime qualification candidate.
- **Isaac Lab itself still has an installation boundary.** The authoritative
  [v3.0.0-EA commit ae37b02](https://github.com/isaac-sim/IsaacLab/commit/ae37b02)
  explicitly records that `uv run isaaclab -f` and the isolated documentation
  build cannot resolve on macOS arm64 because the lockfile supports Linux and
  Windows. Thus Newton's Mac support must not be promoted to an official Mac
  installation of the whole Isaac Lab stack. The
  [official Newton backend API](https://isaac-sim.github.io/IsaacLab/develop/source/api/lab_newton/isaaclab_newton.physics.html)
  includes `use_mujoco_cpu`; the
  [release solver guide](https://isaac-sim.github.io/IsaacLab/release/3.0.0/source/concepts/solver-tuning/tune_mjwarp.html)
  describes it as a diagnostic facility. This is a possible engineering route,
  not a ready supported Apple Silicon release.
- **rl_sar is an explicit Mac sim-to-sim candidate.** Its
  [upstream README](https://github.com/fan-ziqi/rl_sar)
  lists experimental macOS support for MuJoCo, libtorch and ONNX Runtime, and a
  CMake/MuJoCo build path without ROS. Go2/Go2W/B2/B2W have MuJoCo support in the
  robot matrix. Critically, Deeprobotics Lite3 is marked *not supported in
  MuJoCo* there; its Gazebo/real entries do not establish a Mac Lite3 path.
  This is a deployment adapter for trained policies, not Isaac Lab on macOS.
- **UniLab adds an Apple Silicon evaluation lead.** Its own
  [Chinese README](https://github.com/unilabsim/UniLab/blob/main/README_zh.md)
  documents Apple Silicon setup, `eval` for `go2_joystick_flat` with Motrix,
  and macOS interactive replay via `mxpython`. It uses separate MuJoCoUni/Motrix
  backends. The Mac task claims have not been independently run or source-audited
  here; treat them as documented functionality, not validated compatibility.
- **IsaacSim-mlx is not an available implementation.** Despite its listing in
  the organization overview, the [repository itself](https://github.com/RobotFlow-Labs/IsaacSim-mlx)
  is empty at this check. Exclude it from runnable candidates.

Updated assessment: to investigate the closest upstream route to running an
Isaac Lab-trained policy on this Mac, first qualify the official Newton Go2
example under a small CPU run. Keep mjlab and our existing MuJoCo/ONNX adapter
as practical alternatives. No checked source establishes an unchanged Lite3
stair/RTX/official-human run on macOS. Whole-stack adoption remains undecided.
