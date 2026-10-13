# Focused Mac backend timing diagnosis

Stage: experiment + analysis. Dr Sun requested root causes of heartbeat_stale
and unstable30Hz. One logical change: observe backend callback, applied read,
HTTP serialization and Python GC spans. Parent v68; exact native v63 and v59
runtime/control/physics/safety. v69 is a display-only sibling. This package is
diagnostic and cannot be promoted to an accepted navigation repair.

Delegate every original method once, preserving its return value, exceptions,
messages and effects. Collect compact identity-bearing timing events in a
bounded memory buffer; a background writer periodically drains them outside
callback timing spans. Keep original body callback/error traces. Record both
wall and per-thread CPU time, callback heartbeat age and gate reason. A trace
cannot infer OS runnable wait without a scheduler trace; identify that boundary.

Rebuild/qualify exact frozen v63 in the original cached amd64 ROS image on Mac.
The original temporary cache is now unavailable. Regenerate the same Warp1.17
CPU model/raycast kernels through prepare_cache.py with zero physics steps,
then preload them as the v68 prepared retry did. No sensor deadline or physics
computation changes. Preserve the failed initial cache-helper import attempt. Keep original6CPU/
6GB limits, original factory/route/goal/yaw/configuration and every stop/freshness
rule. Freeze source and installed identity before the bounded90s diagnostic
trial. Earlier frozen versions and failed runs remain immutable. gpu5070ti is
busy and must not be used.

Temporary build/physics/archive data go to unique private/tmp; return compact
traces, analysis, hashes and a report. Verify owned-container shutdown and
archive integrity; remove only regenerable owned build products after analysis.
No new render or raw capture transfer into the repository. The tracing run is
not a performance improvement trial. If the intermittent fault does not recur,
report that and preserve the full trace rather than inventing a root cause.
