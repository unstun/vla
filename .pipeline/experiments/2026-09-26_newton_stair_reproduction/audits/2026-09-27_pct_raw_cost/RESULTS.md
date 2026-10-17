# PCT raw-cost ground candidate: rejected for production

The unmodified historical CPU generator was acquired from clean main commit
1cf45a1c12ca785ce533293302be09d51daf0ccb. Its SHA exactly matches the generator
receipt for the production Building map. Raw cost was observed at the function
return, without changing the source or its layer-simplification rule.

The original inflated cost, ground and ceiling channels match every float16
cell. Gradient channels differ in 795 cells by at most 0.0078125; they are not
replaced. The prospective payload retains all 86775 old selected points and adds
38718. It follows the existing height deduplication and minimum-cost propagation.
An independent review checked that inherited lower-cost surfaces have identical
stored ground heights; no cross-height association was observed in this map.

On the exact 189-scan failure, the candidate with v17 yields a native continuation
that passes boundary PVA and full-curve collision checks. This is a positive
component result, not sufficient qualification.

The mapped-object counterexample is decisive: a 13 cm box near a wall produces
16 newly free dense queries, including 13 inside the original double-cylinder
obstacle envelope. See ../2026-09-27_pct_ground_negatives/delta_review.json.
The mapped box, short wall and overhead center/front queries remain blocked,
and the original eight unmapped sensor cases retain their outcomes, but those
passes do not erase the new false-negative boundary. No production input was
changed, and no integration version adopts this candidate.

`connected_ground.py` is an unpromoted exploratory component-labeling prototype.
Its derived payload has not passed native obstacle regression; it is neither a
repair nor a certified replacement for the rejected raw-cost candidate.


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
