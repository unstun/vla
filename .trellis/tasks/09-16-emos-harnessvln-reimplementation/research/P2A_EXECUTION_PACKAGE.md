# P2A Execution Package: Persistent Navigation Goal Lifecycle

Status: implemented by /root/p2a_navigation_service through native
collaboration.spawn_agent, gpt-5.5 / medium; accepted by the lead for the
bounded lifecycle contract only. See acceptance/P2A_LEAD_REVIEW.md and
acceptance/FINAL_ACCEPTANCE.json. The complete HarnessVLN task remains open.

## Objective

Implement the production-oriented goal lifecycle needed between HarnessVLN's
validated target and the existing PCT/SCAN/Lite3 backend. This is one bounded
P2 slice, not full HarnessVLN or simulator acceptance.

Read the active task PRD/design/implementation plan and research source mapping.
The earlier Pi gateway is an explicitly deterministic fixture and must remain
an immutable experimental reference. The new service must not silently use it
or turn fixture geometry into claimed runtime functionality.

## Source of truth and ownership

Local source of truth: /Users/sun/tongbu/study/phdproject/vla.
Executor owns only:
.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/navigation_service/**

The lead owns task/research records, baseline acquisition, runtime inspection
and final acceptance. You are not alone in this codebase: preserve other edits,
do not revert them, and adjust to concurrent changes. Do not stage or commit.
Sibling machine-dog-nav and machine-dog and acquired reference snapshots are
read-only. Do not spawn further agents.

## Existing inputs

- Committed Lite3 bridge: references/upstream/2026-09-16_lite3_isaac_harness_backend,
  machine-dog-nav 848b4aecd01237805e0564c88d3ba09146fd2353.
- Native planner: machine-dog-nav/integration/pct_scan_upstream_ws, canonical
  PCT-SCAN-ROS2 1cf45a1c12ca785ce533293302be09d51daf0ccb with recorded Foxy port.
- SCAN pathCallback accepts initial_path and can replan. The existing reference
  publisher is one-shot and exposes no correlated action lifecycle.
- Do not treat path publication or an old spline as an acceptance receipt.
- No fake backend may be the default for a runnable production-facing entry.

## Required behavior

Build a small typed Python service/core with an explicit backend port. Favor
stdlib and Python 3.8-compatible interfaces for the Foxy boundary. Keep model
tool arguments separate from internally validated spatial targets.

1. Explicit run/epoch, request, goal and route identity. Validate frame/units,
   finite coordinates, current map/evidence revision and observation freshness.
2. One active command owner. Correlated submit/accept/reject/feedback/result
   lifecycle. Duplicate requests are idempotent; same ID/different payload is
   rejected. Reordered or old-epoch feedback cannot mutate a new goal.
3. Replacement is cancel-then-confirm-stop-then-submit, not concurrent goals.
   Cancellation is idempotent. A late acceptance/success cannot resurrect a
   cancelled or superseded goal. Missing stop acknowledgement retains the
   unresolved command owner and blocks replacement.
4. Timeout, backend/transport failure and localization/map invalidation produce
   explicit outcomes. They cannot create navigation success or silently
   release command ownership while motion is unresolved.
5. Persistent service state across multiple subgoals; no simulator/controller
   reset calls. Emit structured action/event records with monotonic sequencing
   and goal correlation. Separate actual terminal cause from model prose.
6. An unavailable backend fails explicitly. Test doubles are confined to tests.
   If exposing a transport entry, it must default to unavailable/refuse execution
   until a real backend is configured, not auto-acknowledge requests.

Keep the boundary small: no general agent framework, model integration, graph
memory, camera implementation, new locomotion or planner optimization changes.
Do not claim that an interface-only backend port is actual ROS integration.

## Validation and return

Implement meaningful regression tests for two-goal sequencing, acknowledgement
correlation, replacement/cancel ordering, delayed old feedback, duplicate IDs,
expiry, backend failure, stale/map-changed evidence and invalid payloads.
Exercise failure after command submission, including an uncertain outcome.
Use test-controlled clocks. Include actual command-call traces so tests can
show no second motion submission before the first stop is acknowledged.

Run targeted local checks; preserve exact commands, output and source hashes
under the owned directory. Return RESULT.md listing changed files, contract,
tests, unresolved integration points and the strongest justified claim. Tests
without a live backend are lifecycle/contract evidence only.

No paid model calls, GPU simulator launch, formal run or physical actuation in
this assignment. No remote edits are needed. The lead separately checks actual
runtime resources and may assign a bounded simulator integration after this
contract is reviewed. Final implementations and logs must remain local; future
remote execution requires input hash equality and verified artifact return.
