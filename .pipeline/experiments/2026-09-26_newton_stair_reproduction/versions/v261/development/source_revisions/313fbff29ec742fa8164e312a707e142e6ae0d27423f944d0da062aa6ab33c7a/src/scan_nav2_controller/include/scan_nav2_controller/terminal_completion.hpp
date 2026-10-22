#pragma once

#include <chrono>
#include <cmath>
#include <cstdint>
#include <lite3_nav2_interfaces/msg/robot_execution_state.hpp>

namespace scan_nav2_controller
{
// One terminal window, owned by the controller and queried by GoalChecker.
// Source time proves physical duration; steady time detects a stalled stream.
class TerminalCompletion
{
public:
  using Sample = lite3_nav2_interfaces::msg::RobotExecutionState;
  using Clock = std::chrono::steady_clock;
  using Time = Clock::time_point;
  double hold_s{2.0}, timeout_s{10.0}, max_gap_s{0.25};

  void resetGoal() {
    waiting_=false; holding_=false;
  }
  void updatePose(bool within, int64_t simulation_ns, Time now=Clock::now()) {
    if (!within) { resetGoal(); return; }
    if (!waiting_) {
      waiting_=true; holding_=false;
      entered_sim_ns_=simulation_ns; entered_wall_=now;
    }
  }
  bool waiting() const { return waiting_; }
  void observe(const Sample &sample, Time now=Clock::now()) {
    if (has_sample_ && (sample.run_epoch_ns!=epoch_ ||
        sample.state_sequence<=last_sequence_ || sample.simulation_time_ns<=last_sim_ns_)) return;
    if (!valid(sample)) { holding_=false; return; }
    const bool gap=has_sample_ &&
      (seconds(sample.simulation_time_ns-last_sim_ns_)>max_gap_s ||
       std::chrono::duration<double>(now-last_wall_).count()>max_gap_s);
    has_sample_=true; epoch_=sample.run_epoch_ns;
    last_sequence_=sample.state_sequence; last_sim_ns_=sample.simulation_time_ns; last_wall_=now;
    if (!waiting_ || sample.simulation_time_ns<static_cast<uint64_t>(entered_sim_ns_) ||
        sample.stance_mode!=Sample::FIXED_STAND || sample.policy_owns_joints ||
        !sample.navigation_ready || sample.command_stale || !quiet(sample)) {
      holding_=false; return;
    }
    if (!holding_ || gap) { hold_start_ns_=sample.simulation_time_ns; holding_=true; }
  }
  bool ready(int64_t simulation_ns, Time now=Clock::now()) const {
    return waiting_ && holding_ && simulation_ns>=0 &&
      static_cast<uint64_t>(simulation_ns)>=last_sim_ns_ &&
      seconds(static_cast<uint64_t>(simulation_ns)-last_sim_ns_)<=max_gap_s &&
      std::chrono::duration<double>(now-last_wall_).count()<=max_gap_s &&
      seconds(last_sim_ns_-hold_start_ns_)>=hold_s;
  }
  bool timedOut(Time now=Clock::now()) const {
    return waiting_ && std::chrono::duration<double>(now-entered_wall_).count()>=timeout_s;
  }

private:
  static double seconds(uint64_t ns) { return static_cast<double>(ns)*1e-9; }
  static double norm(const geometry_msgs::msg::Vector3 &v) {
    return std::hypot(std::hypot(v.x,v.y),v.z);
  }
  static bool finite(const geometry_msgs::msg::Twist &v) {
    return std::isfinite(v.linear.x) && std::isfinite(v.linear.y) && std::isfinite(v.linear.z) &&
      std::isfinite(v.angular.x) && std::isfinite(v.angular.y) && std::isfinite(v.angular.z);
  }
  static bool valid(const Sample &s) {
    return s.run_epoch_ns!=0 && s.stance_mode<=Sample::REJOIN &&
      finite(s.measured_velocity) && finite(s.applied_command);
  }
  static bool quiet(const Sample &s) {
    return norm(s.measured_velocity.linear)<=0.03 && norm(s.measured_velocity.angular)<=0.05 &&
      norm(s.applied_command.linear)<=1e-6 && norm(s.applied_command.angular)<=1e-6;
  }
  bool waiting_{false}, holding_{false}, has_sample_{false};
  int64_t entered_sim_ns_{0};
  uint64_t epoch_{0}, last_sequence_{0}, last_sim_ns_{0}, hold_start_ns_{0};
  Time entered_wall_{}, last_wall_{};
};
}  // namespace scan_nav2_controller
