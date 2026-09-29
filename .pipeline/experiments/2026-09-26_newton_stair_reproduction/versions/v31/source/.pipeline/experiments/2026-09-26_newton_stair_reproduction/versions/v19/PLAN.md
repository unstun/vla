# v19: retain original PCT elevation precision for selected terrain

Stage: experiment + analysis. Parent: v18. One logical data-interface repair.

At PCT cell [26,133], original float32 ground 0.41728198528289795 was stored as
float16 0.417236328125. Its 45.657 micrometre downward error flips 32 recorded
floor endpoints from inside to outside the existing 0.05 m classification band.
The native v18 189-scan replay is blocked at its previous endpoint; replacing
only the selected published heights with original generation precision yields
an accepted 0.298 m continuation, with PVA/full-curve and negative gates intact.

Use the archived original float32 NPZ, SHA
9adbbaf3754fc1a488ada560775407d4c684d57e19a6caea7075fa907b5c0c2d.
Require all five channels to round exactly to the pinned production pickle,
and require identical metadata before using its heights. Keep the original
float16 map for selection, deduplication, costs and the global PCT planner.
Only the same 86775 selected ground heights change. XY and cost bytes, the
0.05 m classification band, body envelope, nonterrain history and all safety
checks remain unchanged. The rejected raw-cost extension is not included.

The original tracking_physical publisher contract remains byte-identical.
Flat-scene publishers are unaffected. Opt in explicitly at the Building launch;
missing/mismatched original precision data must fail, not silently fall back.

Validation: original endpoint red/green evidence; paired-source rejection tests;
unchanged selection/cost and original physical-ground payload; native 189-scan
continuation plus stale/out-of-map/no-progress negatives; old 66/67 inputs with
new published ground; then actual production-input Building physics.
