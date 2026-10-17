#include <cassert>
#include <cmath>

#include "motion_sdk_breath_profile.hpp"
#include "motion_sdk_safety.hpp"

namespace {

bool Near(double left, double right, double tolerance = 1e-9) {
  return std::abs(left - right) <= tolerance;
}

}  // namespace

int main() {
  assert(!RobotStateRequiresStop(1, 0));
  assert(!RobotStateRequiresStop(4, 0));
  assert(!RobotStateRequiresStop(5, 0));
  assert(!RobotStateRequiresStop(6, 0));
  assert(RobotStateRequiresStop(8, 0));
  assert(RobotStateRequiresStop(1, 1));
  assert(RobotStateRequiresStop(6, 0x80000000u));

  const BreathPose start = SampleAnimalBreath(0.0);
  assert(Near(start.compression.position, 0.0));
  assert(Near(start.compression.velocity, 0.0));

  const BreathPose inhale = SampleAnimalBreath(kBreathInhaleSeconds);
  assert(Near(inhale.compression.position, kBreathExpansion));
  assert(Near(inhale.roll.position, kBreathRollBias));
  assert(Near(inhale.pitch.position, -kBreathPitchBias));
  assert(Near(inhale.compression.velocity, 0.0));

  const BreathPose exhale = SampleAnimalBreath(
      kBreathInhaleSeconds + kBreathExchangeSeconds);
  assert(Near(exhale.compression.position, kBreathCompression));
  assert(Near(exhale.roll.position, -kBreathRollBias));
  assert(Near(exhale.pitch.position, kBreathPitchBias));
  assert(Near(exhale.compression.velocity, 0.0));

  const BreathPose end = SampleAnimalBreath(kBreathDurationSeconds);
  assert(Near(end.compression.position, 0.0));
  assert(Near(end.roll.position, 0.0));
  assert(Near(end.pitch.position, 0.0));
  assert(Near(end.compression.velocity, 0.0));

  double minimum = 1.0;
  double maximum = -1.0;
  for (int sample = 0; sample <= 3250; ++sample) {
    const BreathPose pose = SampleAnimalBreath(sample / 1000.0);
    for (int leg = 0; leg < 4; ++leg) {
      const BreathScalar compression = LegCompression(pose, leg);
      assert(std::isfinite(compression.position));
      assert(std::isfinite(compression.velocity));
      minimum = std::min(minimum, compression.position);
      maximum = std::max(maximum, compression.position);
    }
  }
  assert(minimum >= -0.015000001);
  assert(maximum <= 0.027000001);
  assert(kKneeToHipCompression * maximum <= 0.054000001);
  return 0;
}
