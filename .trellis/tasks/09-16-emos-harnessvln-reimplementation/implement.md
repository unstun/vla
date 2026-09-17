# Implementation And Acceptance Plan

The full task remains in progress. P2A lifecycle acceptance and the bounded P2B
continuous native navigation pilot passed. Next are Pi/Cortex tool integration,
real sensing/grounding and broader fault validation.

## P0: Direction and source audit

- [x] Record Pi plus Cortex as the selected upper runtime direction.
- [x] Record Isaac Lab / machine-dog-nav reuse and eventual physical deployment.
- [x] Recheck the paper placeholder, published mechanism descriptions and
  existing native navigation source/evidence.
- [x] Export the 79-file committed Lite3 bridge from 848b4aec into VLA.
- [x] Verify 65 native planner-port hashes and audit prior executed source.
- [x] Freeze 65 canonical native planner/notice files, eight explicit Foxy
  adaptations and 145 global PCT/license files from committed upstream objects;
  reconstruct and verify the port without sibling reads.
- [x] Run selected bridge CPU checks: 93 passed, 1 ROS-dependent skip,
  15 subtests passed. No simulator launched by this gate.
- [x] Locate the exact native_full02 executed runner and record its diff against
  the selected committed runner: camera metadata and capture cadence changes.
- [x] Freeze scene/map/configuration against selected execution evidence and
  qualify the committed runner with the reviewed external-goal patch in a
  fresh bounded Isaac standing episode. This proves standing/transport/finish,
  not navigation or unchanged-source parity.

## P1: Offline interface slice (completed, limited claim)

- [x] Acquire pinned Pi, EMOS and EmbodiedAgents references.
- [x] Install real Pi 0.85.1 with a frozen npm lock.
- [x] Implement/test the fixture gateway and real Pi loop.
- [x] Check stale/forged evidence, inactive subgoals, unreachable goals, failed
  execution, duplicate calls, raw-tool bypass, batched movement and false stop.
- [x] Pass 16 tests locally and on the 5070 Ti, with source/return hash proof.
- [x] Preserve the 10-turn / 2-fixture-movement / 3-rejection trace.
- [x] Label zero actual LLM calls, no Cortex runtime and no physics navigation.

## P2: Existing navigation backend, persistent action service

- [x] Inspect the actual Isaac Lab and Podman/Foxy runtime copies and resource
  state; reuse those paths instead of replacing them with a generic EMOS stack.
- [x] Run all eight existing bridge transport tests in actual Foxy/rclpy on
  5070 Ti with source hash equality; this includes the earlier ROS-only skip.
  This isolated CPU-container check does not run Isaac or the policy.
- [x] P2A: implement and independently accept the Python lifecycle core and
  explicit backend port. After three correction requests, 37 executor tests
  and 21 lead tests passed locally and under actual Foxy Python 3.8.10 with
  matching source hashes. See research/acceptance/P2A_LEAD_REVIEW.md.
- [x] Verify committed bridge, all 217 V12 runtime files and checkpoint,
  native PCT/SCAN and assets in the local source and selected execution copy.
  Actual PCT RPC and scan_03 Foxy build/controller boundary checks passed;
  installed SCAN file identities are recorded separately.
- [x] P2B: bind the accepted goal/route lifecycle to actual PCT planning and
  SCAN pathCallback, with measured acknowledgement/result/stop evidence.
  Root-executed actual4 passed independent physics and return-hash checks.
- [x] Add an independent freshness watchdog and persistent asynchronous
  cancellation/arrival stop confirmation.
- [ ] Integrate and test map-invalidation propagation through the real service.
- [ ] Verify Cortex-compatible dispatch with one decision owner; its planner
  stays disabled and it has no alternate raw-control path.
- [x] Run a bounded control-only case before adding an LLM: two distinct spatial
  goals in one episode, no robot/map/policy-history reset, real measured motion.
- [x] Verify one mid-motion cancel/stop/resubmission in actual Isaac, plus
  cancelled/old-generation spline suppression in the real C++ controller probe.
- [ ] Expand goal replacement, duplicate/reordered messages and reconnect
  validation across the full integrated runtime.
- [ ] Compare commands, trajectory and contacts to the frozen native baseline
  so an interface adaptation cannot silently change lower-level behavior.

## P3: Actual perception, localization and paper mechanisms

- [ ] Add aligned RGB-D and frame-time camera transforms from the selected rig.
- [ ] Check depth convention, intrinsics/extrinsics and invalid-depth behavior
  against rendered geometric targets, then sensor replay.
- [x] Locate the separate FAST-LIVO2 deployment candidate and its local
  maintenance/candidate/stability evidence boundaries.
- [ ] Pin and test the selected real SLAM/LIO version and map/odom/base/camera
  chain. Keep the diagnostic truth-pose profile explicitly separate.
- [ ] Implement language subgoal initialization, hierarchical event memory and
  ST Graph places/entities/relations with paper-style retrieval.
- [ ] Implement actual view/region grounding and navigation projection.
- [ ] Exercise all eight tools on real observations; remove fixture substitutes
  from the production configuration.
- [ ] Check observation freshness, reachability, task consistency, verified
  backtracking, contradictory evidence and stop acceptance.
- [ ] Fault tests: RGB/depth loss, pose jump, map epoch change, blocked target,
  planner failure, contact events, model delay/failure and transport loss.

## P4: Language-driven Isaac evaluation

- [ ] Freeze prompts/model/provider, scene/map prior, calibration, instructions,
  budgets and repeats before running a paid or extended suite.
- [ ] Start with a bounded single-instruction pilot, then multi-subgoal and
  ambiguity/recovery cases on an unchanged lower-level stack.
- [ ] Include directional and relational instructions, passing through a door,
  finding an object, returning to a visited place and correct final stopping.
- [ ] Include held-out cases and repeat runs; preserve failed attempts.
- [ ] Report task and oracle success where defined, stop error, completion of
  intermediate constraints, collision/contact, interventions, path/time, model
  calls, latency and cost. Show rendered and logged evidence from the same run.
- [ ] Run mechanism ablations against the same backend and frozen cases:
  without graph memory, without task progression, and without validation.
  Ablations that remove protection stay in simulation.
- [ ] Record every paper deviation; do not relabel Isaac results as published
  benchmark reproduction.

## P5: Physical deployment readiness

- [ ] Reuse the same tool/action contracts with real sensor replay and
  receive-only live topics; validate calibration, pose quality and timing.
- [ ] Verify stale-input/timeout/cancel/hold behavior and independent operator
  takeover near the command consumer; prove model failure cannot bypass them.
- [ ] Freeze a reviewed hardware/software/calibration/velocity envelope.
- [ ] Conduct separately authorized supervised low-speed trials, then expand
  task/scene complexity only after the earlier gate passes.
- [ ] Require repeated task completion and bounded failure behavior in the
  declared envelope before describing the system as deployment-ready.

## Evidence and scope

The source of truth is this VLA repository. Remote copies are execution-only.
Every run must match the local input hash manifest and return raw evidence.

Do not edit machine-dog-nav, replace V12, reactivate the rejected V17 branch,
import a dirty tree, start a formal long run or actuate the real robot as an
implicit side effect of this plan. A prototype or fixture pass cannot satisfy
P2-P5. Numerical performance/latency/safety thresholds are frozen in the
corresponding run contract after baseline measurement, before evaluating the
candidate; no after-the-fact threshold relaxation is permitted.
