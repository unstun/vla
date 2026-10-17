#ifndef SCAN_PHYSICAL_FLOOR_PRESENCE_H
#define SCAN_PHYSICAL_FLOOR_PRESENCE_H

// A floor's existence is independent of its traversal score. This type has no
// Support label and cannot be passed to CollisionDecision or LiDAR classification.
#include <plan_env/reactive_collision.h>
#include <limits>

namespace reactive_stair {
struct PhysicalFloorCell { double elevation_m; double traversal_cost; };
struct PhysicalFloorSnapshot {
  std::string source_id, frame;
  double stamp_s{0.0}, resolution_m{0.0}, origin_x_m{0.0}, origin_y_m{0.0};
  std::map<Cell2, std::vector<PhysicalFloorCell>> cells;
};
inline bool physicalFloorMetadata(const PhysicalFloorSnapshot &value) {
  return !value.source_id.empty() && !value.frame.empty() && std::isfinite(value.stamp_s) &&
      value.stamp_s > 0.0 && std::isfinite(value.resolution_m) && value.resolution_m > 0.0 &&
      std::isfinite(value.origin_x_m) && std::isfinite(value.origin_y_m) && !value.cells.empty();
}
inline bool validPhysicalFloor(const PhysicalFloorSnapshot &value) {
  if (!physicalFloorMetadata(value)) return false;
  for (const auto &entry : value.cells) {
    if (entry.second.empty()) return false;
    for (const auto &floor : entry.second)
      if (!std::isfinite(floor.elevation_m) || !std::isfinite(floor.traversal_cost) || floor.traversal_cost < 0.0) return false;
  }
  return true;
}
inline bool physicalFloorIndex(const PhysicalFloorSnapshot &value, double x, double y, Cell2 &cell) {
  if (!physicalFloorMetadata(value)) return false;
  const double ix = std::floor((x-value.origin_x_m)/value.resolution_m);
  const double iy = std::floor((y-value.origin_y_m)/value.resolution_m);
  if (!std::isfinite(ix) || !std::isfinite(iy) || ix < std::numeric_limits<int>::min() ||
      ix > std::numeric_limits<int>::max() || iy < std::numeric_limits<int>::min() || iy > std::numeric_limits<int>::max()) return false;
  cell = {static_cast<int>(ix), static_cast<int>(iy)}; return true;
}
// Same nearest-height and ambiguity contract as selected terrain, without a Support label.
inline int nearestPhysicalFloor(const std::vector<PhysicalFloorCell> &floors, double level, double maximum_distance) {
  if (!std::isfinite(level) || !std::isfinite(maximum_distance) || maximum_distance < 0.0) return -1;
  int selected=-1; double best=std::numeric_limits<double>::infinity(); bool ambiguous=false;
  for (size_t i=0;i<floors.size();++i) {
    if (!std::isfinite(floors[i].elevation_m) || !std::isfinite(floors[i].traversal_cost) || floors[i].traversal_cost<0.0) return -1;
    const double distance=std::abs(floors[i].elevation_m-level);
    if (distance+1e-9<best) {best=distance; selected=static_cast<int>(i); ambiguous=false;}
    else if (std::abs(distance-best)<=1e-9) ambiguous=true;
  }
  return ambiguous || best>maximum_distance ? -1 : selected;
}
inline bool physicalFloorHeight(const PhysicalFloorSnapshot &physical, const TerrainSnapshot &input,
                                const Cell2 &cell, double level, double maximum_distance, double &height) {
  Cell2 physical_cell;
  if (!physicalFloorIndex(physical, input.origin_x_m+(cell.x+0.5)*input.resolution_m,
                          input.origin_y_m+(cell.y+0.5)*input.resolution_m, physical_cell)) return false;
  const auto found=physical.cells.find(physical_cell); if(found==physical.cells.end()) return false;
  const int nearest=nearestPhysicalFloor(found->second,level,maximum_distance); if(nearest<0) return false;
  height=found->second[nearest].elevation_m; return true;
}
inline bool physicalFloorDrop(const PhysicalFloorSnapshot &physical, const TerrainSnapshot &input,
                              const Cell2 &cell, double level, double step) {
  Cell2 physical_cell;
  if (!physicalFloorIndex(physical,input.origin_x_m+(cell.x+0.5)*input.resolution_m,
                          input.origin_y_m+(cell.y+0.5)*input.resolution_m,physical_cell)) return true;
  const auto found=physical.cells.find(physical_cell); if(found==physical.cells.end()) return true;
  if (nearestPhysicalFloor(found->second,level,step)>=0) return false;
  // Preserve the existing higher-only solid-wall interpretation. Ambiguous
  // nearby levels and genuinely lower/missing floors remain conservative.
  for (const auto &floor:found->second)
    if (!std::isfinite(floor.elevation_m) || std::abs(floor.elevation_m-level)<=step || floor.elevation_m<level-step) return true;
  return false;
}
} // namespace reactive_stair
#endif
