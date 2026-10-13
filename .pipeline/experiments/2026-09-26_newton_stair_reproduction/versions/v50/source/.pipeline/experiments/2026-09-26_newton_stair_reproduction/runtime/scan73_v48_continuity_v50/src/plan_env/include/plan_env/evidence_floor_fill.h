#ifndef P2B_EVIDENCE_FLOOR_FILL_H
#define P2B_EVIDENCE_FLOOR_FILL_H

// v34 (Dr Sun, 2026-09-29; audits/2026-09-29_corridor_entry). SCAN's footprint
// support reads PCT's navigation ground, which PCT trims by its obstacle-distance
// inflation. The surface evidence is PCT's uninflated selection of the same
// ground. Where the navigation cell containing an evidence cell's centre has no
// layer within tolerance_m of an evidence layer, the returned ground gains that
// layer, unless a drop lies within guard_radius_m: an evidence cell whose square
// comes within guard_radius_m of the candidate's square, with no surface within
// step_m of the layer and either no surface at all or one more than step_m below
// it. A cell with only higher surfaces is solid (a wall under an upper floor);
// LiDAR occupancy still decides obstacles. Navigation layers are never changed or
// removed. Unusable evidence adds nothing, as it scores exactly as without
// evidence in the step score (v30).
#include <plan_env/reactive_collision.h>

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <limits>
#include <vector>

namespace reactive_stair {

struct EvidenceFloorFill {
  bool evidence_used = false;
  std::size_t added = 0;          // evidence layers added to the navigation ground
  std::size_t drop_rejected = 0;  // candidates rejected because a drop lies within the guard
};

inline bool evidenceFillIndex(double coordinate, double origin, double resolution, int &index) {
  const double value = std::floor((coordinate - origin) / resolution);
  if (!std::isfinite(value) || value < std::numeric_limits<int>::min() ||
      value > std::numeric_limits<int>::max()) return false;
  index = static_cast<int>(value);
  return true;
}

inline TerrainSnapshot addGuardedEvidenceFloor(const TerrainSnapshot &navigation,
                                               const TerrainSnapshot *evidence,
                                               double tolerance_m, double step_m,
                                               double guard_radius_m,
                                               EvidenceFloorFill *summary = nullptr) {
  TerrainSnapshot out = navigation;
  EvidenceFloorFill fill;
  const bool usable = evidence != nullptr && valid(navigation) && valid(*evidence) &&
      evidence->frame == navigation.frame &&
      std::abs(evidence->resolution_m - navigation.resolution_m) <= 1e-9 &&
      std::isfinite(tolerance_m) && tolerance_m >= 0.0 &&
      std::isfinite(step_m) && step_m > 0.0 &&
      std::isfinite(guard_radius_m) && guard_radius_m >= 0.0;
  if (!usable) {
    if (summary) *summary = fill;
    return out;
  }
  fill.evidence_used = true;
  const double resolution = navigation.resolution_m;
  // Evidence cells whose squares come within guard_radius_m of the candidate cell's square.
  std::vector<Cell2> guard;
  const int reach = static_cast<int>(std::ceil(guard_radius_m / resolution)) + 1;
  for (int dx = -reach; dx <= reach; ++dx)
    for (int dy = -reach; dy <= reach; ++dy) {
      const double gap_x = std::max(0, std::abs(dx) - 1) * resolution;
      const double gap_y = std::max(0, std::abs(dy) - 1) * resolution;
      if (gap_x * gap_x + gap_y * gap_y <= guard_radius_m * guard_radius_m + 1e-12)
        guard.push_back({dx, dy});
    }
  // A drop: no surface within step_m of the level, and no surface at all or one below it.
  const auto drop = [&](const Cell2 &cell, double level) {
    const auto found = evidence->cells.find(cell);
    if (found == evidence->cells.end()) return true;
    bool lower = false;
    for (const SurfaceCell &surface : found->second) {
      if (std::abs(surface.elevation_m - level) <= step_m) return false;
      if (surface.elevation_m < level - step_m) lower = true;
    }
    return lower;
  };
  for (const auto &entry : evidence->cells) {
    int ix = 0, iy = 0;
    if (!evidenceFillIndex(evidence->origin_x_m + (entry.first.x + 0.5) * resolution,
                           navigation.origin_x_m, resolution, ix) ||
        !evidenceFillIndex(evidence->origin_y_m + (entry.first.y + 0.5) * resolution,
                           navigation.origin_y_m, resolution, iy)) continue;
    const Cell2 target{ix, iy};
    for (const SurfaceCell &candidate : entry.second) {
      const double level = candidate.elevation_m;
      const auto present = out.cells.find(target);
      if (present != out.cells.end() &&
          std::any_of(present->second.begin(), present->second.end(), [&](const SurfaceCell &surface) {
            return std::abs(surface.elevation_m - level) <= tolerance_m;
          })) continue;
      bool rejected = false;
      for (const Cell2 &offset : guard)
        if (drop({entry.first.x + offset.x, entry.first.y + offset.y}, level)) {
          rejected = true;
          break;
        }
      if (rejected) {
        ++fill.drop_rejected;
        continue;
      }
      // The decoder's default status; the step score labels it with the other layers.
      out.cells[target].push_back({Support::Stair, level});
      ++fill.added;
    }
  }
  if (summary) *summary = fill;
  return out;
}

}  // namespace reactive_stair

#endif
