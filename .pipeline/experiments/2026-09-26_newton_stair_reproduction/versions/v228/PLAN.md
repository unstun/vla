# v228: bind support cell identity to the original PCT lattice

Parent v227 is a preserved failed attempt: physical-origin alignment fixes the
three old witnesses but introduces two equivalent corner failures. Float32
cloud minima do not define the original PCT lattice.

TerrainBundle already verifies PCT bytes against the terrain manifest. Parse
its existing PCTMAP01 header and bind its nominal lower cell-edge origin into
the native profile. Native support queries use that origin with double-ULP
integer normalization and half-open cells. Verify navigation/scored identity,
qualified physical source, equal resolution and near-integer shifts for all
inputs. Unconfigured sources retain original lookup.

Preserve all heights, terrain labels, cloud bytes, LiDAR classification, edge
fill/drop guards, unknown/history occupancy, hard tolerances, RL and repair
budget. No neighboring-cell selection, body-height adjustment or admission
waiver. Reuse the existing publisher/profile/native checker; no new source.

Gate: nine-package regression; same five old/new corner witnesses; installed
planner final-route admission and independent native recheck; full original
v217 query comparison with separate geometry/occupancy and edge predicates.
