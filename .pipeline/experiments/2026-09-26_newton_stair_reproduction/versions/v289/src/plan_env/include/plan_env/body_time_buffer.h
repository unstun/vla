#ifndef VLA_BODY_TIME_BUFFER_H
#define VLA_BODY_TIME_BUFFER_H

#include <nav_msgs/msg/odometry.hpp>
#include <cstdint>
#include <deque>
#include <string>
#include <utility>

namespace scan_input_time {
// Called only by the serialized native-data callback group. This gates delivery,
// not freshness: consumers still enforce the original 100 ms body age limit.
class BodyTimeBuffer {
 public:
  using Message = nav_msgs::msg::Odometry::ConstSharedPtr;
  bool push(Message message) {
    if (!healthy()) return false;
    if (!message || message->header.stamp.sec < 0 || message->header.stamp.nanosec >= 1000000000u)
      return fail("invalid_body_source_stamp");
    const int64_t stamp = int64_t(message->header.stamp.sec)*1000000000LL + message->header.stamp.nanosec;
    if (stamp <= 0) return fail("invalid_body_source_stamp");
    if (stamp < high_water_) { ++ignored_older_samples_; return false; }
    if (stamp == high_water_) return true; // A duplicate cannot refresh evidence.
    if (pending_.size() >= 64) return fail("future_body_buffer_exhausted");
    high_water_ = stamp;
    pending_.emplace_back(stamp,std::move(message));
    return true;
  }
  Message takeDue(int64_t clock_ns) {
    Message latest;
    if (!healthy()) return latest;
    while (!pending_.empty() && pending_.front().first <= clock_ns) {
      latest = pending_.front().second;
      pending_.pop_front();
    }
    return latest;
  }
  uint64_t ignoredOlderSamples() const { return ignored_older_samples_; }
  bool healthy() const { return error_.empty(); }
  const std::string &error() const { return error_; }
 private:
  bool fail(const char *reason) { error_=reason; return false; }
  uint64_t ignored_older_samples_ = 0;
  int64_t high_water_ = 0;
  std::deque<std::pair<int64_t,Message>> pending_;
  std::string error_;
};
}
#endif
