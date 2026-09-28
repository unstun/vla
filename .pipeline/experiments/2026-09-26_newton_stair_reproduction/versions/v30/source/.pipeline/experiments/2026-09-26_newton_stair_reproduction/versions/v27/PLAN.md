# v27: simplify a verified native seed using OMPL's direct-motion branch

Stage: experiment + analysis. Parent: v26. One native initialization change.

The actual v26 stopped-state replay at30.005138397s retains189 original scans
and the actual measured pose. With a fresh delivered pose and fixed replay
clock, the start, target and full direct segment are free, but the successful
81-vertex native AStar seed begins with a backwards detour. The initialized
curve fails optimization in both existing height modes. Therefore solving only
the separately recorded hold/freshness loop would not repair this state.

Reuse the deterministic direct front-to-back motion check in OMPL1.7.0
PathSimplifier::reduceVertices, pinned commit
eabb4d0f825666e4553a2ec0ecb9c7a5a33637dd, lines141-150. Retain mandatory native
AStar success, endpoint identity and every original edge check. Only afterward,
when GridMap::collisionFreeSegment verifies the entire exact endpoint connector,
replace intermediate vertices with those exact endpoints. On any blocked or
unknown connector keep the original path. No random shortcut loop is imported.

The existing segment predicate samples both endpoints and at most half a voxel
apart with the actual double-cylinder, raw occupancy, body reference, terrain
and freshness checks. Keep original arc-length sampling, boundary PVA fitting,
height/fixed-height optimization, timing, minimum cruise, dynamics and complete
final-curve validation. A valid seed is not authorization to publish a curve.

This does not change emergency hold/controller behavior, executor scheduling,
footprint, perception, unknown policy, map, speed or PD thresholds. Review those
open failures separately. Validate the new captured-state red/green twice,
previous nine continuations, unchanged eight unmapped cases and blocked/stale
controls. Freeze source/build before any new historical full-route physics run.
