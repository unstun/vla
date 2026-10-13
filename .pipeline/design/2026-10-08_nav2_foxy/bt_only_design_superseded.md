---
date: 2026-10-08
stage: planning
status: proposed_design_with_user_selected_platform
evidence_label: surveyed
reviewed: false
runtime_execution: not_run
---

# Lite3 navigation on Ubuntu 20.04 and ROS 2 Foxy

## Decision and scope

Dr Sun selected the existing Jetson, Ubuntu 20.04 and ROS 2 Foxy because that
robot cannot be upgraded to Ubuntu 22.04. Treat this as a deployment constraint,
not a claim about all Jetson hardware. This document designs the migration;
it does not authorize robot motion or record an implemented migration.

Use official Nav2 orchestration with the existing native PCT/SCAN navigation
and command/stop contracts. The first increment adopts `nav2_bt_navigator`,
`nav2_behavior_tree`, `nav2_msgs` and `nav2_lifecycle_manager`, plus their pinned
Foxy dependencies. It does not start stock planner/controller/recovery servers.
PCT/SCAN continue to own planning and tracking. Wrapping them in `nav2_core`
plugins is a possible later increment, requiring separate interface qualification.

Nav2 is a task-management boundary, not evidence that mapping throughput,
continuous stair motion or 30 Hz local planning has been fixed. The existing
continuity task stays in progress. v48 remains the reference, v82 a frozen failed
candidate, and v84/v85 component investigations; no new runtime version is
allocated for this documentation-only decision.

## Platform and upstream pin

| Item | Design constraint |
| --- | --- |
| Target | Existing Jetson, Ubuntu 20.04, ARM64; inventory exact SKU/JetPack first |
| ROS | Foxy throughout the target ROS graph; no Humble/rolling binary overlay |
| Nav2 reference | Release 0.4.7, commit `a947ab5656e46ae3aa1afdf95e1706a16e478974` |
| License | Apache-2.0; retain notices on deliberate source acquisition |
| Installation | Resolve available ARM64 packages/source dependencies, then freeze exact versions and hashes before building |
| Hardware drivers | Preserve installed JetPack, CUDA and sensor/locomotion driver compatibility |
| Build boundary | amd64/Humble component tests do not qualify ARM64/Foxy binaries |

