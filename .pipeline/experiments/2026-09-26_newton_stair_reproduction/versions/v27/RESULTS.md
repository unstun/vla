# v27 physical trial: native crash, full route incomplete

All component results in COMPONENT_RESULTS.md remain valid. The live historical
full-route attempt `v27_historical_full01` reached about13.24s physics before
native SCAN reported Segmentation fault (ros2run exit245). No arrival, completed
route, final PD acceptance or verified Linux state copyback. The native process
failure caused container exit before tmpfs state copyback. Raw telemetry,22 sensor
captures, video states and logs remain preserved; no successful video was made.

The captured final seed269 is already a two-point native AStar recovery path;
that individual attempt did not enter v27's new simplification branch. This
alone does not exclude earlier execution-history effects. Saved-input bounds
replay reproduces abort at that captured seed, but no exact live crash stack
has yet been recorded. Native constraint counterexamples expose pre-existing
invalid intersection flags and empty-container propagation. A prior finite
constraint fix was lost when restoring the scan_04 optimizer. v28 is proposed,
not implemented. See the2026-09-28 archive handoff for continuation.
