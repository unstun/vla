# v222 design

Use ../10-17-pct-scan-traversability/design.md as the shared contract. This child starts from tested v221 and adds typed local rejection witnesses, bounded map/route-bound constraint memory and actual next-search changes.

The implementation source is a new immutable-version overlay under versions/v222; parent snapshots are references, never editing targets. Preserve native source-age and command admission separately from global static feasibility.

Actual implementation: frozen v230, composed from validated v229. The original
v222 designation was reserved before intervening fixes. See v230/PLAN.md and
v230/RESULTS.md for the implemented contract and component/recorded gate.
