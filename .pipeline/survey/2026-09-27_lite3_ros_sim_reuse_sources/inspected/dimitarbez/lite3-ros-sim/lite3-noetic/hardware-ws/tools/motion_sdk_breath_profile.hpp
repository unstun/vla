#pragma once

#include <algorithm>
#include <cmath>

// A deliberately slower physical translation of Gazebo's neutral idle loop.
// Gazebo alternates height, roll, and pitch every 0.6875 s.  Hardware keeps
// every foot planted, HipX fixed, and yaw at zero while reproducing the same
// two-sided inhale/exhale and opposing roll/pitch phrasing.
constexpr double kBreathInhaleSeconds = 0.75;
constexpr double kBreathExchangeSeconds = 1.25;
constexpr double kBreathReturnSeconds = 1.25;
constexpr double kBreathDurationSeconds =
    kBreathInhaleSeconds + kBreathExchangeSeconds + kBreathReturnSeconds;

constexpr double kBreathExpansion = -0.008;
constexpr double kBreathCompression = 0.020;
constexpr double kBreathRollBias = 0.004;
constexpr double kBreathPitchBias = 0.003;
constexpr double kKneeToHipCompression = 2.0;

struct BreathScalar {
  double position{0.0};
  double velocity{0.0};
};

struct BreathPose {
  BreathScalar compression;
  BreathScalar roll;
  BreathScalar pitch;
};

inline BreathScalar QuinticBreathSegment(double elapsed, double duration,
                                         double start, double end) {
  const double u = std::max(0.0, std::min(1.0, elapsed / duration));
  const double smooth = 10.0 * std::pow(u, 3) -
      15.0 * std::pow(u, 4) + 6.0 * std::pow(u, 5);
  const double derivative_u = 30.0 * std::pow(u, 2) -
      60.0 * std::pow(u, 3) + 30.0 * std::pow(u, 4);
  return {start + (end - start) * smooth,
          (end - start) * derivative_u / duration};
}

inline BreathPose SampleAnimalBreath(double elapsed) {
  elapsed = std::max(0.0, std::min(kBreathDurationSeconds, elapsed));
  BreathPose pose;
  if (elapsed <= kBreathInhaleSeconds) {
    pose.compression = QuinticBreathSegment(
        elapsed, kBreathInhaleSeconds, 0.0, kBreathExpansion);
    pose.roll = QuinticBreathSegment(
        elapsed, kBreathInhaleSeconds, 0.0, kBreathRollBias);
    pose.pitch = QuinticBreathSegment(
        elapsed, kBreathInhaleSeconds, 0.0, -kBreathPitchBias);
    return pose;
  }
  elapsed -= kBreathInhaleSeconds;
  if (elapsed <= kBreathExchangeSeconds) {
    pose.compression = QuinticBreathSegment(
        elapsed, kBreathExchangeSeconds, kBreathExpansion,
        kBreathCompression);
    pose.roll = QuinticBreathSegment(
        elapsed, kBreathExchangeSeconds, kBreathRollBias,
        -kBreathRollBias);
    pose.pitch = QuinticBreathSegment(
        elapsed, kBreathExchangeSeconds, -kBreathPitchBias,
        kBreathPitchBias);
    return pose;
  }
  elapsed -= kBreathExchangeSeconds;
  pose.compression = QuinticBreathSegment(
      elapsed, kBreathReturnSeconds, kBreathCompression, 0.0);
  pose.roll = QuinticBreathSegment(
      elapsed, kBreathReturnSeconds, -kBreathRollBias, 0.0);
  pose.pitch = QuinticBreathSegment(
      elapsed, kBreathReturnSeconds, kBreathPitchBias, 0.0);
  return pose;
}

inline BreathScalar LegCompression(const BreathPose& pose, int leg) {
  // MotionSDK leg order: FL, FR, HL, HR.  Differential leg compression tilts
  // the planted torso without moving HipX or asking the feet to twist in yaw.
  const double roll_sign = (leg == 0 || leg == 2) ? 1.0 : -1.0;
  const double pitch_sign = (leg == 0 || leg == 1) ? 1.0 : -1.0;
  return {
      pose.compression.position + roll_sign * pose.roll.position +
          pitch_sign * pose.pitch.position,
      pose.compression.velocity + roll_sign * pose.roll.velocity +
          pitch_sign * pose.pitch.velocity,
  };
}
