#include <plan_env/motion_heading.h>
#include <plan_env/known_lite3_trunk.h>
#include <cassert>
#include <iostream>
using namespace reactive_stair;

int main() {
  const double actual = -1.525;
  const double noisy = -0.58305062;
  const double dx = 0.001 * std::cos(noisy), dy = 0.001 * std::sin(noisy);
  const double heading = motionHeading(dx, dy, actual, 5.03, 5.03);
  assert(heading == actual);
  // The old noisy direction placed the reference point beside the actual
  // trunk, matching the scan16 initial-pose diagnosis. The body did not turn.
  const double old_x = 0.18 * std::cos(noisy - actual);
  const double old_y = 0.18 * std::sin(noisy - actual);
  assert(!knownLite3TrunkInterior(old_x, old_y, 0, 5.03, 5.03));
  assert(knownLite3TrunkInterior(0.18, 0, 0, 5.03, 5.03));
  assert(std::abs(motionHeading(0.1, -0.2, actual, 5.03, 5.03) - std::atan2(-0.2, 0.1)) < 1e-12);
  assert(std::isnan(motionHeading(dx, dy, actual, 5.2, 5.03)));
  assert(std::isnan(motionHeading(dx, dy, actual, 5.0, 5.03)));
  assert(std::isnan(motionHeading(NAN, dy, actual, 5.03, 5.03)));
  std::cout << "unresolved direction uses fresh measured yaw; real displacement uses path yaw; invalid/stale fallback rejected\n";
}
