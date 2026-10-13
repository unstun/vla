#ifndef VLA_MOTION_HEADING_H
#define VLA_MOTION_HEADING_H
#include <cmath>
#include <limits>
#include <plan_env/reactive_collision.h>

namespace reactive_stair {
// Match the existing controller's 1e-4 squared horizontal direction threshold.
// A sub-centimeter displacement is not evidence that the body has rotated.
inline double motionHeading(double dx, double dy, double measured_yaw,
                            double now, double body_stamp) {
  if (!std::isfinite(dx) || !std::isfinite(dy))
    return std::numeric_limits<double>::quiet_NaN();
  if (dx * dx + dy * dy >= 1e-4) return std::atan2(dy, dx);
  if (!std::isfinite(measured_yaw) || body_stamp <= 0.0 || !fresh(now, body_stamp, 0.1))
    return std::numeric_limits<double>::quiet_NaN();
  return measured_yaw;
}
}  // namespace reactive_stair
#endif
