---
origin: ai_only
reviewed: false
---

# Navigation VLA Localization Patterns

## Question

How do representative navigation VLA systems obtain robot localization, and
does the Lite3 TIC-VLA integration require Fast-LIVO2 specifically?

## Source-backed findings

### TIC-VLA

- The paper describes an egocentric navigation policy that consumes RGB
  history, language, robot velocity, reasoning latency, and short-horizon
  ego-motion. It does not require a privileged global goal or a global map.
- The pinned official simulation behavior reads world pose, linear velocity,
  and angular velocity from the Isaac Sim robot interface.
- It computes the displacement since the reasoning-generation reference pose,
  then rotates that world-frame displacement into the body frame defined by
  the reference quaternion before passing `dx, dy` to the model.
- Figure 6 of the paper explicitly shows the real Unitree Go2 equipped with a
  depth camera, RGB camera, LiDAR, and an onboard Jetson Orin NX. The released
  repository does not include the Go2 real-robot transport, localization, or
  control adapter, and the paper does not name the LiDAR odometry/SLAM
  algorithm. Therefore, the public evidence establishes that LiDAR was present
  on the authors' platform, but not which estimator produced the model's
  ego-motion state or whether a map was consumed by TIC-VLA itself.

Primary sources:

- Paper: https://arxiv.org/html/2602.02459
- Pinned official behavior:
  `references/upstream/2026-08-20_tic_vla/source/TIC-VLA/DynaNav/behavior/spot_test_ticvla.py`
- Pinned official model:
  `references/upstream/2026-08-20_tic_vla/source/TIC-VLA/DynaNav/ticvla.py`

### OmniVLA

- The official pose-goal inference example reads GPS latitude/longitude and
  compass heading, converts them to a robot-relative goal, and passes that
  relative goal to the policy.
- Other supported goal modalities, such as language or goal images, do not
  inherently require GPS input to the VLA model.

Primary source:

- https://github.com/NHirose/OmniVLA/blob/main/inference/run_omnivla.py

### LM-Nav

- LM-Nav localizes visually against a previously collected topological image
  graph and follows visual subgoals rather than requiring a dense metric map.
- Its real-world graph collection uses images and GPS measurements; this is a
  different localization architecture from continuous LiDAR SLAM.

Primary source:

- https://proceedings.mlr.press/v205/shah23a.html

## Lite3 implication

Fast-LIVO2 is one possible provider of the TIC-VLA motion state, not a model
dependency. A replacement is acceptable if it provides timely, correctly
framed body velocity, yaw rate, position, and orientation sufficient to
compute reasoning-relative body-frame `dx, dy`.

Running a SLAM/odometry stack in parallel is consistent with the authors'
LiDAR-equipped hardware arrangement. The architectural boundary should remain
explicit: the estimator publishes ego-motion, while TIC-VLA consumes that
state without owning the mapper or requiring its map output.

The current Lite3 bridge transmits the Fast-LIVO2 quaternion, but
`live_bridge.py` discards it when constructing `RobotStateSample`, and
`shadow_service.py` subtracts world-frame `x, y` without the official
reference-orientation rotation. This is an implementation mismatch to fix and
test before active robot evaluation. It is not evidence that Fast-LIVO2 itself
is necessary or that it caused the observed model behavior.

## Claim boundary

These systems were inspected as localization/interface examples. This note
does not claim that any alternative state estimator has been integrated or
validated on Lite3.
