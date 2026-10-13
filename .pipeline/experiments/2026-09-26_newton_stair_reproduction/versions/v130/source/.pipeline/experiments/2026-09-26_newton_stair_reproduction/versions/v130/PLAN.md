# v130: bind reference admission search to the due measured body origin

Parent: frozen v129, original control v114. Route admission currently consults
start_pt_ before the first local plan sets it, and reuses a previous local
trajectory start on recovery. A real native callback/AStar probe reproduces
wrong search centers for stale/nonfinite prior state and due-body clock cases.

Change only new-reference query context: drain/apply original due FSM odometry
on valid route entry, pass its measured origin explicitly to goal-neighborhood
checking, and retain the old prepared start for existing local-replan callers.
The legacy path callback without odometry may use its finite path origin. No
source stamp is renewed; a one-nanosecond future pose must remain queued until
due. No waypoint, goal, support/collision rule, threshold, optimizer, retry or
timeout changes. Unknown map must still reject every probe route.

Owned behavior: scan_replan_fsm.cpp and its private helper declaration. Add an
explicit-start overload rather than mutating unrelated local PVA/rollback state.
Actual installed native callback tests must move from0/4 to4/4 correct origins
while preserving unknown-map rejection and source-time ordering. Then validate
actual physics; the origin witness alone does not establish mission reliability.
