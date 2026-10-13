#pragma once

#include <array>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <sstream>
#include <string>

namespace scan_planner {

// Diagnostic only. These values never authorize motion or choose a retry.
enum class FailureStage : std::size_t {
  None, Target, SeedSearch, SeedGeometry, Optimizer, Dynamics, FinalCollision,
  Epoch, InvalidInput, Count
};
enum class ObservationState { Fresh, Missing, Invalid, Future, Stale };

inline const char *name(FailureStage stage) {
  constexpr const char *names[] = {"none", "target", "seed_search", "seed_geometry",
    "optimizer", "dynamics", "final_collision", "epoch", "invalid_input"};
  const auto index = static_cast<std::size_t>(stage);
  return index < static_cast<std::size_t>(FailureStage::Count) ? names[index] : "invalid";
}
inline const char *name(ObservationState state) {
  switch (state) {
    case ObservationState::Fresh: return "fresh";
    case ObservationState::Missing: return "missing";
    case ObservationState::Invalid: return "invalid";
    case ObservationState::Future: return "future";
    case ObservationState::Stale: return "stale";
  }
  return "invalid";
}
inline ObservationState observationState(bool ready, double now, double stamp, double max_age) {
  if (!ready) return ObservationState::Missing;
  if (!std::isfinite(now) || !std::isfinite(stamp) || !std::isfinite(max_age) || max_age < 0)
    return ObservationState::Invalid;
  if (now < stamp) return ObservationState::Future;
  return now - stamp <= max_age ? ObservationState::Fresh : ObservationState::Stale;
}

struct PlanningFailure {
  FailureStage stage{FailureStage::None};
  const char *detail{"none"};  // Compile-time literals only; no external text.
  ObservationState observation{ObservationState::Missing};
  std::uint64_t map_revision{0};
};

class PlanningOutcome {
 public:
  void begin() {
    active_ = true;
    success_ = false;
    first_ = last_ = {};
    counts_.fill(0);
    failures_ = 0;
  }
  bool active() const { return active_; }
  void rejected(FailureStage stage, const char *detail, ObservationState observation,
                std::uint64_t revision) {
    const auto index = static_cast<std::size_t>(stage);
    if (!active_ || stage == FailureStage::None || index >= counts_.size()) return;
    last_ = {stage, detail, observation, revision};
    if (failures_++ == 0) first_ = last_;
    ++counts_[index];
  }
  void finish(bool success) { success_ = success; active_ = false; }
  bool success() const { return success_; }
  std::size_t failures() const { return failures_; }
  const PlanningFailure &first() const { return first_; }
  const PlanningFailure &last() const { return last_; }
  const std::array<std::size_t, static_cast<std::size_t>(FailureStage::Count)> &counts() const {
    return counts_;
  }
  std::string json() const {
    std::ostringstream out;
    out << "{\"success\":" << (success_ ? "true" : "false")
        << ",\"rejections\":" << failures_ << ",\"first\":";
    writeFailure(out, first_);
    out << ",\"last\":";
    writeFailure(out, last_);
    out << ",\"counts\":{";
    for (std::size_t i = 1; i < counts_.size(); ++i) {
      if (i > 1) out << ',';
      out << '\"' << name(static_cast<FailureStage>(i)) << "\":" << counts_[i];
    }
    out << "}}";
    return out.str();
  }

 private:
  static void writeFailure(std::ostream &out, const PlanningFailure &value) {
    out << "{\"stage\":\"" << name(value.stage) << "\",\"detail\":\"" << value.detail
        << "\",\"observation\":\"" << name(value.observation)
        << "\",\"map_revision\":" << value.map_revision << '}';
  }
  bool active_{false};
  bool success_{false};
  std::size_t failures_{0};
  PlanningFailure first_, last_;
  std::array<std::size_t, static_cast<std::size_t>(FailureStage::Count)> counts_{};
};

}  // namespace scan_planner
