# v136: service pending mission messages at native work boundaries

Host parent v135; compiled parent v134 (v135 reused its exact native install).
The v135 fixed pilots finish2/3 with no falls; the third fails at25.399m with an
upright body after seven attempts. Do not start its formal comparison.

Observed dispatch defect: generation4 arrives at37.635944s and its controller
times out at39.654835s, but the FSM only accepts it at40.744236s, then processes
the already-issued cancellation. Generation3 has no FSM acknowledgment before
the depth-one route queue is replaced. Bounded callbacks reach778ms while the
serialized work group keeps doing old-plan work. Old measured-stop proof is
still required; this is delayed processing, not absent physical stillness.

One change: at each FSM work boundary, consume original queued cancellation
messages before route messages through the existing callbacks. Bounds match
the existing DDS depths10/1. All original identity, cancellation high-water,
source freshness and geometry rules remain. Keep replacement routes queued
while EMERGENCY_STOP is exiting so the old exit cannot erase the new target.
Transport errors fail the native worker closed. No timeout, retry-count or
physical-stop threshold changes. No new threads or concurrent FSM mutation.

Test the actual installed FSM with queued DDS messages and explicit timer ticks:
old version leaves them queued, new version processes them; cancellation beats
a queued canceled route; a pending replacement survives the old emergency exit.
Then build/test, freeze, run three fixed physical pilots. Only3/3 arrivals/no
falls authorize six fresh runs per arm, comparing old nativev134 (v135 behavior)
withv136 on the same v136 host and same v135 global map. All failures remain.
The earlier v133 original-map comparisons stay separate. Main task stays open.
