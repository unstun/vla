# Local curve video and solve-time HTML

Stage: experiment + analysis. Dr Sun requested visible local planning curves in
the simulation video and an HTML plot of local planning computation time.
The v114 archive has zero Bspline events: the observer subscribes to the old
/planning/bspline rather than the native Nav2 /quad_0/planning/bspline topic.
Its seed captures are not the final optimized/published curves and must not be
used as a substitute. v116 changes recording only, using exact frozen v114 native
source/install/config/policy and original scene. Record final splines, safety,
cancellation and existing controller admission/command identities. Use a bounded
new physical run with its own identity; never relabel it as v114's prior run.

v117 will own display/report changes: native curves in a contrasting visible
style, original global route distinct, stale/cancelled curves cleared, actual
source trajectory IDs/times bound to frames, and a standalone offline HTML with
per-round wall computation times, success/failure marks,33.33ms budget, raw CSV,
and a synchronized video cursor. Keep scene/body states untouched. Plot solve
latency, not command period or FPS; do not smooth away spikes.

Execution is the authorized bounded Mac Newton simulation using its retained
Foxy ARM64 runtime. gpu5070ti is storage only. New raw/root bytes stay outside
the repository pending verified remote retention; local return is the review MP4,
HTML, small timing data and compact hash/provenance, expected under20MiB.
No robot actuation, changes to planning/control/safety, or subagents.
