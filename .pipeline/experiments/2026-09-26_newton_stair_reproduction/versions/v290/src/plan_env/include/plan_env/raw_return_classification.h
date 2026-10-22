#ifndef SCAN_REACTIVE_RAW_RETURN_CLASSIFICATION_H
#define SCAN_REACTIVE_RAW_RETURN_CLASSIFICATION_H

#include "eth_step_score_adaptation.h"

#include <cmath>
#include <limits>

namespace reactive_stair {

// PCT ground support is independent of the LiDAR occupancy stream. This is a
// positive endpoint classification; it never classifies an inflated hit by
// itself, and a nonterrain return at the same voxel wins.
inline bool selectedGroundReturn(const TerrainSnapshot &terrain,
                                 double x_m, double y_m, double z_m,
                                 double band_m, bool allow_risers = true) {
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
  if (!allow_risers) return false;
  // A mapped riser lies between adjacent selected treads. Its measured XY
  // may belong to either tread's cell; use the same interval from both sides.
  const StepScoreParameters parameters;
  if (std::abs(terrain.resolution_m - parameters.expected_resolution_m) > 1e-6 ||
      ix <= std::numeric_limits<int>::min() || ix >= std::numeric_limits<int>::max() ||
      iy <= std::numeric_limits<int>::min() || iy >= std::numeric_limits<int>::max()) return false;
  const int layer = nearestSurface(found->second, z_m, parameters.critical_height_m);
  if (layer < 0) return false;
  const auto &central=found->second[layer];
  if(central.support!=Support::Flat && central.support!=Support::Stair)return false;
  const double reference=central.elevation_m;
  for (int dx = -1; dx <= 1; ++dx) {
    for (int dy = -1; dy <= 1; ++dy) {
      if ((dx * dx + dy * dy) * terrain.resolution_m * terrain.resolution_m >
          parameters.first_radius_m * parameters.first_radius_m) continue;
      const auto neighbor = terrain.cells.find({static_cast<int>(ix) + dx, static_cast<int>(iy) + dy});
      if (neighbor == terrain.cells.end()) continue;
      const int associated = nearestSurface(neighbor->second, reference, parameters.critical_height_m);
      if(associated<0)continue;
      const auto &surface=neighbor->second[associated];
      if(surface.support!=Support::Flat && surface.support!=Support::Stair)continue;
      const double lower=std::min(reference,surface.elevation_m),upper=std::max(reference,surface.elevation_m);
      if(upper>lower && upper-lower<parameters.critical_height_m &&
          z_m>=lower-band_m && z_m<=upper+band_m)return true;
    }
  }
  return false;
}

inline bool mayWaiveRawContributor(bool confirmed_terrain_return,
                                   bool current_nonterrain_return,
                                   bool historical_nonterrain_return) {
  return confirmed_terrain_return && !current_nonterrain_return &&
         !historical_nonterrain_return;
}

}  // namespace reactive_stair

#endif
