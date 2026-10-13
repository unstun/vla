# v135 preparation: global/local support-map consistency

Parent: v134, which failed all three fixed pilots after about 0.8 m without falls.
Do not adopt it. Its original static floor-gap defect is independently reproduced,
but broad coverage veto prevents the existing PCT reference from being followed.

One proposed change: add the identical negative coverage constraint to a copy of
the original PCT traversal-cost tensor, recomputing only affected cost gradients.
All elevations, physics, sensor/static support payloads and native v134 checks
remain unchanged. Native packages may reuse verified v134 installed bytes.
Global PCT has no body yaw; its conservative clearance encloses both local
cylinders (0.35 m radius + 0.18 m offset). This is a proposed static-map input
change, not yet a frozen runtime or adopted result.

First gate: real installed PCT must find a route for the original start/goal,
with all original native safety checks retained. Record old/new paths and mask
intersections. A failed route-feasibility gate prevents physical deployment.
Then captured geometry/host/graph checks and the declared fixed physical pilots
and six-per-arm comparison. Every failure is retained on gpu5070ti.
