#ifndef VLA_KNOWN_LITE3_TRUNK_H
#define VLA_KNOWN_LITE3_TRUNK_H
#include <cmath>
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

inline Occupancy measuredTrunkQuery(Occupancy occupancy, bool inflated_hit,
                                    bool known_trunk_interior) {
  if (occupancy == Occupancy::Unknown && !inflated_hit && known_trunk_interior)
    return Occupancy::Free;
  return occupancy;
}
}  // namespace reactive_stair
#endif
