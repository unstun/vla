# v222 execution

Follow ../10-17-pct-scan-traversability/implement.md, steps 5-7 after the v221 receipt passes.

Before editing, resolve all inherited file hashes and relevant backend specs. Add meaningful integration tests for actual returned paths and native query verdicts. Build on gpu5070ti without launching physics. Return version-owned source/build/test/replay receipts locally, then review the diff and freeze the source manifest. Any later logical repair receives a new integer version.

## 2026-10-17: actual implementation version v230

The original v222 name was reserved for this task before the intervening
scoring/lattice/height fixes. Implement now as v230, parent frozen validated
v229, preserving the old snapshots. Reuse pull queries in the existing service
and Header->BT trigger; no DirectIO/MotionExchange session protocol is needed.
See versions/v230/PLAN.md for source-bound typed evidence and validation gates.

## v230 verification receipt

Attempt04 passes nine packages/154 distinct cases (174 colcon records). Actual
installed PCT fixture returns a detour with continuous 0.179713 m clearance from
a 0.15 m disk, retains it on unknown, and restores identical original geometry
on newer exact Free or new mission. Blocked terminal retention rejects.
Recorded native typed/binary parity and all occupancy predicates are unchanged
for 126324+3 queries; source identities remain nonempty/stable. Building retains
v229's exact route, 0/3821 rejected, +0.056539 m raw solid margin, 0.730794 s.
See versions/v230/RESULTS.md. Earlier failed source/tests are retained. No
physics/closed-loop NativeWorker promotion at this component gate. The approved
source commits are v229 `420a0ff9` and v230 `e9f8bec0`.

## Commit and next experiment authorization, 2026-10-17

Dr Sun approved a separate v230 commit after v229, including version index and
task documentation. He then authorized one complete v230 closed-loop physics
route from the original v219 endpoints/gates, unchanged RL and 0.35 m thresholds,
with 45-55 s stair diagnostics and a comparison video. That experiment is a
separate run package; it does not rewrite this frozen component gate.

## v231 single physical attempt: failed

The authorized original-route v230 execution ran once under frozen v231
bindings, unchanged RL/0.35 m guards. Controller_server SIGABRT (-6) near46.7s
prevents route completion. Original recording ends at600000 steps without a
finish request; original full-route and shared-terminal gates both fail.
42 completed successful rounds in45–55s stop at46.376s, with one incomplete
start; no completed rounds start at47–55s. No positive physical feedback-detour
claim is supported. Keep the task in progress and v219/v220 accepted. See
versions/v231/RESULTS.md and the linked audit; no retry or controller fix in
this execution-only step.
