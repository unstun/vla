#ifndef VLA_KNOWN_LITE3_TRUNK_H
#define VLA_KNOWN_LITE3_TRUNK_H
#include <cmath>
#include <algorithm>
#include <plan_env/reactive_collision.h>

namespace reactive_stair {
// Exact union of the two TORSO collision boxes in the pinned Isaac URDF:
// 803d552703bcc4f72ce15f38b95bc3f62e3e4ada0b42bf3ecf71b32b6590bb9d.
// This classifies only the current measured trunk interior. It neither clears
// map cells nor establishes free space around, ahead of, or behind the trunk.
inline bool knownLite3TrunkInterior(double x, double y, double z,
                                    double now, double pose_stamp) {
  if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z) ||
      pose_stamp <= 0.0 || !fresh(now, pose_stamp, 0.1)) return false;
  const bool in_xy = (std::abs(x) <= 0.25 && std::abs(y) <= 0.05) ||
                     (std::abs(x) <= 0.125 && std::abs(y) <= 0.10);
  return in_xy && std::abs(z - 0.01) <= 0.06;
}


// Reference: Nav2 Humble 3c3db59 ObstacleLayer::updateFootprint/updateCosts.
// Geometry is the same two-circle footprint used by SCAN collision queries.
// Unlike Nav2's unconditional footprint clearing, an observed obstacle wins.
// Vertically it spans the trunk bottom (-0.05 m) up to the mid360_scan_frame
// origin (+0.10854 m in TORSO, pinned Isaac URDF 803d5527). The 15-degree
// nose-down Mid-360 cannot observe that slice beside and behind itself.
inline bool knownNavigationFootprintInterior(double x, double y, double z,
    double now, double pose_stamp, double radius, double offset) {
  if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z) ||
      !std::isfinite(radius) || radius < 0.0 || !std::isfinite(offset) || offset < 0.0 ||
      pose_stamp <= 0.0 || !fresh(now, pose_stamp, 0.1)) return false;
  const double dx = std::min(std::abs(x - offset), std::abs(x + offset));
  return dx * dx + y * y <= radius * radius && z >= -0.05 && z <= 0.10854;
}

inline Occupancy measuredTrunkQuery(Occupancy occupancy, bool inflated_hit,
                                    bool known_trunk_interior) {
  if (occupancy == Occupancy::Unknown && !inflated_hit && known_trunk_interior)
    return Occupancy::Free;
  return occupancy;
}
}  // namespace reactive_stair
#endif
