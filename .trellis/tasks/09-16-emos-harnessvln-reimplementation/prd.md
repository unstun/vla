# HarnessVLN Reimplementation For Deployable Lite3 Navigation

## Goal and user direction

Dr Sun selected Pi plus Cortex on 2026-09-16, then selected the existing
machine-dog-nav Isaac Lab / Lite3 stack as the simulation and navigation
foundation. The final objective is a functional, reliable system for physical
Lite3 deployment, with the closest supportable implementation of HarnessVLN's
published mechanisms.

The official HarnessVLN repository remains a README-only placeholder.
This work is an independent method reimplementation. Implementation identity,
paper-score reproduction and physical readiness require separate evidence.

## Required behavior

- Pi owns one model/tool loop. Cortex/EMOS interfaces may organize robot tools
  and feedback; its autonomous planner must not run as a second decision owner.
- Reuse the existing Lite3 V12 control, PCT global planner, SCAN local planner,
  bridge, contact observations and Isaac Lab articulation.
- Implement all eight published tool roles with actual observations, grounding,
  navigation and feedback. Fixtures remain test data only.
- Implement evidence-backed subgoal progression, hierarchical event memory and
  the persistent spatiotemporal graph, including retrieval and failure memory.
- Convert semantic targets into calibrated, timestamped spatial goals and
  validate their evidence, geometry and task relevance before execution.
- Execute multiple changing subgoals continuously without resetting the
  physical robot, policy history or map at each language decision.
- Support cancellation, interruption, recovery and evidence-checked task stop.
  Emergency/operator stopping must never wait for model completion validation.
- Use real sensor and localization interfaces for the deployment profile.
  Simulator truth pose may support a labelled diagnostic profile only.
- Keep evaluator-only goal annotations, success flags and geodesic scoring out
  of model context and online task-completion decisions.
- Record departures from the paper: Pi/Cortex implementation, prompts, model,
  continuous control, PCT/SCAN executor, robot shape, sensor rig and task set.
- Freeze source/configuration/assets locally in VLA before remote execution;
  return raw traces, images, pose/action histories, metrics and hashes.

## Evidence and acceptance

Already established:

- [x] Real Pi loop plus deterministic Python gateway: 16 tests passed on Mac
  and the 5070 Ti host, with source and artifact hash proof.
- [x] Selected committed Lite3 bridge exported into VLA without dirty-tree
  copying; 93 selected CPU tests passed, 1 ROS-dependent test skipped.
- [x] Read-only source audit of the native planner port and prior Building run.
- [x] SCAN local planner build: `scan_04` (one-line terminal-acceleration fix) is the accepted build since
  2026-09-17 (Dr Sun). Child task `09-16-scan-terminal-accel-fix-qualification`: native A/B AC0-AC6 passed;
  8 continuous Isaac cancel/resume episodes, 7/8 passed (episode 3 failed the goal-B stillness check: V12
  policy on a zero command, no PD stance hold); evidence
  `.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/scan_fix_qualification/RESULT.md`. Simulation only,
  one flat route, no placed obstacle.

Still required:

- [ ] Full selected navigation baseline and adaptations are frozen and reviewed.
- [ ] Actual simulator RGB-D, camera transforms and localization feed the tools.
- [ ] Grounding, graph retrieval and task transitions work on real observations.
- [ ] A persistent Isaac episode executes at least two different subgoals,
  including goal replacement/cancellation, without state reset.
- [ ] Missing/stale sensors, localization loss, planner rejection, collision,
  transport loss and model timeout produce verified bounded behavior.
- [ ] A frozen multi-instruction simulation suite reports all outcomes,
  including failures, repeats, latency, collisions and intervention counts.
- [ ] The same contracts pass physical-sensor replay and receive-only operation.
- [ ] Separately authorized supervised Lite3 trials verify the deployment
  envelope, stopping and takeover before scope expansion.

## Boundaries

The sibling machine-dog-nav and machine-dog repositories are read-only in this
task. Existing VLA/MIP/Isaac results and snapshots are preserved. This direction
does not automatically authorize formal long experiments or physical motion.
The previous fixture run is not counted as HarnessVLN navigation success.
The wider task stays in progress through the remaining acceptance gates.
