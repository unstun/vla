# v232: contain local-planning exceptions and close native-process failures

Parent navigation: frozen v230 (e9f8bec0). Failure reference: v231 physical
attempt near46.686s. Dr Sun authorizes these four fixes and offline tests only.
Local source is authoritative; gpu5070ti is a build/test execution copy.

1. Stop rebound objective evaluation immediately after a native error/rebound
   flag; preserve solver cancellation even for a zero interim gradient.
2. Soft environmental samples use finite local/neighbor geometry or finite
   measured yaw when the hard-check heading expires. Keep analytic derivatives
   consistent with the selected direction. Invalid geometry fails the solve;
   no NaN enters EnvironmentalField. Hard freshness/selected-support rules stay.
3. Catch within optimizer callbacks/entries, FSM timers/input callbacks, map
   callbacks and the NativeWorker query service. Failed work reports failure,
   invalidates partial native state and releases publication leases. Query
   errors return unavailable without partial verdicts. Catch unknown exceptions
   as well; no exception may escape an owned ROS callback into Foxy spin.
4. Use launch OnProcessExit for actual critical children, not log parsing.
   Atomically bind failure receipts to run/epoch, retain the mission bridge,
   fail the active job and close the existing matching FAILED finish request.
   Guard late action acceptance and cleanup errors. Detect launch/bridge exit
   at the outer graph supervisor too. Intentional shutdown is not a fault.

Expected changes: bspline optimizer/helper and environmental tests; a small
shared callback boundary, FSM/map/NativeWorker registration and callback tests;
navigation launch/process receipt, MissionBridge and mission/child-exit tests;
version-owned graph supervisor/finish helper. No RL, geometry, hard threshold,
normal scheduling/retry or physical-run changes. No new cross-module recovery
protocol. Preserve frozen parents and earlier failed test attempts.

First reproduce stale stationary-tail and aborted-objective failures against
parent code. Then run affected nine-package tests, actual two-thread Foxy
callback exception tests, real SIGABRT child with live launch parent and matching
FAILED finish closure, unknown/stale/epoch/late-accept/shutdown controls, original
126324+3 verdict/predicate parity and installed Building admission. Return source
inventories, logs/XML and compact receipts; keep captures/build caches remote.
Freeze only after the offline gate passes. No physical simulation or commit is
included in this request.
