# v174: reject degenerate PCT optimization without aborting the process

Stage: experiment and analysis. Parentv172. Its local route used measured-progress
renewal correctly and reached the final goal region, but PCT aborted on the final
replan: GPMPOptimizer::SubSamplePath assertedpath.size()>1. The actual native A*
route had one point. Subsequent RPCs found a dead worker; this is not an arrival.

Before native front/back access and optimizer subsampling, reject paths withfewer
than2points. Keep original no-route semantics, geometry, optimizer behavior and
safety gates. The existing explicit same-owner/same-mission reference reuse may
then recover after measuredstop. Never fabricate a two-point route or success.
Test old native process abort against the captured map/pose; new actual worker
must reject near-goal and identical endpoints, still plan the original fullroute,
and reject a later singleton without returning a stale optimizerresult. Cover
both native optimizer modes. Require graph and localfullroute beforeLinuxrepeats.

The guard-only candidate exposed a coupled request-lifecycle defect: Search only
reset node scores/parents when its previous result was nonempty. An identical-
endpoint query leaves an empty result and zero-cost goal node; the next otherwise
valid full request fails. The unchanged fresh planner accepts649points. Reset
scores and parent links on every search, retaining all static map costs/heights.
The paired worker regression must now pass after both singleton and empty results.
Guard-only failed build/source identity are preserved underresults/guard_only_failure.
