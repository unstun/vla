# v138: apply the global support envelope in local planning too

Parent v137. Three pilots finish2/3without falls; the third stops upright at
(7.885,6.511,4.828) and accepts all replacement references but generates no new
safe curve. Keep that failed batch and do not start its formal comparison.

Direct recorded-curve witness: the optimizer's accepted curve is rejected at
t0.878170478. Its body is(7.684185,6.569040,4.828249), while the controller's
0.8s lookahead yaw is-2.74771449. The front cylinder is at(7.517968,6.499961)
and the original support-gap mask vetoes it. Seed/control-polygon tangent checks
and the final lookahead orientation are different; repeated cold smoothing cuts
back into the prohibited footprint. This is a geometric, not freshness failure.

One conservative addition: local common collision queries also check the body
center against the same yaw-independent support envelope used by global PCT,
radius0.35+abs(0.18)=0.53m. Preserve the existing two-cylinder support veto and
all live occupancy, height, identity/freshness and physical-stop checks. The
addition can only reject. Global map bytes, physics, policy and deadlines stay
unchanged. It makes unsafe turn-clearance visible to seed/optimizer checks
before final lookahead validation. No optimizer or controller gain is changed.

The already trapped v137 stop position is inside that conservative envelope;
this repair must prevent entering it in a fresh episode. It is not a claim of
escaping an arbitrary already-invalid pose. Validate actual native queries on
recorded geometry, including old permitted/new blocked turn-clearance cases,
unchanged clear cases and preservation of all old rejects; then fixed pilots
and, only after3/3arrivals/no falls, six fresh trials per arm. Baseline nativev137,
candidatev138, same v135 global map and v138 host. All work on gpu5070ti.
