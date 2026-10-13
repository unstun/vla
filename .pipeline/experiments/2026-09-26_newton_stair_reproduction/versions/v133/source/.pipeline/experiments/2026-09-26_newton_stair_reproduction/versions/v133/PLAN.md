# v133: refresh arrived inputs between search and reference fallback

Parent frozen diagnostic v132; original control v114. Actual v132physics
records3nonfinite sample0headings after147-168ms searches and2fallback failures
with observations older than250ms. The original helper drains inputs before
search but not between search and its fallback queries.

Add one guarded call to existing refreshSensorInputs after unsuccessful goal
neighborhood search, before walking the reference. This also applies to local
reference fallback callers. It does not retry search, renew stamps, change
geometry, skip collisions, relax any deadline or increase the inherited budget.
Missing fresh input and one-nanosecond future input must remain invalid.

Actual installed FSM/helper/map/queued-body regression uses a controlled search
failure that advances ROS time120ms. Original drops the route despite already
queued newly-due body data. Candidate must apply that due data and admit the
reference, while absent data and a1ns-future pose still fail. The search is a
fixture stub; physical pilots/repeats remain separate mandatory evidence.

Build, component, host and real-graph checks; freeze; then three bounded
diagnostic pilots. Complete all three navigation outcomes. Do not start another
full comparison unless all three arrive without falls; retain every failure. Diagnostic
V132_REFERENCE_ADMISSION log format remains in the source and is version-bound
by this manifest. Full acceptance still requires repeated actual navigation;
previous v128/v131failed comparisons remain immutable and unaccepted.
