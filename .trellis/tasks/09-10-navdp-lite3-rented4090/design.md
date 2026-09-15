# Design boundary

The current local controller follows LightNav paths without independent obstacle
avoidance. The selected NavDP-family policy will replace trajectory generation;
the existing pinned Lite3 dynamics/walking export remains the locomotion reference.

Selected checkpoint: InternRobotics/X-NavDP at
7cee38a8d8308874d2b8488783c612f42060ac41, x-navdp_posttrain.ckpt,
SHA-256 267089a81bbbe7a913debda6603f3f1b66a79520370ce953b2d888d793b89f24.
Use the original quadruped embodiment index 2 as an explicitly unvalidated Lite3
transfer. Inputs are RGB uint8, metric optical-axis depth float32, local goal
[forward,left,0] in meters, world base position, and xyzw quaternion. Output is
24 local xyz trajectory points plus candidate trajectories and Q values.
Use the original X-NavDP acados MPC, including signed linear commands, at the
documented quadruped bounds (0.5 m/s and 0.5 rad/s).

First screen: clear 1 m and 2 m goals; two seeded 4 m goals behind a 0.7 m tall
box. Maximum 40 active wall seconds each plus 2 seconds stopping observation.
Arrival within 0.25 m triggers an explicitly external stop; contact or fall
ends the trial as failure. A 0.5-second command freshness watchdog provides
zero velocity while inference is delayed; count and report such interventions.

All new code and inputs live under a dated NavDP experiment directory. Acquire
the pristine NavDP repository at its surveyed commit. Inspect the selected
variant before adapting its input/output contract. Preserve upstream inference
math, preprocessing, and candidate selection. Use an isolated runtime outside
LightNav paths so cleanup cannot break the new trial.

Reuse only identified robot/assets/controller utilities from the local Lite3
experiment, with source hashes and attribution. Render metric depth using MuJoCo;
record RGB/depth, capture pose, returned trajectory, command, contacts and actual
motion. Point-goal termination is controller/evaluator behavior, not language or
native learned STOP. A local-only first screen is not an official Isaac benchmark.

Cleanup uses an explicit path inventory and checks for running task processes.
Keep provenance, configuration, raw records, metrics and videos by default;
checkpoint/runtime deletion must not use broad wildcard repository deletion.
