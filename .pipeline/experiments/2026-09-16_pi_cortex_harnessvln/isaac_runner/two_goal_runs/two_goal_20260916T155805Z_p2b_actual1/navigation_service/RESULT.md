# P2A Persistent Navigation Service Result

Status: implemented and locally validated as lifecycle/contract evidence only.
Round 1, round 2 and round 4 lead acceptance failed; all failure sets were
reproduced against the lead-owned adversarial suite, then fixed in this
directory.

## Changed Files

- `.gitignore`: ignores local Python bytecode caches in this owned directory.
- `README.md`: documents the bounded contract and run commands.
- `__init__.py`: exports the navigation-service types.
- `core.py`: typed persistent navigation lifecycle service with explicit backend
  port.
- `test_core.py`: regression tests with a trace backend and test-controlled
  clock.
- `verify.py`: compile/test runner that records raw logs, source SHA-256 and
  the lead-owned adversarial suite result.
- `checks/checks_*/*`: raw command logs and result manifests.

## Contract Implemented

`PersistentNavigationService` owns one active command owner for a run/epoch.  A
goal request carries a request ID, goal ID, validated metric target, map
epoch/revision and evidence snapshot.  The service validates finite coordinates,
frame/units, localization validity, map freshness and observation freshness
before route planning.

The backend is an explicit `NavigationBackendPort`.  The default port raises
`navigation_backend_unavailable`; tests use an injected trace backend.  There is
no fake backend default and no ROS/Isaac execution in this slice.

Lifecycle behavior:

- duplicate request ID plus identical payload is idempotent;
- duplicate request ID plus different payload is rejected;
- a second goal is blocked while command ownership is unresolved;
- replacement is stop request -> stop confirmation -> request revalidation ->
  submit;
- missing/uncertain stop acknowledgement retains owner and blocks replacement;
- stop/cancel/map-invalidation/timeout preserve the original immutable
  `BackendCommand` identity for later stop receipts;
- submit outcomes may be accepted, rejected, pending, uncertain or corrupt;
- submit `rejected` only releases a command that was genuinely awaiting initial
  admission and had no acceptance/progress evidence;
- pending submit requires a correlated delayed acknowledgement;
- corrupt/unknown submit outcomes and backend exceptions after possible
  submit/stop side effects retain unresolved ownership;
- malformed stop outcomes retain unresolved ownership;
- backend route-specific submit and stop replies must match the submitted route
  ID;
- synchronous submit-time callbacks are correlated because owner is installed
  before `submit_route`;
- synchronous failed feedback during submit is preserved as failure, not
  converted to success by a later submit return;
- synchronous stop callbacks cannot cause the outer stop return to erase a new
  command owner admitted by that callback;
- late accepted/progress/arrived feedback cannot satisfy a pending stop;
- late submit rejection cannot clear pending-stop ownership;
- late submit rejection cannot clear accepted/executing ownership without stop
  proof;
- failed execution feedback is not treated as proof that motion stopped;
- feedback sequence/status validation happens before any sequence mutation;
- timeout asks the backend to stop/hold and stays unresolved unless stop is
  explicitly confirmed;
- map invalidation is an explicit unresolved outcome and does not silently
  release command ownership;
- concurrent submissions are serialized by an admission lock.
- successful synchronous accepted/progress callbacks during submit merge with a
  valid accepted submit return as success instead of being reported as failure.

`arrived`, `stopped` and `cancelled` mean confirmed command quiescence for the
correlated command.  They are not inferred from route publication, proximity or
model text.

`invalidate_map` marks an active command unresolved but does not itself call
backend stop/hold.  A caller must request cancellation/hold after map
invalidation; no independent watchdog or timer loop is implemented in this
contract.

All emitted events carry monotonic sequence, run ID, epoch, kind, status and
goal/route correlation where applicable.  Terminal cause is stored as lifecycle
state, not inferred from model prose.

Backend-port assumption:

- `plan_route`, `submit_route` and `stop` are synchronous boundary calls that
  must return a bounded acknowledgement, rejection or pending/uncertain outcome
  promptly.
- Synchronous callbacks into the service are supported.
- A backend method must not block indefinitely waiting for another-thread
  callback while the service lock is held; it must return pending/uncertain and
  deliver correlated feedback later.
- This contract does not claim realtime cancellation with an unbounded blocking
  backend.

## Validation

Latest targeted check:

```text
python3 verify.py
```

Raw logs:

- `checks/checks_*/00_compileall.log`
- `checks/checks_*/01_unittest.log`
- `checks/checks_*/02_lead_adversarial.log`
- `checks/checks_*/result.json`

Lead round 1 failed evidence was left intact under the lead-owned acceptance
directory:

- `.trellis/tasks/09-16-emos-harnessvln-reimplementation/research/acceptance/round1.log`
- `.trellis/tasks/09-16-emos-harnessvln-reimplementation/research/acceptance/round1.json`

Lead round 2 failed evidence was also left intact:

- `.trellis/tasks/09-16-emos-harnessvln-reimplementation/research/acceptance/round2.log`
- `.trellis/tasks/09-16-emos-harnessvln-reimplementation/research/acceptance/round2.json`

Lead round 4 failed evidence was also left intact:

- `.trellis/tasks/09-16-emos-harnessvln-reimplementation/research/acceptance/round4.log`
- `.trellis/tasks/09-16-emos-harnessvln-reimplementation/research/acceptance/round4.json`

`result.json` records:

```text
compileall returncode 0
unittest returncode 0
lead_adversarial returncode 0
37 owned tests ran OK
21 lead adversarial tests ran OK
```

Source hashes are machine-recorded in each `checks/checks_*/result.json`; use
the newest checks directory for the final run.

Regression coverage includes two-goal sequencing, replacement ordering,
missing stop acknowledgement, stale feedback, delayed acknowledgement,
late feedback during pending stop, failed execution without stop receipt,
synchronous failed callback during submit, original command identity after map
change, evidence expiry during route planning, ordinary OSError/ConnectionError
after side effects, malformed submit/stop replies, route-ID mismatched replies,
reentrant admission during planning, stop callbacks that admit a new owner,
contradictory rejection after acceptance/progress, successful synchronous
accepted/progress callbacks during submit, BackendUnavailable after submit
dispatch, duplicate IDs, timeout stop requests, backend unavailable/failure,
stale map/evidence, invalid localization, invalid units, non-finite/future
timestamps, invalid freshness configuration and non-finite target coordinates.
The trace backend asserts no second submit occurs before first stop
acknowledgement.

## Remaining Integration Gaps

- No ROS2 action/service transport is implemented yet.
- No real PCT route planner call is bound to `plan_route`.
- No SCAN `initial_path` publication or acknowledgement extension is bound to
  `submit_route`.
- No Isaac Lab process, Podman/Foxy runtime, simulator sensor stream or Lite3
  motion was launched.
- No physical robot actuation or receive-only hardware proof was attempted.
- Arrival/failure feedback is only contract-level injected test data; it is not
  measured robot or simulator feedback.

Strongest justified claim: validated local lifecycle contract for a future
PCT/SCAN backend adapter.  This is not integrated navigation and not runtime
simulation evidence.
