# v153 bounded idempotent Mac applied-state transport

Stage: experiment + analysis. Host parent v151, native v151 unchanged. This
version changes only host transport recovery and records every attempt.
v151Mac trials02/03failed when the server eventually received/wrote the exact
snapshot but the client's100ms request timed out. Third-trial cgroup telemetry
shows no navigation-period CPU quota throttling or OOM. Server handling of the
failed snapshot itself took0.248ms; the delay preceded receipt.

Keep100ms send/receive timeouts. Retry the exact serialized bytes at most twice
on a new ZeroMQ REQ socket; the synchronous physics caller advances no step
between attempts. Server permits only the current sequence and exact same hash
as an idempotent read-back, rechecking original source freshness and reader.
Old sequences, altered bytes, wrong run/epoch and stale source still reject.
Never refresh source time, claim an unreceived ACK, or reinterpret copyback
mismatch as success. All retries failing still terminate the trial.

Tests exercise actual local sockets: delayed reply after commit; exact duplicate
with one file write; changed/old/stale/wrong identity rejection; all replies
missing; unmodified clean request. Then freeze host and run original-start
physical trials, retaining every failure separately from navigation outcomes.
The native collision-sampling candidate is not accepted by transport success.
