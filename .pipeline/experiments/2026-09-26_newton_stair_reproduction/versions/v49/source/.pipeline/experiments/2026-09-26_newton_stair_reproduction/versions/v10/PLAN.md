# v10: separate physical ground evidence from traversability scores

Parent: frozen v8. v9 is retained as a rejected diagnostic configuration because
it clears a measured low box. Stage: experiment + analysis. Repair authorized.

One behavior change: raw LiDAR return classification uses the delivered PCT
ground elevations before step scoring, while motion feasibility continues to
use the scored support map. A missing/invalid scoring neighborhood must not
change a positively matching ground return into a historical nonterrain hit.

Reuse the existing `selectedGroundReturn` function, unchanged 0.05 m band,
original cost-selected PCT ground bytes, and existing native ray occupancy.
Keep all unknown/height/layer/obstacle-history guards, the v8 collision envelope
and the minimum planned cruise speed. No obstacle labels, truth mesh, extra
clearance heuristic or forced history clearing is introduced.

Source reference: pinned ETH StepFilter keeps `elevation` intact and writes
`step_height` / traversability as separate layers. The local representation
adapts this separation to existing `TerrainSnapshot` structures; it is not an
import of the upstream ROS node.

Owned source: new native candidate `scan48_ground_evidence_v10`, changing only
`grid_map.h` (separate ground snapshot) and `scan_reactive_grid_methods.inc`
(store valid unscored ground and use it for return classification). Invalid
new ground input must invalidate the classification snapshot. Frozen v8/v9
and original archived runtime remain unchanged.

Acceptance: original native continuation replay, meaningful sparse-support
classification regression, complete measured obstacle suite including the
low box, and full-curve/PVA/dynamic checks. Physical validation follows only
if these conditions pass. Terminal-status reporting remains a separate change.
