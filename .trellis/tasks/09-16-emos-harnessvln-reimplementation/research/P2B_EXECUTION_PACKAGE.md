# P2B: Actual PCT / SCAN Navigation Adapter

User authorization: implement the next bounded integration and try it in the
existing Isaac Lab simulation. Reuse gpt-5.5 / medium for implementation; the
lead owns acceptance. No model calls, physical actuation or formal long suite.

## Objective and boundary

Connect the accepted P2A lifecycle core to actual native PCT planning and SCAN
execution. The smallest missing behavior is a changing spatial target becoming
a real PCT route, explicitly accepted by SCAN, with correlated command output,
measured progress and confirmed stopping before another goal is admitted.

Implementation belongs in a VLA-owned adapter and explicit source patches over
the pinned native planner. Preserve optimization, V12 policy and native gains.
Publication alone is not acknowledgement; old splines cannot drive a new goal.
The final pilot must execute two spatial goals in one continuous Isaac episode.

Local source of truth: /Users/sun/tongbu/study/phdproject/vla.
Worker owns ONLY:
.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/backend_adapter/**

The accepted navigation_service is read-only. If it needs a change, explain the
specific reproduced defect to the lead before editing it. All references and
both sibling repositories are read-only. You are not alone: preserve others'
edits and do not stage, commit, spawn agents or overwrite lead-owned files.

Lead owns source/configuration/asset qualification, remote orchestration,
Isaac-runner adaptation, task records and independent acceptance. Worker builds
local code, tests and reproducible build/launch entrypoints; do not launch the
simulator or remote processes independently.

## Read first

- Task prd.md, design.md, implement.md and research/isaac_backend_mapping.md.
- research/acceptance/P2A_LEAD_REVIEW.md and accepted navigation_service/core.py.
- .trellis/spec/backend/quality-guidelines.md and simulator-inference-evidence.md.
- references/upstream/2026-09-16_lite3_isaac_harness_backend/SOURCE.md.
- Frozen source/pct_scan_foxy/src/plan_manage: scan_replan_fsm.cpp,
  closed_loop_controller.cpp, associated headers, messages and launch/configs.
- Frozen source/pct_global/src/pct/pct_planner Python wrapper and config.
- Frozen bridge: foxy_bridge_node.py, protocol.py, transport.py,
  command_state.py, run_pct_scan_building.py.

Existing reference commands (read only): machine-dog-nav/.pipeline/experiments/
2026-09-11_pct_scan_upstream_baseline/tools/probe_native_plain_pct.py,
run_native_on_host.sh and config/native_launch.py. Do not copy the old modified
SCAN workspace or old result as new evidence.

## Required interfaces

1. A Python 3.8 ROS/Foxy adapter using the accepted P2A core. Real PCT planning
   from measured current pose and requested metric target, same frozen map and
   native optimization. Return native optimizer body-reference Z, excluding
   upstream display-only +0.5 m. No canned routes or heuristic fallback.
2. Backend methods must return promptly: perform slow planning without blocking
   safety/watchdog feedback. Explain the interaction with the core's synchronous
   planning port. Avoid a second model/planning decision owner.
3. Correlated route admission at the actual SCAN consumer. Use explicit command
   identity/generation through route, spline and controller, with a minimal
   reproducible patch. No inference from an unrelated spline or publication.
4. Cancel/stop disables old trajectory execution and suppresses late old
   messages. Confirm hold at the command consumer, then measured stillness;
   only then emit stopped/arrived. Goal replacement waits for that confirmation.
5. A monotonic wall-time watchdog must close the command gate on stale odometry,
   missing heartbeat/owner, cancellation, map invalidation, planner error or
   transport loss. It operates independently of model calls. Remap raw SCAN
   output so it cannot bypass the gate into the existing bridge.
6. Persistent node and policy episode across goals. No reset, pose injection,
   velocity teleportation or controller replacement. Diagnostic simulator-truth
   localization is allowed and must be labelled, not described as SLAM.
7. Record immutable command/goal/route identity, actual PCT output, admission,
   generated spline identity, raw/gated commands, measured pose/speed, stop
   request/ack, and terminal cause. Keep failure logs.

Send the lead an early concise wire/launch contract (topics, ports, config,
CLI inputs, acceptance/stop semantics) before expanding implementation; this
lets the independent Isaac-runner adaptation proceed without conflicting edits.

## Artifacts and checks

Keep code, explicit upstream patches, patch source hashes, configs, regression
tests, build/launch instructions and RESULT.md in the owned directory. Frozen
reference bytes must not be edited. A materialized overlay must be reconstructible
and its source hashes recorded. Do not hide new authored source as generated data.

Test actual boundary parsing/correlation and control-gate failure behavior,
including delayed old splines, malformed IDs, cancellation/replacement, stale
odometry, disconnect and timeout. A manually injected backend is a contract
test only. Lead separately runs the code in the real Foxy image and Isaac.

Remote execution root will be under
/home/sun/vla_exec/2026-09-16_pi_cortex_harnessvln/p2b/.
Sync gate: local source/config manifest equals execution copy before launch;
return raw run artifacts and verify hashes locally. Existing native execution
and asset paths are read-only inputs. No remote-only fixes may remain.

Return the strongest justified claim, exact commands/test logs and remaining
integration gaps. Do not call unexecuted ROS or simulator integration working.
