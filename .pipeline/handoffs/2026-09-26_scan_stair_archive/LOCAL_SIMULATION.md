---
origin: ai+web
reviewed: false
date: 2026-09-26
---

# Local simulation capability check

The user asked whether simulation can run locally while gpu5070ti is powered
off. This is a capability assessment, not authorization inferred for a new
simulator migration. No installation or physics run was performed.

- `uname -sm`: Darwin arm64. `system_profiler SPHardwareDataType` returned
  MacBook Pro, Apple M5, 32 GB. Direct `sysctl` hardware access was denied;
  the system-profiler summary supplied the observed hardware identity.
- The current interpreter `/Users/sun/.openviking-venv/bin/python3` has NumPy
  and SciPy, but no `mujoco`, `pybullet`, `isaacsim`, `isaaclab` or `pxr` module.
- The project interpreter in
  `2026-09-08_tic_vla_dynanav_5070ti/demo/.venv/bin/python` has no `mujoco`,
  `torch` or `rclpy`. These two checks do not inventory every environment on
  the Mac and must not be phrased as proof of no installation anywhere.
- scan33's 15 native C++ target/FSM cases ran on this Mac. They use explicit
  manager, reference route and ROS doubles. They are not a complete planner
  replay or robot physics simulation.
- Existing VLA source at
  `../../experiments/2026-09-10_x_navdp_lite3_rented4090/lib/robots/lite3.py`
  uses real MuJoCo physics (`mj_step` and contact force reads). It is an
  existing adaptation starting point; its prior remote trials do not prove
  local availability or compatibility with the current SCAN stair stack.

The [official MuJoCo repository](https://github.com/google-deepmind/mujoco#installation)
provides macOS universal binaries. The [Python viewer documentation](https://mujoco.readthedocs.io/en/stable/python.html#passive-viewer)
requires `mjpython` for the passive viewer on macOS. This supports using MuJoCo
for a deliberately adapted local Lite3 physics trial; runtime performance and
scene/policy/sensor parity must still be tested.

The [Isaac Sim 5.1 requirements](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html)
list Linux/Windows with NVIDIA RTX hardware, and limit the aarch64 build to
DGX Spark. This Apple Silicon Mac cannot run the current Isaac 5.1 RTX LiDAR
and official animated-human pipeline as-is. Replacing its renderer, physics or
sensor model creates a separate test condition; it cannot stand in for the
existing scenario's acceptance evidence.

Recommended order if local work is requested: continue native algorithm tests;
prepare a complete recorded-input planner harness if feasible; then reuse the
existing MuJoCo Lite3 adapter in an isolated VLA-local environment and validate
scene, policy and sensor interfaces. Preserve original Isaac acceptance for
the server. This is a proposal, not a completed setup.
