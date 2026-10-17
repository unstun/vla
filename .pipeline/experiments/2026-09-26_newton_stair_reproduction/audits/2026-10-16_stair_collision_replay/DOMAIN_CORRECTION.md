# Traversability-region display correction

The first movie showed PCT cost dots and two SCAN sampled-position panels. It did
not display PCT and SCAN regions with a common, clearly visible footprint.

This correction uses three equal-scale filled-cell maps: original PCT cost mask,
original SCAN collision query, and current native SCAN collision/support query.
All three use the same one-layer-per-XY floor grid. SCAN is queried on every floor
cell in the displayed region, including PCT-rejected cells; missing cells remain
explicitly gray. A fixed original floor band prevents upper/lower floors from
overwriting each other in projection. This is a conditional position-feasibility
slice at the recorded body yaw and ground + 0.30 m, not a complete reachable set.

Reuse the same captured sensor history, body states and reference route. Run the
already verified collision binaries. The original GPU-rendered scene is reused
at identical video-frame indices; the new composite is encoded on gpu5070ti.
Preserve the first movie and its source/evidence. No navigation implementation,
threshold, frozen version or adopted pointer changes.
