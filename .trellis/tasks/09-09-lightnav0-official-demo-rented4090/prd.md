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

Round 1 executed three official-case episodes and requires corrections; runtime
execution and correct target arrival remain separate outcomes.

Dr Sun requested a researched continuation package with better visualization.
The current manual execution contract is
`.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/continuation_v3/EXECUTION_PACKAGE.md`.
It requires three fixed vLLM BF16 repetitions, complete native captures and
frame-associated state, offline overhead replay, synchronized multi-view MP4s,
explicit stopping/arrival measurements, and local hash-verified return. Static
preparation probes do not count as new navigation. The v3 package is prepared,
not dispatched; earlier packages and raw results remain preserved.
