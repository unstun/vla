# Recorded replacement diagnostic

Actual native manager calls using original curve2366 start PVA and endpoint
produce the same accepted2.220781670746s curve under v147 and v151. Independent
original PVA/dynamic checks pass; v151 checks1116samples. The v151 actual FSM
reference path also finds an accepted1.831504979084s alternative,921samples,
with original boundary/dynamic checks. The total reference call takes188ms in
this cold, fixed-simulation-clock diagnostic. No real-time success is implied.

Thus the selected failure position is not shown to be a geometric dead end.
This probe does not restore the previous warm hint or asynchronous map batching.
The original sample-grid false clear and finite mission retry exhaustion remain
separate facts. We do not change retries to hide repeated safety stops.

Corrected reason: native verdict6 is UnknownObstacle, and voxel0 is unknown.
The earlier support-clearance wording was wrong. Original occupied/freshness
limits remain unchanged. v151 also changes warm-seed point counts indirectly;
this is recorded before further candidate attribution.
