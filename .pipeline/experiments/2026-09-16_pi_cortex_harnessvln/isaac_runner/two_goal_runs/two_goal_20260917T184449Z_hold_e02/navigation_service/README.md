# Persistent Navigation Service Contract

This directory contains the bounded P2A lifecycle service for HarnessVLN to
PCT/SCAN navigation.  It is a Python 3.8-compatible state-machine contract, not
a ROS action server and not an Isaac or robot run.

The core service owns:

- explicit `run_id`, epoch, request, goal, route and command identities;
- boundary validation for finite metric targets, map/evidence revision,
  localization validity and evidence freshness;
- one active command owner;
- idempotent request replay and same-ID/different-payload rejection;
- cancel-then-confirm-stop-then-submit replacement ordering;
- submit-side synchronous callback correlation plus delayed submit
  acknowledgement handling;
- stale-feedback and old-epoch rejection;
- explicit unresolved outcomes for uncertain submit/stop, timeout, backend
  loss and map invalidation;
- monotonic structured events correlated to the active goal and route.

Submit/stop terms:

- `rejected` means initial admission had no backend effect.  A contradictory
  late rejection after acceptance or progress is ignored and does not release
  command ownership.
- `arrived`, `stopped` and `cancelled` are accepted only as confirmed terminal
  feedback for the correlated command.  They are not inferred from proximity,
  model prose or route publication.
- `invalidate_map` marks the active command unresolved under the new map state;
  it does not itself stop motion.  The caller must request cancellation/hold
  through `cancel_active` or another backend stop path.  No independent
  watchdog/timer is implemented in this contract.

The default `NavigationBackendPort` raises `navigation_backend_unavailable`.
Tests inject a manual backend double so contract behavior can be checked without
fabricating production success.

Backend-port assumption:

- `plan_route`, `submit_route` and `stop` are synchronous boundary calls that
  must return a bounded acknowledgement, rejection or pending/uncertain outcome
  promptly.
- A backend method may synchronously call back into the service; this is why the
  service uses a reentrant lock plus a separate admission guard.
- A backend method must not block indefinitely waiting for a callback from
  another thread while the service lock is held.  Such an adapter must return
  `pending` or `uncertain` and deliver correlated feedback/acknowledgement
  later.
- This contract does not claim realtime cancellation with an unbounded blocking
  backend.
- The current implementation is contract-only Python code and is not ROS/Isaac
  integration evidence.

Run:

```sh
python3 -m unittest -v test_core.py
python3 verify.py
```
