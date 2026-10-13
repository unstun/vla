#pragma once
#include <cmath>
#include <cstdint>
#include <mutex>
#include <algorithm>
#include <stdexcept>

// A veto-only component seam. It does not publish commands or replace native
// trajectory, floor/support, PVA, identity, cancellation or stop checks.
class LaneGuard {
 public:
  enum class Decision { AllowExisting, NoOwner, Cancelled, SensorInvalid,
                        SensorStale, HazardPending, MapRejected, MapStale };
  explicit LaneGuard(double original_max_age) : max_age_(original_max_age) {
    if (!std::isfinite(max_age_) || max_age_ <= 0) throw std::invalid_argument("Invalid original freshness limit");
  }
  void beginOwner(uint64_t owner) {
    std::lock_guard<std::mutex> lock(mutex_);
    // Repeating the same owner's admission must not reset a latched cancel.
    if (owner == owner_) return;
    owner_ = owner; cancelled_ = false; sensor_invalid_ = true; input_seen_ = false;
    sensor_stamp_ = map_stamp_ = hazard_stamp_ = 0; map_clear_ = false;
  }
  void cancel(uint64_t owner) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (owner == owner_) cancelled_ = true;
  }
  bool observe(uint64_t owner, double stamp, bool valid_pair, bool threat) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!owner || owner != owner_) return false;
    if (!std::isfinite(stamp) || stamp <= 0 || stamp <= sensor_stamp_ || !valid_pair) {
      sensor_invalid_ = true; input_seen_ = true; return false;
    }
    sensor_stamp_ = stamp;
    // Invalid pairing/order is latched until explicit owner replacement.
    if (!input_seen_) sensor_invalid_ = false;
    input_seen_ = true;
    if (threat) hazard_stamp_ = std::max(hazard_stamp_, stamp);
    return true;
  }
  bool mapped(uint64_t owner, double stamp, bool original_checks_clear,
              double fully_applied_observation_stamp) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!owner || owner != owner_ || !std::isfinite(stamp) || stamp <= 0 || stamp < map_stamp_ ||
        !std::isfinite(fully_applied_observation_stamp) || fully_applied_observation_stamp < 0 ||
        fully_applied_observation_stamp > stamp) return false;
    map_stamp_ = stamp; map_clear_ = original_checks_clear;
    // A latest-only mapper cannot acknowledge skipped hazards merely by
    // publishing a later stamp. Caller must supply the contiguous applied bound.
    if (original_checks_clear && fully_applied_observation_stamp >= hazard_stamp_)
      hazard_stamp_ = 0;
    return true;
  }
  Decision evaluate(uint64_t owner, double now) const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!owner || owner != owner_) return Decision::NoOwner;
    if (cancelled_) return Decision::Cancelled;
    if (!std::isfinite(now) || sensor_invalid_) return Decision::SensorInvalid;
    if (!fresh(sensor_stamp_, now)) return Decision::SensorStale;
    if (hazard_stamp_ > 0) return Decision::HazardPending;
    if (!map_clear_) return Decision::MapRejected;
    if (!fresh(map_stamp_, now)) return Decision::MapStale;
    return Decision::AllowExisting;
  }
 private:
  bool fresh(double stamp, double now) const { return stamp > 0 && stamp <= now && now - stamp <= max_age_; }
  const double max_age_;
  mutable std::mutex mutex_;
  uint64_t owner_ = 0;
  bool cancelled_ = false, sensor_invalid_ = true, input_seen_ = false, map_clear_ = false;
  double sensor_stamp_ = 0, map_stamp_ = 0, hazard_stamp_ = 0;
};
