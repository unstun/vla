---
origin: ai_only
reviewed: false
status: draft
---

# HarnessVLN On Pi, Cortex And The Existing Lite3 Stack

## Current architecture

Dr Sun's latest direction replaces the Habitat-first proposal with the existing
Isaac Lab / Lite3 navigation stack and makes physical deployment the final
acceptance target. Pi remains the sole model/tool-loop owner. The original
Cortex-only and Habitat-first choices are superseded.

    Language instruction + synchronized sensor evidence
      -> Pi decision loop
      -> HarnessVLN task state, event memory and spatiotemporal graph
      -> proposal / grounding / geometry / task-state validation
      -> Cortex-compatible robot-tool adapter
      -> persistent navigation action service
      -> PCT global route -> SCAN local planning/control -> Lite3 V12
      -> Isaac Lab initially; real Lite3 after deployment gates
      -> measured pose, execution and contact feedback -> harness update

Cortex is not a replacement for the selected planners or locomotion controller.
Its standalone tool-server interface is not yet implemented. Its private ROS
discovery/dispatch seams need a tested adapter with the autonomous planning loop
disabled. EMOS Kompass and the public Motion Host Lite3 plugin are not selected
as replacements for this existing navigation-to-locomotion path.

## Source identities and current evidence

- Pi agent-core / pi-ai npm 0.85.1; registry gitHead
  d981de1229ef899957bbe968bc8dcda02a21f477.
- EMOS 31b82958e7a1646b9af606184518333c97290f58, with EmbodiedAgents/Cortex
  c37ab75db4aba88bcc99d17f6eabac146ad46d20.
- machine-dog-nav branch codex/scan-foxy-isaac, selected bridge commit
  848b4aecd01237805e0564c88d3ba09146fd2353. Its 79 bridge files match the
  current bridge working tree and were exported from committed git objects.
- Native PCT/SCAN upstream 1cf45a1c12ca785ce533293302be09d51daf0ccb.
  The 65 canonical planner/notice files and eight explicit Foxy adaptations
  are now frozen in VLA and match the inspected UPSTREAM_MANIFEST.json.
  Another 145 global PCT/license files came from the same committed upstream.
  The port can be reconstructed and hash-verified without sibling reads.
  Scene/map/configuration and a fresh episode remain separate baseline gates.
- Existing VLA V12 snapshot:
  references/upstream/2026-09-11_lite3_v12_locomotion. Policy model_149999.pt,
  SHA-256 a9d31dce90e6e8c564d955e473d6d3502f893d7ef5a5c1efaf5bb50d6b3d5450;
  machine-dog source identity 8c3fdffa84b85be0704a10ea5b2533817d543822.
- Method: HarnessVLN 2609.15195v1. Code placeholder:
  AgibotGeneral/harnessvln b71bed50953c5f300ce2c5aeefbb18383514c11b.

Current bridge acquisition:
references/upstream/2026-09-16_lite3_isaac_harness_backend.
Existing September 11 snapshots remain unchanged.

Read-only native_full02 evidence records 98.08 simulation seconds, 74.063 m
travel, 0.03768 m final XY error, zero measured non-foot force, no autoreset
and no pose injection. This is a previous fixed-goal navigation episode.
Of 151 compared execution-source files, 150 match the current corresponding
files; run_pct_scan_building.py differs. The exact historical runner was found
and hash-verified; research/runner_delta.diff records camera metadata and
capture-cadence changes. Do not transfer that historical result to a new runner
or to language navigation without a new test.

The first Pi fixture slice passed 16 tests on two hosts. The committed bridge
slice passed 93 CPU tests and 15 subtests; one rclpy-dependent test was skipped.
Subsequently all eight transport tests, including that ROS-only case, passed
in the existing 5070 Ti Foxy/Python 3.8.10 image with matching source hashes.
Seven overlap the earlier CPU transport cases. None of these counts represents
a new Isaac or physical navigation episode.

## Main implementation gap: persistent subgoal execution

The selected upstream reference_path_publisher publishes configured waypoints
once after odometry arrives. SCAN's pathCallback already accepts a new
initial_path and transitions to trajectory generation/replanning. The missing
integration is a persistent, goal-identified service around that capability:

1. Admit a validated spatial goal with goal ID, frame/map epoch and source
   observation. Start from measured current pose, not a frozen episode spawn.
2. Ask the existing PCT planner for a route using the selected geometric map.
3. Submit the route to SCAN and obtain explicit acceptance/rejection evidence.
4. Correlate plan/execution feedback with the active goal and route identity.
5. Report actual arrival, rejection, timeout, cancellation or execution failure.
6. Allow replacement only after the previous command ownership is settled.

Publishing a path is not an acceptance receipt. A zero process exit, proximity
to a benchmark goal, or an old spline must not masquerade as current-goal
completion. If an acknowledgement extension is needed, keep it in the VLA
execution overlay and record its patch; do not alter planner optimization
silently.

One simulator process, one articulation, one policy state/history and one
continuous localization/map state persist across subgoals. The fixed-goal
recording wrapper's episode termination must not end every navigation action.
Independent evaluator goal-distance fields stay outside agent inputs.

