// Exercise the actual compiled FSM with a synthetic sub-metre spline and a
// controlled ROS clock. No substitute planner, controller, or physics loop.
#include <plan_manage/scan_replan_fsm.h>
#include <rcl/time.h>
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>

void check(bool passed, const std::string &name)
{
  if (!passed) throw std::runtime_error(name);
  std::cout << "V35_CHECK " << name << " PASS" << std::endl;
}

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  try
  {
    rclcpp::NodeOptions options;
    const char *invalid = std::getenv("V35_INVALID_FREQUENCY");
    if (invalid)
      // strtod preserves a subnormal value for the implementation's period
      // validation; stod would throw on underflow before reaching the FSM.
      options.parameter_overrides({rclcpp::Parameter("fsm.replan_frequency", std::strtod(invalid, nullptr))});
    auto node = std::make_shared<rclcpp::Node>("scan_planner_node", options);
    scan_planner::SCANReplanFSM fsm;
    if (invalid)
    {
      bool rejected = false;
      try { fsm.init(node.get()); }
      catch (const std::runtime_error &error)
      {
        rejected = std::string(error.what()).find("fsm.replan_frequency") != std::string::npos;
      }
      check(rejected, "invalid_frequency_rejected");
      rclcpp::shutdown();
      return 0;
    }
    fsm.init(node.get());
    fsm.exec_timer_->cancel();
    fsm.safety_timer_->cancel();
    auto clock = [&](double seconds) {
      auto *handle = node->get_clock()->get_clock_handle();
      check(rcl_enable_ros_time_override(handle) == RCL_RET_OK, "clock_override_enabled");
      check(rcl_set_ros_time_override(handle, std::llround(seconds * 1e9)) == RCL_RET_OK,
            "clock_set");
    };
    auto &local = fsm.planner_manager_->local_data_;
    Eigen::MatrixXd points(3, 7);
    for (int i = 0; i < 7; ++i) points.col(i) << 0.8 * i / 6.0, 0.0, 0.35;
    for (int i = 4; i < 7; ++i) points.col(i) << 0.8, 0.0, 0.35;
    scan_planner::UniformBspline curve(points, 3, 0.5);
    auto reset = [&]() {
      clock(100.0);
      local.position_traj_ = curve;
      local.velocity_traj_ = curve.getDerivative();
      local.acceleration_traj_ = local.velocity_traj_.getDerivative();
      local.duration_ = curve.getTimeSum();
      local.start_time_ = node->now();
      local.start_pos_ = curve.evaluateDeBoorT(0.0);
      local.traj_id_ = 7;
      fsm.exec_state_ = scan_planner::SCANReplanFSM::EXEC_TRAJ;
      fsm.have_target_ = true;
      fsm.replan_fail_count_ = 0;
      fsm.end_pt_ = Eigen::Vector3d(10.0, 0.0, 0.35);
      fsm.odom_pos_ = local.start_pos_;
      fsm.odom_vel_.setZero();
      fsm.go2_execution_frozen_ = false;
      fsm.last_freeze_update_time_ = node->now();
      fsm.planner_manager_->global_data_.global_duration_ = 10.0;
      fsm.planner_manager_->global_data_.last_progress_time_ = 1.0;
#ifndef V35_LEGACY_PARENT
      fsm.replan_frequency_ = 2.0;
      fsm.last_nominal_replan_s_ = 100.0;
#endif
    };
    reset();
    clock(100.5);
    check(local.duration_ > 0.5 && (curve.evaluateDeBoorT(0.5) - local.start_pos_).norm() < 1.0,
          "fixture_short_and_not_expired");
    check(local.velocity_traj_.evaluateDeBoorT(local.duration_).norm() < 1e-10,
          "fixture_has_zero_terminal_velocity");
    fsm.execFSMCallback();
#ifdef V35_LEGACY_PARENT
    check(fsm.exec_state_ == scan_planner::SCANReplanFSM::EXEC_TRAJ,
          "parent_reproduces_missing_early_trigger");
#else
    check(fsm.exec_state_ == scan_planner::SCANReplanFSM::REPLAN_TRAJ,
          "short_curve_triggers_at_half_second");

    const char *expected = std::getenv("V35_EXPECT_FREQUENCY");
    check(node->get_parameter("fsm.replan_frequency").as_double() == (expected ? std::stod(expected) : 2.0),
          "configured_or_omitted_frequency_loaded");
    reset();
    fsm.replan_thresh_ = 1e-5;
    clock(100.49);
    fsm.execFSMCallback();
    check(fsm.exec_state_ == scan_planner::SCANReplanFSM::EXEC_TRAJ,
          "distance_cannot_trigger_before_period");
    for (int i = 0; i < 40; ++i) fsm.execFSMCallback();
    check(fsm.exec_state_ == scan_planner::SCANReplanFSM::EXEC_TRAJ,
          "paused_clock_does_not_trigger");

    reset();
    fsm.go2_execution_frozen_ = true;
    clock(100.5);
    fsm.execFSMCallback();
    check(fsm.exec_state_ == scan_planner::SCANReplanFSM::EXEC_TRAJ,
          "execution_freeze_suppresses_periodic_trigger");

    reset();
    fsm.end_pt_ = curve.evaluateDeBoorT(0.5);
    clock(100.5);
    fsm.execFSMCallback();
    check(fsm.exec_state_ == scan_planner::SCANReplanFSM::EXEC_TRAJ,
          "near_final_goal_keeps_existing_suppression");

    reset();
    fsm.exec_state_ = scan_planner::SCANReplanFSM::REPLAN_TRAJ;
    // Non-finite odometry makes the real getLocalTarget gate reject, before
    // any geometric query. This is a failed plan, not a fake solver response.
    fsm.odom_pos_.x() = std::numeric_limits<double>::quiet_NaN();
    clock(100.49);
    fsm.execFSMCallback();
    check(fsm.replan_fail_count_ == 0, "retry_not_attempted_before_deadline");
    clock(100.5);
    fsm.execFSMCallback();
    check(fsm.replan_fail_count_ == 1 && fsm.last_nominal_replan_s_ == 100.5,
          "failed_attempt_consumes_interval");
    for (int i = 0; i < 40; ++i) fsm.execFSMCallback();
    check(fsm.replan_fail_count_ == 1, "failure_does_not_spin_at_poll_frequency");
    clock(101.0);
    fsm.execFSMCallback();
    check(fsm.replan_fail_count_ == 2, "retry_runs_at_next_period");
    check(local.traj_id_ == 7 && local.position_traj_.getControlPoint().isApprox(points, 0.0),
          "failed_and_throttled_attempts_keep_accepted_curve");
    clock(111.0);
    fsm.execFSMCallback();
    fsm.execFSMCallback();
    check(fsm.replan_fail_count_ == 3, "missed_periods_coalesce_without_burst");

    reset();
    fsm.exec_state_ = scan_planner::SCANReplanFSM::GEN_NEW_TRAJ;
    fsm.odom_pos_.x() = std::numeric_limits<double>::quiet_NaN();
    clock(100.49);
    fsm.execFSMCallback();
    check(fsm.replan_fail_count_ == 0, "initial_plan_retry_waits_for_period");
    clock(100.5);
    fsm.execFSMCallback();
    for (int i = 0; i < 20; ++i) fsm.execFSMCallback();
    check(fsm.replan_fail_count_ == 1, "initial_plan_failure_is_rate_limited");

    reset();
    clock(99.0);
    check(!fsm.nominalReplanDue(true) && fsm.last_nominal_replan_s_ == 99.0,
          "clock_rewind_reanchors_without_attempt");
    clock(99.49);
    check(!fsm.nominalReplanDue(true), "rewound_clock_waits_full_period");
    clock(99.5);
    check(fsm.nominalReplanDue(true), "rewound_clock_resumes_after_period");
    fsm.replan_frequency_ = 4.0;
    clock(99.74);
    check(!fsm.nominalReplanDue(true), "configured_four_hz_waits");
    clock(99.75);
    check(fsm.nominalReplanDue(true), "configured_four_hz_triggers");

    reset();
    fsm.replan_frequency_ = 0.0;
    fsm.replan_thresh_ = 1.0;
    clock(100.5);
    fsm.execFSMCallback();
    check(fsm.exec_state_ == scan_planner::SCANReplanFSM::EXEC_TRAJ,
          "legacy_mode_retains_distance_trigger");
    fsm.replan_thresh_ = 1e-5;
    fsm.execFSMCallback();
    check(fsm.exec_state_ == scan_planner::SCANReplanFSM::REPLAN_TRAJ,
          "legacy_mode_still_triggers_on_distance");

    reset();
    clock(100.0 + local.duration_);
    fsm.execFSMCallback();
    check(fsm.exec_state_ == scan_planner::SCANReplanFSM::REPLAN_TRAJ && fsm.have_target_,
          "local_window_expiration_keeps_existing_transition");
    reset();
    fsm.end_pt_ = curve.evaluateDeBoorT(local.duration_);
    fsm.planner_manager_->global_data_.last_progress_time_ = 10.0;
    clock(100.0 + local.duration_);
    fsm.execFSMCallback();
    check(fsm.exec_state_ == scan_planner::SCANReplanFSM::WAIT_TARGET && !fsm.have_target_,
          "final_completion_keeps_wait_target_transition");

    reset();
    clock(99.8);
    fsm.checkCollisionCallback();
    check(fsm.exec_state_ == scan_planner::SCANReplanFSM::EMERGENCY_STOP,
          "safety_callback_remains_immediate_for_invalid_curve_time");
#endif
    rclcpp::shutdown();
    return 0;
  }
  catch (const std::exception &error)
  {
    std::cerr << "V35_FAILURE " << error.what() << std::endl;
    rclcpp::shutdown();
    return 1;
  }
}
