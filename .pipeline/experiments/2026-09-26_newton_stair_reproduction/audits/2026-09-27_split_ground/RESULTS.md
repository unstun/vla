# Diagnostic result


## Later acceptance-semantics audit

The new-free overlap counts remain factual, but the earlier blanket safety
interpretation was too strong. The original selected baseline itself permits
114/489 query locations whose double-cylinder envelope overlaps the known
0.13 m low box, and 41/489 in its near-wall variant. It already includes 63 or
28 low-box top support points (cost below 20) and labels many side returns as
terrain via the existing riser rule. Thus neither baseline nor candidate
implements a semantic "all independent boxes must be avoided" policy.

The user was asked to choose geometric traversability versus mandatory
independent-box avoidance. That choice is pending. Envelope/terrain overlap is
not proof of actual rigid-body collision or successful stepping. The plain
expanded-ground and plain split-ground candidates still did not pass the
actual v19 continuation; no production acceptance follows from this correction.
The surface-only candidate has a passing recorded continuation, but still
requires the separate input contracts, obstacle regression and physical run.
