# v18: preserve a fresh converged clock estimate across rejected observations

Stage: experiment + analysis. Parent: v17. One change in `scripts/clock_sync.py`.

Follow the already-pinned MAVROS a5979a5299775d9dd9ce1d57f9cfa1542c5259b9
sample-rejection semantics: a rejected timing sample does not renew or destroy
an otherwise valid converged estimate. Keep the existing 200 ms accepted-sample
TTL, 10 ms RTT/deviation limits and conservative timestamp uncertainty.
Invalidate on filter reset, transport/protocol error or responder change. Check
current convergence as well as the cached estimate. Separate last-observation
rejection from current synchronization validity in diagnostic output.

The actual v17 capture reproduces premature invalidation; five receive-loop
regressions include recorded data, expired/never-renewed cache, filter reset,
socket loss, identity and echo failures. Three tests fail on the parent and all
five pass on the candidate. The original stop also included a true TTL expiry;
this repair does not guarantee that physical stop cause will disappear.

No planner, ground source, robot envelope, velocity requirement, safety watchdog
or controller parameter changes. The raw-PCT-ground candidate is rejected after
a mapped low box near a wall exposed newly admitted envelope intersections.

Validation: frozen source identity, complete clock receive-loop regression,
then a bounded production-input Building physical trial with the same v17 native
build. Only physical route completion can establish navigation acceptance.
