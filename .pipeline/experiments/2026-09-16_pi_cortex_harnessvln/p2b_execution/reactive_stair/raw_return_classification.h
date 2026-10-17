#ifndef P2B_REACTIVE_RAW_RETURN_CLASSIFICATION_H
#define P2B_REACTIVE_RAW_RETURN_CLASSIFICATION_H

#include "reactive_collision.h"

#include <cmath>
#include <limits>

namespace reactive_stair {

// PCT ground support is independent of the LiDAR occupancy stream. This is a
// positive endpoint classification; it never classifies an inflated hit by
// itself, and a nonterrain return at the same voxel wins.
inline bool selectedGroundReturn(const TerrainSnapshot &terrain,
                                 double x_m, double y_m, double z_m,
                                 double band_m) {
  if (terrain.cells.empty() || !std::isfinite(terrain.resolution_m) ||
      terrain.resolution_m <= 0.0 || !std::isfinite(x_m) || !std::isfinite(y_m) ||
      !std::isfinite(z_m) || !std::isfinite(band_m) || band_m < 0.0) return false;
  const double ix = std::floor((x_m - terrain.origin_x_m) / terrain.resolution_m);
  const double iy = std::floor((y_m - terrain.origin_y_m) / terrain.resolution_m);
  if (!std::isfinite(ix) || !std::isfinite(iy) ||
      ix < std::numeric_limits<int>::min() || ix > std::numeric_limits<int>::max() ||
      iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max()) return false;
  const auto found = terrain.cells.find({static_cast<int>(ix), static_cast<int>(iy)});
  if (found == terrain.cells.end()) return false;
  for (const SurfaceCell &surface : found->second)
    if ((surface.support == Support::Flat || surface.support == Support::Stair) &&
        std::abs(z_m - surface.elevation_m) <= band_m) return true;
  return false;
}

inline bool mayWaiveRawContributor(bool current_terrain_return,
                                   bool current_nonterrain_return,
                                   bool historical_nonterrain_return) {
  return current_terrain_return && !current_nonterrain_return &&
         !historical_nonterrain_return;
}

}  // namespace reactive_stair

#endif
