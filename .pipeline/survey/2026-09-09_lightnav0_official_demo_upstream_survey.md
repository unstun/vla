---
origin: official_upstream+local_inspection
reviewed: false
date: 2026-09-09
---

# LightNav-0 official-demo selection

User-selected source: https://github.com/lightorigins/LightNav-0, pinned at
`d83fbfb9748ca6b497a2f2a7f4a3e95e2110e40c`. Model release:
https://huggingface.co/LightOriginsHQ/LightNav-0/tree/826dc5fbfa37afa8293d2e336d329b6ffc0bfb64.

The repository includes an official MuJoCo demo with a complete public ProcTHOR
scene, original instruction, WebSocket client and MPC. The default robot is a
kinematic TurtleBot. This is the selected reproduction path; optional MicroDuck,
Habitat benchmarks and real-robot deployment are outside this task.

Primary-source code mapping and license/provenance are in
`references/upstream/2026-09-09_lightnav0_official_demo/comparison.md` and its
`repository_manifest.yaml`. Preparation verified the pristine checkout and all
2,236 bundled asset files. Remote read-only inspection verified a reachable RTX
4090 host with a protected existing Isaac Sim process. Actual dependency/model
compatibility and navigation performance remain untested.

Execution package:
`.pipeline/experiments/2026-09-09_lightnav0_official_demo_rented4090/OPUS_EXECUTION_PACKAGE.md`.
Status: imported source and prepared manual package; not dispatched or reproduced.
