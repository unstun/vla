# Exact endpoints for collision-repair guidance

The same-time step18 diagnostic established a three-node, fully checked route
between the original failed retry endpoints at control columns 250 and 252.
Default endpoint adjustment returned INIT_ERR. The initial proxy case remained
unreachable under strict search and is not evidence for changing initialization.

scan31 changes only two actual repair calls: initControlPoints(false) passes
exact_endpoint=true, while its first_init=true behavior remains default;
check_collision_and_rebound also passes true, including merged-segment retries.
Control-polygon segmentation, stored endpoints, assignments, gradients, weights,
retry bounds, full trajectory checks and map predicates are unchanged.

The native regression extracts the full initControlPoints and full rebound
collision detector, besides the earlier assignment block. Ten existing validity
cases plus six call-mode cases cover initial/retry/callback/merged/failure/reuse
behavior. The merge case locks exactly CP1→CP4 followed by CP1→CP8 and strict mode
for both calls. Search/map/logger are doubles; no graph or full optimizer claim.
Old scan30 fails the five predeclared repair-mode cases and passes eleven others;
scan31 passes all sixteen local cases. Independent review found no production
blocker; its merge assertion feedback was incorporated into local v2 and the
remote package. Earlier v1 packages remain preserved.

Remote native tests, full build and paired real optimizer replay are pending.
Only a complete-gate accepted curve can qualify a new live candidate.

Remote Foxy native regression completed: all 16 cases pass with the strengthened
merge-endpoint fixture. Full build is in progress.

Full Foxy build and 462-file install identity pass. Fresh replay completes with
45 checked seeds, zero moving publication and no search time cap. The first
plan's full-curve collision now generates 3 paired constraints, then 6. Later
solver callbacks perform 14 rebound cancellations before an empty valid-direction
repair sets STOP_FOR_ERROR. This is progress beyond the zero-constraint failure,
not an accepted curve. First two complete curve checks still report the same
collision time and squared control norm; later returned geometry needs inspection.

Next diagnostic checks the actual curve only after original optimizer failure,
and records the final failed control-polygon segment/route. It distinguishes a
remaining true curve collision from an overly conservative control-point proxy.
The failure guard itself remains unchanged.

Old accepted-input regression completed: one accepted moving cubic; controls
and knots exactly match the prior accepted scan28 result. Complete curve gates
therefore remain compatible with that positive input.
