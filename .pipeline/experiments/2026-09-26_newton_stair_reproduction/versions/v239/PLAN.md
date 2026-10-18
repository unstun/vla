# v239: cooperative input processing in native A*

Parent: frozen v238. One native source file changes. The full continuous-clock
109–114.5s replay exposed a second starvation producer: a 177ms optimizer-local
A* plus a 54ms retry aged cloud evidence to0.3526s while the measured body
remained fresh and the seed/body positions were identical. v238 alone is not
zero-emergency qualified.

During a long search, poll the existing ordered input drain at20ms intervals.
If the adopted map revision, source observation or sliding origin changes,
return ordinary SEARCH_ERR with an empty result. The existing bounded native
retry starts a new round/open set. Never combine old scores with new map bytes.
The original200ms total budget and all geometry/freshness/goal/PVA/dynamic/
publication/stop rules remain unchanged. No cross-module connector/state machine.

path_searching is a static archive: rebuild bspline_opt, scan_planner, controller
and plugin consumers, including test executables. Verify actual installed
symbol strings/linked libraries; an archive-only rebuild is not runtime proof.

Validate the original141 recorded times/stair controls, existing native cases,
and two real-clock due-message window arms with emergency and spline-coverage
metrics. Original body movement remains recorded; no new physics/PD/video claim.
Keep v232/v233 selected and all predecessor source/install/results immutable.