[REP 2000](https://github.com/ros-infrastructure/rep/blob/master/rep-2000.rst)
lists Focal/ARM64 as a Foxy target. Foxy maintenance ended in 2023; keep a
reproducible dependency record rather than depending on an unpinned moving
branch. The [Foxy release record](https://github.com/ros/rosdistro/blob/master/foxy/distribution.yaml)
lists navigation2 release 0.4.7-1 and source branch `foxy-devel`.
The source release and Debian package revision are different identifiers.

The [source audit](source_audit.json) records inspected file hashes. This is
source inspection, not an executable Nav2 import. Before implementation, acquire
the selected snapshot under a dated purpose-named directory in this repository,
record dependencies and original upstream build instructions, and record every
local patch. Existing PCT native binaries require source/dependency and ARM64
qualification; historical Humble Python extensions cannot be copied to Jetson.

## Responsibilities and process boundaries

| Component | Responsibility | Authority limit |
| --- | --- | --- |
| Existing mission/backend entry plus Nav2 adapter | Validate goals, allocate full identity, manage one owner, dispatch Nav2, expose authoritative mission state | No second controller or independent ownership registry |
| Official Foxy BT navigator | Execute the selected mission tree, publish action feedback, orchestrate success/failure | Its action terminal state does not prove physical stop |
| Custom BT leaf | Submit and observe the existing backend mission using Foxy-compatible plugin APIs | No heavy solve or blocking physical-stop wait in `tick()`/`halt()` |
| PCT | Global route from measured state and selected map/layer | A route alone cannot authorize motion |
| SCAN | Native initialization, optimization, timed trajectory, full-curve/support/dynamic validation and tracking | Cannot bypass owner, map, body or stop conditions |
| Mapper | Single writer and immutable completed revisions with original source stamps | New publication time cannot refresh old observation evidence |
| Independent sensor veto | Reject on hazardous, missing, unpaired or stale observations | Cannot declare a stale map safe or clear unprocessed hazards |
| Existing command gate and stop supervisor | Sole accepted command path, watchdog, revocation, controller hold and measured stop | Must remain effective while BT/planning is blocked or absent |
| Existing locomotion adapter | Apply accepted commands and provide applied/stop evidence | Simulator PD/RL evidence is not a real-robot deployment qualification |

Implement adapters around the existing backend, not a second mission framework.
Run heavy map/PCT/SCAN work outside the BT executor; keep the command watchdog
and sensor callback execution independent of those workers. Threads alone do not
guarantee latency under CPU saturation. Qualify executor scheduling and, if needed,
process separation on the target before claiming the fault path is independent.

## Foxy interfaces and adapter contract

The audited Foxy interfaces differ from current Nav2 examples:

| Audited interface | Relevant Foxy contract | Consequence |
| --- | --- | --- |
| `NavigateToPose` | `pose`, `behavior_tree`; Empty result and progress feedback | Keep detailed stop/failure evidence in existing mission status |
| `ComputePathToPose` | `pose`, `planner_id`; returns Path and planning time | Do not generate newer `start`/`use_start` request fields |
| `FollowPath` | Path and `controller_id`; Empty result | No timed spline/PVA or full P2B identity; no newer goal-checker selector |
| `nav2_core::Controller` | `setPlan(Path)` and `computeVelocityCommands(pose, velocity)` | A stock plugin boundary does not preserve the native execution contract by itself |
| BT navigator configuration | `default_bt_xml_filename`, `plugin_lib_names` | Use this release's loader, not modern navigator plugin APIs |

Primary files are linked individually in [source_audit.json](source_audit.json).
The default behavior tree clears costmaps and includes spin recovery; replace it
with a small purpose-owned tree that delegates a mission and waits for the
backend's complete outcome. Do not load clear/spin/backup recovery nodes for the
stair profile. The pinned root tree has no `nav2_collision_monitor` package;
the design relies on the existing veto/stop path, not a newer package assumed
to exist in Foxy.

Proposed routing (names to be frozen in the first implementation version):

- The existing mission entry remains public. It issues exactly one internal
  `/lite3/nav2_internal/navigate_to_pose` action after creating an owner-bound
  dispatch record. The BT leaf takes the `goal` blackboard input and asks the
  backend to consume that record once, matching exact frame, pose, stamp and
  full identity. It must reject a missing/expired/already-consumed record.
- Public caller and internal Nav2 action UUIDs map to the complete existing
  identity: `run_id`, `epoch`, `request_id`, `goal_id`, `route_id`, `command_id`,
  `generation`, `map_epoch`, `map_revision`; accepted curves also bind `traj_id`.
  These remain in P2B payloads/backend state, not invented fields in stock actions.
  Preserve existing controlled route/generation transitions and their validation.
- The navigator's `goal_pose` subscriber is remapped away from the public RViz
  input. RViz requests enter through the same public mission validation. The
  public adapter ignores caller-supplied BT filenames and selects the frozen tree.
  Namespaces are routing, not access control: direct internal requests receive no
  new command ownership, and a live authorized ROS graph is a deployment assumption.
- The leaf's nonblocking operations are conceptually `start_bound_mission`,
  `read_compact_status`, and `request_owned_stop`. These are adapter operations,
  not new ROS interfaces claimed to exist today. Reuse the current backend API;
  freeze transport and timeout behavior during the first buildable slice.
- The original goal, including Z and final yaw, stays distinct from PCT's
  grid-snapped route endpoint. The exact `P2BRoute.has_goal_pose/goal_pose`
  propagation must pass end-to-end tests; the inspected generic `submit_route`
  function alone does not populate those fields and is insufficient as proof.

The standard `nav_msgs/Path` may carry XYZ route geometry, but it does not carry
the native spline timing, boundary velocity/acceleration or owner authorization.
Keep those native contracts intact instead of reconstructing them from a Path.

## Cancellation, preemption and terminal outcomes

Foxy's `BtActionNode::on_cancelled()` returns SUCCESS by default. Its `halt()`
requests action cancellation and waits only for the action protocol response.
The navigator subsequently terminates the action on BT cancellation. None of
these paths establishes a physical stop. See
[BT action node](https://github.com/ros-navigation/navigation2/blob/a947ab5656e46ae3aa1afdf95e1706a16e478974/nav2_behavior_tree/include/nav2_behavior_tree/bt_action_node.hpp#L123)
and [navigator termination](https://github.com/ros-navigation/navigation2/blob/a947ab5656e46ae3aa1afdf95e1706a16e478974/nav2_bt_navigator/src/bt_navigator.cpp#L305).

Required sequence:

1. Public cancel/preempt or a fault immediately revokes the old owner's permission
   for nonzero commands through the existing gate, independently of BT ticks.
2. Request the matching P2B stop and cancel the internal Nav2 action. BT `halt()`
   also makes an idempotent owned-stop request; do not rely on that callback alone.
3. Retain the old identity as the stop-evidence owner. Wait for matching
   `P2BAdmission`, `consumer=controller`, stopped status, controller hold and
   measured stillness through the existing evidence checks.
4. Missing/late/unmatched evidence remains stopping/uncertain with no new motion
   grant. FSM rejection, cancellation ACK, zero Twist and timeouts are not success.
5. Only a confirmed stopped state permits release and a new owner. Queue at most
   one replacement goal; additional requests receive an explicit busy response.

Override cancellation-to-success behavior in the custom leaf. Ordinary leaf
SUCCESS requires backend arrival including exact goal/height/yaw and final stop.
BT failure triggers the same stop path; expose mission failure as terminal only
after the original stop contract completes. An early internal Nav2 terminal
result is transport state and cannot release ownership. A stale success callback
after cancellation cannot win the race. Repeated cancels are idempotent.

The existing watchdog must close the gate on mission/BT loss without waiting for
the lifecycle manager. Inspected 0.4.7 lifecycle source provides transitions but
contains no `bond` mechanism; do not assume modern lifecycle fault monitoring.
On restart, discard dispatch records and command grants, reconcile measured
state and require a fresh request. Never resume a prior moving command implicitly.

## Mapping, timing and geometry

Keep original paired sensor/body stamps, support provenance, map revision,
full double-cylinder geometry, PVA/dynamics and complete-curve checks. Preserve
the existing 250 ms map-evidence freshness limit and the original body/heartbeat
thresholds. Source age, map completion age and held-map age are separate metrics.
Fast sensor veto only adds rejections. v84 showed distinct-frame dropping loses
occupied evidence; retain all distinct observations unless a separately tested
equivalence rule is accepted. v85's measured-body check still needs moving and
braking-envelope integration before adoption.

Retain the previously selected targets: global planning 1 wall Hz, local planning
and controller 30 wall Hz. Report useful completed solves, raw controller commands,
gate decisions, sensor processing and map completions separately, with deadline
misses and longest gaps. A 30 Hz BT/decision timer cannot satisfy those targets.
Mapping overload may still force a stop; Nav2 does not change that fact.

Use separate simulator and robot clock/localization profiles. Simulator `/clock`
and diagnostic truth odometry cannot become robot localization. On Jetson, bind
sensor source stamps and measured transforms to the actual clock chain; use
monotonic elapsed time for watchdogs and reject backward/invalid time transitions.
Freeze the deployed frame tree and map-layer association before execution.

## Implementation slices and acceptance

| Slice | Deliverable | Required evidence before progressing |
| --- | --- | --- |
| 0: target inventory | Jetson SKU, JetPack/L4T, OS/architecture, ROS/RMW, sensor/TF topics, current locomotion interface and pin, memory/CPU budget | Read-only receipt; no OS/driver changes; unresolved compatibility remains explicit |
| 1: Foxy build and mock | Pinned Nav2, thin adapter, one purpose-owned BT and mock P2B backend | Foxy build/load; start, failure, cancellation and restart; zero actuation publishers; ARM64 build receipt required for target qualification |
| 2: command-free integration | Full identity and stop/goal binding through real backend interfaces with fake actuator | The matrix below passes, including failure while mapper/BT is blocked; no hardware sender |
| 3: Newton integration | Versioned integration with preserved original sensors, route, policy and safety profile | Flat start/walk/cancel/hold first; then original corner/stair/obstacle route, physical outcome, timing and ordinary wall-time video |
| 4: Jetson receive-only | Actual sensors/localization and complete compute path with actuation disabled | ARM64 runtime and resource/latency/clock evidence; no command reaches locomotion |
| 5: robot qualification | Explicitly authorized bounded motion using pinned machine-dog deployment interface | Separate authorization and robot-specific stopping/geometry acceptance; not covered by simulator passes |

Required failure tests for slices 1–3:

| Condition | Observable pass criterion |
| --- | --- |
| Cancel races with success or a late curve | Old owner never regains a command grant; no false arrival |
| New goal during motion | Old identity stops and is measured still before new admission |
| Wrong run/epoch/generation/map/consumer or delayed old ACK | No acceptance or stop completion for the current owner |
| Controller ACK without hold/stillness, or missing ACK | Remain stopping/uncertain; no timeout-based release |
| Direct goal_pose/action request without a bound dispatch | No new effective motion owner or command |
| Map stalled 650 ms, sensor loss, bad pairing, clock jump, BT/backend exit | Original gate rejects; capture revocation-to-applied-stop latency without relaxing thresholds |
| Obstacle seen only in a backlogged scan | Preserve/veto that evidence; no clearing by a later timestamp alone |
| Missing support, wrong level, low unmapped box or stair riser | Original geometry/support cases keep their expected outcomes |
| Requested goal differs from route endpoint | Original XYZ/yaw/stop acceptance controls success |

Bind each code/configuration increment to the next unused integer version, a
preserved predecessor, source/install/input hashes and matching test/video
artifacts. Do not edit frozen v82/v84/v85 sources or promote current.json merely
because Nav2 starts. Keep a mutually exclusive launch selector for the reference
and Nav2 candidate; both must never publish effective commands simultaneously.
Rollback occurs only after stop verification and restores the recorded reference
launch, without deleting candidate evidence.

## Evidence and outstanding work

Local source of truth remains this VLA repository. Any execution copy must match
the selected source/config/dependency manifest before running and return compact
results and hashes to the same local paths. Heavy captures/builds stay on
gpu5070ti with verified provenance; no remote-only qualification claim.

Checked local evidence includes the P2B message fields, actual ROS receiver,
current repair specifications and [v84/v85 report](../../experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-08_mapping_admission/REPORT.md).
Older scan_10 Foxy builds do not qualify current v82 or this adapter. Exact target
hardware/dependencies, actual deployment localization and locomotion interface,
ARM64 PCT buildability, adapter transport and measured stop/timing performance
remain to be verified. No runtime migration, external execution or robot action
was performed to produce this design.