## Perception and localization contract

Each observation must carry observation ID, capture timestamp and clock
domain, image/depth identity, intrinsics, depth convention/units, camera pose,
transform chain, localization source/quality and map epoch. Backprojection and
target freshness use evidence from that same capture, not a later body pose.

The inspected Building runner reads root_pos_w / root_quat_w directly from
Isaac. Its odometry is simulator truth; a ray-cast MID-360 is not real LiDAR/LIO.
The real FAST-LIVO2 candidate was located separately in machine-dog under
2_experiment/deployment/lite3_fast_livo2_v1.2. Its current local README separates
maintenance release v1.2.1 from experimental candidates; the September 8
fixed-input replay record still leaves motion/pose-stability and fresh live
comparison gates open. It is a reuse candidate, not verified integration into
this navigation harness. See research/isaac_backend_mapping.md.

Two explicitly labelled profiles are required:

- Diagnostic simulation: simulator pose is permitted to isolate harness bugs.
- Deployment-representative: localization comes from the selected sensor/SLAM
  provider; simulator truth is evaluator-only. Localization loss, jump or map
  change invalidates affected targets and graph anchors.

The existing VLA camera code is a reuse reference, not an automatic drop-in.
In particular, its optional fused RGB view retains an ideal head_eval depth
stream. Do not feed that combination into geometric grounding without a
verified pixel-to-ray/depth alignment. Prefer a calibrated single RGB-D camera
for the first deployment-oriented geometry test.

The known Building/PCT map is a prebuilt geometric-map condition. Declare that
prior; do not call it online unknown-environment mapping or allow hidden semantic
goal annotations to enter the agent.

## Harness mechanisms and ownership

Pi owns model API calls and turn boundaries. Project modules own the following
paper mechanisms, independently of Pi chat history and EMOS storage choices:

- Stable subgoal IDs and pending/active/completed/blocked progression.
- Working, progress and reflection memory. Reflection memory owns complete
  subgoal-specific events; graph failure annotations reference those events
  instead of duplicating full execution history.
- Persistent places/entities/relations, observation provenance and failure
  applicability in a spatiotemporal graph.
- Task-conditioned retrieval, context construction and bounded image history.
- View/region grounding, depth checks and spatial target projection.
- Central proposal validation, verified backtracking and stop acceptance.

The eight public tools are observe, observe_panorama, retrieve_memory,
ground_target, query_depth, navigate_to, backtrack and request_stop.
Every deployed tool must use actual evidence; no fixture fallback is permitted.

Pi tools are sequential. Only one movement or terminal operation is admitted
per response. The backend rechecks allowlists and validity at dispatch; raw
velocity, direct STOP, shell and parameter-edit paths are not model tools.
Long navigation actions use explicit lifecycle/feedback instead of the fixture
transport's fixed five-second blocking request.

See research/fidelity_and_deployment.md for the method-to-evidence matrix.
Preserve published constants where semantically applicable. Keep robot body
geometry, control rates and physical stop margins in a separately named
Lite3 profile rather than copying the paper's 0.10 m agent radius.

## Cancellation, stopping and controller ownership

Task completion requires semantic, geometric and progress evidence. Emergency
stop, operator takeover and low-level fault response are separate controls and
must work even when the model or Cortex is unavailable.

Retain the existing V12 interface, command bounds/watchdog, measured feedback
and contact observations. Native mode records some non-foot contacts without
adding termination; do not describe contact detection as universal collision
prevention. Any additional deployment stop policy must be separately tested,
versioned and distinguished from the native baseline.

A stale/cancelled action cannot regain command ownership after reconnect.
Request IDs are idempotent within a run/epoch. Model latency must not block the
locomotion loop. A model timeout stops or holds execution according to an
explicit tested policy, and is not a semantic task-success event.

## Method fidelity and deployment variants

Core task/memory/validation/recovery semantics target the paper. Pi/Cortex,
DeepSeek (if reused), reconstructed unreleased prompts, PCT/SCAN and continuous
Lite3 control are declared implementation/model/executor substitutions.
Isaac/Lite3 metrics cannot be reported as reproduced R2R/RxR/ObjectNav scores.
A separate original-protocol benchmark profile may be added later; Habitat is
no longer a prerequisite for the first selected robot-stack integration.

## Rollout and local source of truth

Use isolated VLA directories and execution copies. The sibling repositories
remain read-only. Import only committed code or an explicitly documented,
reviewed canonical-base/patch artifact; never copy a dirty tree silently.

Before launch, freeze source, map/scene, policy, calibration, prompts, model,
instruction list, seed and resource budget. Verify local/remote hashes. Return
sensor frames, graph/task snapshots, tool/action logs, contacts, trajectory,
native terminal cause and independently computed metrics.

The existing native runner uses an Isaac Lab environment and a Podman Foxy
container. Missing docker/ros2 on the default SSH PATH does not prove that stack
is absent. Inspect those actual execution paths before installing a new ROS
distribution. Cortex's runtime must not force replacement of the working Foxy
planner environment.

Rollback disables only the new VLA adapter/overlay. Historical MIP, fixed-goal
navigation runs, policy state contracts and source snapshots remain intact.
