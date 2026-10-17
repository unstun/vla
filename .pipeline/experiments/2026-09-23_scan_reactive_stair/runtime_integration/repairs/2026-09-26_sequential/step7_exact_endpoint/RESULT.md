# Exact endpoint consistency: native runtime result

The recorded failure is confirmed as the last edge after manager endpoint
replacement. The diagnostic has 75 nodes and rejects edge 74/sample 0; the
original lattice edge still passes. Replacing the endpoint shifts it by
0.023666 m and changes heading by -9.102862 degrees. At the unchanged previous
node, the new front query has UnknownSupport and the rear has UnknownObstacle.
See `TRACE_RESULT.json` and the preserved `scan24_endpoint_v1` raw log.

The scan_25 strict endpoint candidate passes eight local endpoint cases,
eight legacy native search/segment cases, eight Foxy endpoint cases, a full
Foxy build, and the 459-file installed identity gate. Independent review found
no blocker. The first Foxy fixture package failed before tests due to a
host-directory assumption in the test script; a fresh v2 package fixes only
that orchestration issue and passes with unchanged production source.

On exactly the same recorded inputs (manifest 9b72fee5...716589), scan_25 has
zero search failures, zero endpoint mismatches, zero seed-edge rejections and
162 checked seeds. The prior candidate had 179 seed-edge rejections and no
checked seed. Callback counts are not a timing comparison. The endpoint defect
is repaired at the actual native seed boundary, without freeing Unknown or
changing collision/terrain/height thresholds.

All 162 optimization attempts still fail before dynamic checks or the full
final spline gate. There are zero moving splines and no navigation success.
Fifty-eight attempts report an optimized curve collision within the initial
interval; the remaining attempts fail after rebound/restart processing. The
printed “First three control points” warning actually refers to sampled curve
collision at t <= ts, not three independent control-point occupancy tests.

The next isolated diagnosis (`step8_spline_seed`) captures the first replan's
safe seed, downsampled points, fitted/optimized controls, actual p/v/a boundary
residuals, solver termination and internal AStar endpoint adjustment phases.
Extra geometry/map comparisons run only after the original optimizer has
already failed and cannot affect acceptance. No source threshold or objective
is changed in that observer. Its cost is not runtime performance evidence.

Dr Sun explicitly authorized continued task-source synchronization and bounded
build/replay/simulation on gpu5070ti. The earlier automatic-review denial and
its resolution remain in `REMOTE_APPROVAL_BLOCK.json`. All code and returned
evidence are retained in local VLA; no physical robot or formal training runs.
