# Per-control route projection after failed plane guidance

The recorded scan31 failure has seven folded internal controls and a checked
two-node route, with no mathematical plane/route intersections in this specific
snapshot. scan32 adds a limited callback fallback when the original native
plane search finds no finite intersection in a repair segment. That finder is
not an exhaustive enumerator; this condition is not a general proof of absence.

Each candidate is the deterministic closest point on a finite route whose
endpoints match the original control columns. Query the candidate with that
control's own heading, then reuse the original base-point ray and paired unit
constraint write. No fallback direction is copied to an unchecked or rejected
control. Initial guidance and ordinary plane/propagation behavior remain,
along with all finite/zero guards, clearance cost, gradients, weights, retries,
Unknown/height rules and complete curve/PVA/dynamic gates.

Native fixture uses the actual recorded 428-control geometry and two-node route
with a synthetic occupancy boundary. The old source fails the two predeclared
all-clear/mixed-clear projection positives and passes eighteen other cases.
Final local scan32 passes 21 cases: the previous sixteen, recorded projection,
own-heading Unknown, endpoint mismatch, mixed six-clear/one-Unknown, and the
new pure projection geometry group. Existing ordinary-plane cases require
exactly one pair per control, guarding against extra fallback writes. Mixed
case requires CP252 and both endpoints to remain empty.

Independent review found no production blocker and requested the mixed case,
which is incorporated into local v2 and the remote package. Early v1 evidence
is retained. Map/search/logger in these fixtures are doubles; a passing unit
case is not a real-map anchor or final curve result. Full build and original
optimizer replay are separate gates. Original clearance may push past the
nearest point, so inspect final geometry rather than promoting pair counts.

Pinned Foxy native regression also passes all 21 final groups. Source build
is running; real-map projection availability is not inferred from the fixture.

Full build and 462-file identity pass. The real-map first folded segment has
six clear targets and six actual paired writes. It advances past the prior
empty-direction stop, but the first solve reaches 21 rebound cancellations and
returns failure under the unchanged bound. Fresh replay has 40 checked seeds
and zero moving publication. Old positive replay retains exactly the same
accepted controls/knots. This qualifies the constrained direction generation,
not complete stair planning or live navigation.

Next work moves to explicit local-target proposal/commit and bounded shorter
stoppable prefixes on the same accepted reference route, keeping global goal
and complete trajectory gates. This is a separate policy change; no horizon or
iteration-limit tuning is mixed into projection evidence.
