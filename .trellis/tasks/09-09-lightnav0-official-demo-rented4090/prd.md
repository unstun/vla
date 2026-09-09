# LightNav-0 official demo reproduction

Dr Sun selected LightNav-0 and requested the official case on the rented server
on 2026-09-09. Preserve the established manual Opus execution workflow. This
authorizes isolated setup and bounded pretrained simulation, not training or
real-robot actuation.

The selected case is the upstream MuJoCo demo, bundled ProcTHOR `val_2` ceiling
scene, default TurtleBot and default English instruction. Preserve model,
scene, camera, client, MPC and native stopping behavior. Report repeated fixed
case outcomes, including failures, and verified local first-/third-person video.

Acceptance requires pinned source/model/assets, actual GPU inference and
simulated closed-loop records, explicit stop provenance, recorded resource and
timing measurements, and complete hash-verified local artifacts. A launched
server, finite offline prediction, or video without model/control records is
partial evidence. The kinematic TurtleBot demo cannot validate quadruped
locomotion, physical collision avoidance, or full published benchmark scores.

The execution contract is
`.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/OPUS_EXECUTION_PACKAGE.md`.
Current status: package prepared, not dispatched; no inference performed.
