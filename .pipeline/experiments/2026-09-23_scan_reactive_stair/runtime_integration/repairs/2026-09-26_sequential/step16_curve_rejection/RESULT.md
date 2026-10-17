# First rejected curve: position and execution heading

The scan29 observer runs only after the original full-curve rejection. Its
full Foxy build and463-file identity pass. The fresh-input replay retains zero
moving publication. All four body/clock pairs equal5.56999988s; this is a frozen
recorded-input query comparison, not physical traversal or a timing benchmark.

| Curve | First collision | Seed distance | Heading change | Original footprint reason |
|---|---:|---:|---:|---|
| Timed initial |51.077484s |0.044674mm |16.672965deg |Front WrongHeight |
| Final optimized |46.347717s |1.048976mm |2.056527deg |Rear UnknownSupport |

The timed initial point clears when only its yaw is replaced by the parent
seed-edge yaw; projection onto that edge with actual curve yaw remains blocked.
This isolates execution heading at that first failure. The final point clears
either when projected to the seed with actual yaw, or when kept in place with
parent yaw. Its position and orientation jointly cross a support boundary.
Neither substitution has been shown to clear the complete curve and neither
is an execution-compatible production fix. Unknown and support limits remain.

The initial curve is already blocked, so this is not solely damage introduced
by optimization. Both curves satisfy original derivative limits. The optimizer
coarse prefix check returns success while the final full checker rejects. The
first final collision lies at58.55percent of duration, inside the checked prefix;
coarse spacing, not just omitted final third, is therefore relevant.

GEOMETRY.json contains69 seed vertices,426 samples and428 controls/432 knots for
each curve. analyze_probe.py removes complete interleaved ROS log records only
to rejoin buffered numeric stdout; validates every index and count, then checks
independent de Boor reconstruction against native collision positions with
residual below7e-13m. Original logs are untouched. RESULT.json pins both hashes.

Next isolated repair: use the existing complete curve helper inside rebound
and refinement acceptance, preserving execution heading and budgets, and record
whether existing collision retries add valid constraints. This can correct
acceptance semantics without establishing successful geometry repair. Do not
promote a failed control-polygon initialization to unconditional curve failure:
the same proxy initialization error occurs on old data whose curve is clear.
