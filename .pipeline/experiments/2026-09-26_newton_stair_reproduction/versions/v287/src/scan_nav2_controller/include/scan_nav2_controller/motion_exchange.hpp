#pragma once

#include <atomic>
#include <mutex>
#include <optional>
#include <nav_msgs/msg/path.hpp>
#include <scan_planner_msgs/msg/bspline.hpp>

namespace scan_nav2_controller
{
// Two bounded slots, not an event queue: immutable input and completed output.
// Only the native thread consumes Input; only the control thread consumes Output.
class MotionExchange
{
public:
  struct Feedback { bool frozen{false}; int64_t trajectory{-1}; };
  struct Input {
    uint64_t generation{0}, revision{0}, reset{0};
    nav_msgs::msg::Path::ConstSharedPtr route;
    Feedback feedback;
  };
  struct Output {
    uint64_t generation;
    scan_planner_msgs::msg::Bspline::ConstSharedPtr spline;
  };
  struct Planning {uint64_t generation,revision; int64_t first_failure_ns; unsigned failures;};
  uint64_t setRoute(const nav_msgs::msg::Path &route,bool new_goal) {
    auto copy=std::make_shared<const nav_msgs::msg::Path>(route);
    std::lock_guard<std::mutex> lock(mutex_);
    // Geometry refresh is not a new task. A solve spanning it remains usable.
    if (new_goal) {
      ++input_.generation; ++input_.reset; output_.reset(); input_.feedback={};
    }
    ++input_.revision;input_.route=std::move(copy);planning_.reset();
    return input_.generation;
  }
  void cancel() {
    std::lock_guard<std::mutex> lock(mutex_);
    ++input_.generation;++input_.revision;++input_.reset;
    input_.route.reset();input_.feedback={};output_.reset();planning_.reset();
  }
  void planningResult(uint64_t generation,uint64_t revision,bool success,int64_t started_ns) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!input_.route || generation!=input_.generation || revision!=input_.revision) return;
    if (success) {planning_.reset();return;}
    if (!planning_) planning_=Planning{generation,revision,started_ns,0};
    ++planning_->failures;
  }
  std::optional<Planning> planning() const {
    std::lock_guard<std::mutex> lock(mutex_);return planning_;
  }
  void feedback(uint64_t generation,bool frozen,int64_t trajectory) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (input_.route && generation==input_.generation)
      input_.feedback={frozen,trajectory};
  }
  Input input() const {
    std::lock_guard<std::mutex> lock(mutex_);return input_;
  }
  bool publish(uint64_t generation,const scan_planner_msgs::msg::Bspline &spline) {
    auto copy=std::make_shared<const scan_planner_msgs::msg::Bspline>(spline);
    std::lock_guard<std::mutex> lock(mutex_);
    if (!input_.route || generation!=input_.generation) return false;
    output_=Output{generation,std::move(copy)};return true;
  }
  std::optional<Output> take() {
    std::lock_guard<std::mutex> lock(mutex_);
    auto output=std::move(output_);output_.reset();return output;
  }
  std::atomic<uint64_t> applied_revision{0}; // Input consumed, not a planning-success claim.
private:
  mutable std::mutex mutex_;
  Input input_;
  std::optional<Output> output_;
  std::optional<Planning> planning_;
};
}  // namespace scan_nav2_controller
