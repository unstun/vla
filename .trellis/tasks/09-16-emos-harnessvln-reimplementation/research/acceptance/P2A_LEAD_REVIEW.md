# P2A Lead Acceptance

Executor: /root/p2a_navigation_service, requested gpt-5.5 / medium.
Lead owns this review and the independent acceptance tests.

**Final verdict: accepted for the bounded P2A lifecycle contract only.**
The parent HarnessVLN/Isaac/deployment task remains in progress. No actual
PCT/SCAN dispatch, Cortex transport or simulator navigation was exercised by
this service acceptance.

## Round 1: corrections required

The executor's 19 tests passed. Independent fault/order tests failed 11
assertions across 9 test methods against the source hash in round1.json.
Raw reproduction: round1.log and test_p2a_adversarial.py.

Required corrections:

1. Pending cancellation must latch ownership against late acceptance,
   progress and arrival; only a valid stop receipt may release it.
2. An execution failure is not proof of quiescence; unresolved motion retains
   ownership until the backend confirms stopping.
3. A synchronous failure callback during submit cannot become a successful
   completed response merely because the active-owner pointer changed.
4. Active command identity must survive map/epoch invalidation so the original
   command can be cancelled and its stop acknowledgement consumed.
5. Evidence must be checked again after planning before sending motion.
6. NaN, infinity and future evidence times must be rejected.
7. Unknown/malformed submit replies cannot release possibly active motion.
8. Timeout must actually request a backend stop/hold, not just update a label.
9. Concurrent admissions must not submit two command owners.

The same executor was tasked with repairs. The independent lead tests are not
executor-owned and must not be weakened to obtain a pass. This is an engineering
acceptance rejection, not an automatic tool-approval decision.

## Round 2: further corrections required

The first nine lead cases passed after repair. Source review then checked the
remaining branches of those same ownership/correlation rules. The expanded
17-case suite reproduced seven failures and one exception; see round2.log and
round2.json. Specifically: a late rejection acknowledgement still released a
stopping owner; original-map stop receipts were rejected after map change;
reentrant planning could dispatch two goals despite the thread lock; a stop
callback could admit an owner that the outer return then erased; a malformed
submit reply raised AttributeError; a different route ID was accepted; invalid
feedback poisoned the sequence cursor; and NaN configuration disabled expiry.

These findings were returned to the same requested executor. The service's
synchronous backend port also needs an explicit bounded-return contract: it
cannot claim real-time cancellation if a backend blocks indefinitely while
holding the service lock. Actual asynchronous ROS adaptation remains a later
integration gate, not something a passing injected backend proves.

## Round 3: regression pass, review not yet accepted

The lead independently reran 33 executor tests and 17 lead tests locally; both
passed (round3.json and raw logs). The identical source also passed these 50
tests under actual Python 3.8.10 in the existing isolated Foxy image; see
python38_20260916T141838Z/. No simulator or physical interface was started.

Final source review then found four more concrete transition holes, reproduced
as six failed assertions in the expanded 21-method suite (round4.log/json):

- A contradictory rejection after acceptance/progress still released motion.
- A stopped reply for another route released the current command owner.
- BackendUnavailable thrown after dispatch was treated as proof of no effect.
- Valid synchronous acceptance/progress followed by an accepted return was
  reported as failed rather than preserving the actual admission state.

These were returned to the same executor. Stop/arrival receipts also require
an explicit backend guarantee of quiescence; caller-driven map invalidation
and timeout checks must not be mistaken for an autonomous watchdog.

## Independent baseline work

- Native planner sources are frozen from canonical committed blobs: 65 ROS
  planner/notice files plus 145 global PCT/license files. Eight hash-checked
  Foxy/interface adaptations are explicit and reconstructible without sibling
  reads. No new planner optimization behavior is introduced.
- gpu5070ti has the existing Isaac Lab environment, native run/asset roots and
  Podman Foxy image. The initial docker/default-PATH probe did not cover them.
- Eight existing bridge transport tests passed in the actual Python 3.8.10 /
  rclpy Foxy container with network=none and read-only source. This includes the
  earlier skipped ROS dual-cloud test. They do not constitute a new Isaac run.
- The native_full02 runner was found in the immutable layered-review archive
  with the exact recorded source hash. runner_delta.diff shows the current
  committed runner adds recording-camera intrinsics/pose logs and changes
  capture cadence. This is not a fresh runtime parity result; changed render
  scheduling and new recording checks still require a bounded episode test.

## Final acceptance: round 5

After the third correction request, the lead inspected the changed transition
branches and independently reran both suites. Round5.json, round5_owned.log
and round5_lead.log record 37 executor tests plus 21 lead fault/order tests,
all passing; hashes remained unchanged during the run. The executor's separate
checks/checks_20260916T142630Z/ also records successful compilation and tests.

The exact final code passed the same 58 tests under actual Python 3.8.10 in
the existing 5070 Ti Foxy image. Evidence: python38_20260916T142710Z/.
Input hashes matched before and after execution, local source did not change,
and the isolated container was removed. Source_snapshot/ preserves the tested
core and tests. This was a CPU-only, network-isolated test run without Isaac,
policy execution, model calls or robot interfaces.

Final core.py SHA-256:
0fe9addf9f2901b38728b21e3e12485a14cf99dded989e6684dd8475397bef96.
Final test_core.py SHA-256:
9050d0932aa7ee4c675840c49d77d2dd446324b51dc479b33a14c958ed661b4d.
See FINAL_ACCEPTANCE.json for the complete final source hash manifest.

Accepted scope:

- One command owner, correlated immutable identities, idempotent submission,
  replacement after confirmed stopping, and stale/reordered reply handling.
- Tested uncertainty, exception, reentrant/concurrent admission, timeout,
  map-change, freshness and contradictory-response behavior.
- An explicit backend port whose unconfigured default refuses execution.

The failed rounds remain visible. The common defect was treating every reply
as an independent state assignment, without preserving prior acceptance,
execution or stopping evidence. Review therefore covered transition order,
callback reentry and possible side effects rather than only isolated API
happy paths. Future adapters must retain those invariants.

## Contract assumptions and next integration gate

- Backend calls return promptly with a bounded acknowledgement or pending/
  uncertain outcome. The service lock is not a substitute for an asynchronous
  ROS adapter and cannot interrupt an indefinitely blocking backend call.
- Arrival/stopped/cancelled feedback must already prove correlated command
  quiescence. These unit tests do not establish actual robot stopping.
- Map invalidation latches unresolved ownership; its caller must also issue
  cancellation/hold. check_timeout is caller-driven. No independent watchdog
  or timer loop is supplied by this core.
- The typed core is an internal interface. A future external transport must
  validate its wire schema, correlate acknowledgements at the command consumer,
  and prevent alternate raw-control/parameter paths.
- Bind the actual PCT planner and SCAN path/acceptance/stop feedback, then run
  two spatial goals in one continuous Isaac episode with unchanged robot and
  policy history. Freeze scene/map/configuration and resolve the runner's
  recording changes before that run.

Implementation, lead acceptance and commit status are separate: the bounded
contract is accepted; the full task is open; nothing was staged or committed.
