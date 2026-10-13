#include <algorithm>
#include <cmath>
#include <cstdint>
#include <memory>
#include <limits>
#include <stdexcept>
#include <vector>

#include <Eigen/Eigen>
#include <geometry_msgs/msg/twist.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <rclcpp/rclcpp.hpp>
#include <algorithm>
#include <scan_planner_msgs/msg/bspline.hpp>
#include <scan_planner_msgs/msg/p2_b_admission.hpp>
#include <scan_planner_msgs/msg/p2_b_cancel.hpp>
#include <scan_planner_msgs/msg/p2_b_route.hpp>
#include <scan_planner_msgs/msg/p2_b_stamped_twist.hpp>
#include <std_msgs/msg/bool.hpp>
#include <tf2_geometry_msgs/tf2_geometry_msgs.h>
#include <tf2/utils.h>

#include "bspline_opt/uniform_bspline.h"

namespace scan_planner
{
class ClosedLoopController : public rclcpp::Node
{
public:
  explicit ClosedLoopController(const rclcpp::NodeOptions &options = rclcpp::NodeOptions())
      : Node("closed_loop_controller", options)
  {
    time_forward_ = declare_parameter<double>("time_forward", 0.8);
    heading_error_threshold_ = declare_parameter<double>("heading_error_threshold", 0.8);
    kp_pos_ = declare_parameter<double>("kp_pos", 0.8);
    kp_yaw_ = declare_parameter<double>("kp_yaw", 1.5);
    max_vx_ = declare_parameter<double>("max_vx", 0.75);
    max_vy_ = declare_parameter<double>("max_vy", 0.35);
    max_vyaw_ = std::min(declare_parameter<double>("max_vyaw", 1.0), kMaxVYawLimit);
    finish_dist_ = declare_parameter<double>("finish_dist", 0.15);
    goal_xy_tolerance_ = declare_parameter<double>("goal_xy_tolerance", 0.25);
    goal_yaw_tolerance_ = declare_parameter<double>("goal_yaw_tolerance", 0.25);
    goal_z_tolerance_ = declare_parameter<double>("goal_z_tolerance", 0.20);
    for (double tolerance : {goal_xy_tolerance_, goal_yaw_tolerance_, goal_z_tolerance_})
      if (!std::isfinite(tolerance) || tolerance <= 0.0)
        throw std::runtime_error("Goal tolerances must be finite and positive");
    const double controller_frequency = declare_parameter<double>("controller_frequency", 100.0);
    if (!std::isfinite(controller_frequency) || controller_frequency <= 0.0 || controller_frequency > 100.0)
      throw std::runtime_error("controller_frequency must be finite and in (0, 100] Hz");
    const long double period_ns = 1.0e9L / controller_frequency;
    if (!std::isfinite(period_ns) || period_ns < 1.0L ||
        period_ns > static_cast<long double>(std::numeric_limits<std::int64_t>::max()))
      throw std::runtime_error("controller_frequency has an unrepresentable nanosecond period");
    const auto controller_period = std::chrono::nanoseconds(static_cast<std::int64_t>(period_ns));

    bspline_sub_ = create_subscription<scan_planner_msgs::msg::Bspline>(
        "planning/bspline", 10,
        std::bind(&ClosedLoopController::bsplineCallback, this, std::placeholders::_1));
    odom_sub_ = create_subscription<nav_msgs::msg::Odometry>(
        "body_pose", rclcpp::SensorDataQoS(),
        std::bind(&ClosedLoopController::odomCallback, this, std::placeholders::_1));
    goal_sub_ = create_subscription<scan_planner_msgs::msg::P2BRoute>(
        "/p2b/route", 10, std::bind(&ClosedLoopController::goalCallback, this, std::placeholders::_1));
    raw_cmd_pub_ = create_publisher<scan_planner_msgs::msg::P2BStampedTwist>("/quad_0/raw_scan_cmd_vel", 20);
    p2b_admission_pub_ = create_publisher<scan_planner_msgs::msg::P2BAdmission>("/p2b/scan_admission", 10);
    p2b_cancel_sub_ = create_subscription<scan_planner_msgs::msg::P2BCancel>("/p2b/scan_cancel", 10, std::bind(&ClosedLoopController::p2bCancelCallback, this, std::placeholders::_1));
    execution_frozen_pub_ = create_publisher<std_msgs::msg::Bool>("planning/go2_execution_frozen", 10);
    cmd_timer_ = create_wall_timer(controller_period,
                                   std::bind(&ClosedLoopController::cmdCallback, this));
    last_update_time_ = now();
    RCLCPP_INFO(get_logger(), "Closed-loop controller ready: controller_frequency_hz=%.6f period_ns=%lld clock=wall",
                controller_frequency, static_cast<long long>(controller_period.count()));
  }

private:
  static constexpr double kMaxVYawLimit = 1.0;

  bool goalIdentityMatches() const
  {
    return goal_route_ && have_p2b_identity_ && goal_route_->run_id == run_id_ &&
        goal_route_->epoch == epoch_ && goal_route_->request_id == request_id_ &&
        goal_route_->goal_id == goal_id_ && goal_route_->route_id == route_id_ &&
        goal_route_->command_id == command_id_ && goal_route_->generation == generation_ &&
        goal_route_->map_epoch == map_epoch_ && goal_route_->map_revision == map_revision_;
  }

  void goalCallback(const scan_planner_msgs::msg::P2BRoute::ConstSharedPtr msg)
  {
    if (!msg || !msg->has_goal_pose || msg->path.poses.empty() || msg->generation <= cancelled_generation_high_water_ ||
        msg->generation < max_generation_seen_) return;
    const auto &pose = msg->goal_pose;
    const auto &q = pose.orientation;
    const double norm2 = q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w;
    if (!std::isfinite(pose.position.x) || !std::isfinite(pose.position.y) ||
        !std::isfinite(pose.position.z) || !std::isfinite(norm2) || std::abs(norm2 - 1.0) > 1e-6)
      return;
    // A periodic global-path update keeps the initial goal pose and XY latch.
    if (goal_route_ && msg->run_id == goal_route_->run_id && msg->epoch == goal_route_->epoch &&
        msg->command_id == goal_route_->command_id && msg->generation == goal_route_->generation)
      return;
    goal_route_ = msg;
    goal_pos_ << pose.position.x, pose.position.y, pose.position.z;
    goal_yaw_ = tf2::getYaw(q);
    goal_xy_reached_ = false;
  }

  static double normalizeAngle(double angle)
  {
    while (angle > M_PI) angle -= 2.0 * M_PI;
    while (angle < -M_PI) angle += 2.0 * M_PI;
    return angle;
  }

  static Eigen::Vector2d clampNorm(const Eigen::Vector2d &value, double max_norm)
  {
    const double norm = value.norm();
    return (norm <= max_norm || norm < 1e-6) ? value : value / norm * max_norm;
  }

  double estimateDesiredYaw(double t_cur, const Eigen::Vector3d &pos_des) const
  {
    const double t_look = std::min(traj_duration_, t_cur + time_forward_);
    Eigen::Vector3d direction = traj_[0].evaluateDeBoorT(t_look) - pos_des;
    if (direction.head<2>().squaredNorm() < 1e-4)
      direction = traj_[1].evaluateDeBoorT(t_cur);
    return direction.head<2>().squaredNorm() < 1e-4
        ? odom_yaw_ : std::atan2(direction.y(), direction.x());
  }

  void fillIdentity(scan_planner_msgs::msg::P2BStampedTwist &out) const
  {
    out.run_id = run_id_;
    out.epoch = epoch_;
    out.request_id = request_id_;
    out.goal_id = goal_id_;
    out.route_id = route_id_;
    out.command_id = command_id_;
    out.generation = generation_;
    out.map_epoch = map_epoch_;
    out.map_revision = map_revision_;
    out.traj_id = traj_id_;
    out.stamp = now();
  }

  void publishTaggedCommand(const geometry_msgs::msg::Twist &cmd)
  {
    scan_planner_msgs::msg::P2BStampedTwist out;
    fillIdentity(out);
    out.twist = cmd;
    raw_cmd_pub_->publish(out);
  }

  void publishStop(double yaw_rate = 0.0)
  {
    geometry_msgs::msg::Twist cmd;
    cmd.angular.z = std::clamp(yaw_rate, -max_vyaw_, max_vyaw_);
    publishTaggedCommand(cmd);
  }

  bool cancelMatches(const scan_planner_msgs::msg::P2BCancel &msg) const
  {
    return have_p2b_identity_ && msg.run_id == run_id_ && msg.epoch == epoch_ && msg.request_id == request_id_ && msg.goal_id == goal_id_ && msg.route_id == route_id_ && msg.command_id == command_id_ && msg.generation == generation_;
  }

  void publishAdmissionForIdentity(const std::string &status, const std::string &message, bool hold_confirmed,
                                  const std::string &run_id, std::int64_t epoch, const std::string &request_id,
                                  const std::string &goal_id, const std::string &route_id, const std::string &command_id,
                                  std::int64_t generation, const std::string &map_epoch, std::int64_t map_revision,
                                  std::int64_t traj_id)
  {
    scan_planner_msgs::msg::P2BAdmission out;
    out.run_id = run_id;
    out.epoch = epoch;
    out.request_id = request_id;
    out.goal_id = goal_id;
    out.route_id = route_id;
    out.command_id = command_id;
    out.generation = generation;
    out.map_epoch = map_epoch;
    out.map_revision = map_revision;
    out.consumer = "controller";
    out.status = status;
    out.message = message;
    out.hold_confirmed = hold_confirmed;
    out.measured_stillness_confirmed = false;
    out.traj_id = traj_id;
    p2b_admission_pub_->publish(out);
  }

  void publishAdmission(const std::string &status, const std::string &message, bool hold_confirmed)
  {
    if (!have_p2b_identity_) return;
    publishAdmissionForIdentity(status, message, hold_confirmed, run_id_, epoch_, request_id_, goal_id_, route_id_, command_id_, generation_, map_epoch_, map_revision_, traj_id_);
  }

  void p2bCancelCallback(const scan_planner_msgs::msg::P2BCancel::ConstSharedPtr msg)
  {
    if (!msg) return;
    if (!cancelMatches(*msg))
    {
      if (msg->generation >= max_generation_seen_ && msg->generation > cancelled_generation_high_water_)
      {
        cancelled_generation_high_water_ = msg->generation;
        const bool saved_have = have_p2b_identity_;
        publishStop();
        have_p2b_identity_ = saved_have;
        publishAdmissionForIdentity("stopped", msg->reason.empty() ? "idle_controller_hold" : msg->reason, true,
                                    msg->run_id, msg->epoch, msg->request_id, msg->goal_id, msg->route_id, msg->command_id,
                                    msg->generation, msg->map_epoch, msg->map_revision, traj_id_);
      }
      return;
    }
    cancelled_generation_high_water_ = std::max(cancelled_generation_high_water_, msg->generation);
    receive_traj_ = false;
    goal_xy_reached_ = false;
    exec_time_ = 0.0;
    publishStop();
    publishExecutionFrozen(false);
    publishAdmission("stopped", msg->reason.empty() ? "controller_hold" : msg->reason, true);
  }

  void publishExecutionFrozen(bool frozen)
  {
    std_msgs::msg::Bool msg;
    msg.data = frozen;
    execution_frozen_pub_->publish(msg);
  }

  void bsplineCallback(const scan_planner_msgs::msg::Bspline::ConstSharedPtr msg)
  {
    if (msg->pos_pts.empty() || msg->knots.empty() || msg->order <= 0)
    {
      RCLCPP_WARN(get_logger(), "Ignoring invalid B-spline");
      return;
    }
    if (msg->start_time.sec < 0 || msg->start_time.nanosec >= 1000000000u) {
      RCLCPP_WARN(get_logger(), "Ignoring B-spline with invalid time origin");
      return;
    }
    const auto receipt_time = now();
    const rclcpp::Time trajectory_origin(msg->start_time, receipt_time.get_clock_type());
    const bool incoming_has_p2b_identity = !msg->command_id.empty() && msg->generation > 0;
    if (incoming_has_p2b_identity)
    {
      if (msg->generation <= cancelled_generation_high_water_)
      {
        publishAdmissionForIdentity("rejected", "generation_cancelled_before_spline", false,
                                    msg->run_id, msg->epoch, msg->request_id, msg->goal_id, msg->route_id, msg->command_id,
                                    msg->generation, msg->map_epoch, msg->map_revision, msg->traj_id);
        return;
      }
      if (msg->generation < max_generation_seen_)
      {
        publishAdmissionForIdentity("rejected", "stale_spline_generation", false,
                                    msg->run_id, msg->epoch, msg->request_id, msg->goal_id, msg->route_id, msg->command_id,
                                    msg->generation, msg->map_epoch, msg->map_revision, msg->traj_id);
        return;
      }
      if (emergency_stop_ && !msg->emergency_stop && msg->run_id == run_id_ &&
          msg->epoch == epoch_ && msg->command_id == command_id_ && msg->generation == generation_ &&
          msg->traj_id <= traj_id_)
      {
        RCLCPP_WARN(get_logger(), "Ignoring a pre-emergency trajectory during safety stop");
        return;
      }
    }
    Eigen::MatrixXd points(3, msg->pos_pts.size());
    for (size_t i = 0; i < msg->pos_pts.size(); ++i)
      points.col(i) << msg->pos_pts[i].x, msg->pos_pts[i].y, msg->pos_pts[i].z;
    Eigen::VectorXd knots(msg->knots.size());
    for (size_t i = 0; i < msg->knots.size(); ++i) knots(i) = msg->knots[i];
    UniformBspline position(points, msg->order, 0.1);
    position.setKnot(knots);
    traj_ = {position, position.getDerivative()};
    traj_.push_back(traj_[1].getDerivative());
    traj_duration_ = traj_[0].getTimeSum();
    traj_id_ = msg->traj_id;
    run_id_ = msg->run_id;
    epoch_ = msg->epoch;
    request_id_ = msg->request_id;
    goal_id_ = msg->goal_id;
    route_id_ = msg->route_id;
    command_id_ = msg->command_id;
    generation_ = msg->generation;
    map_epoch_ = msg->map_epoch;
    map_revision_ = msg->map_revision;
    have_p2b_identity_ = incoming_has_p2b_identity;
    if (have_p2b_identity_) max_generation_seen_ = std::max(max_generation_seen_, generation_);
    // Consume the producer's sampled epoch once. Subsequent command ticks keep
    // the original incremental phase, including heading/final-yaw freezing.
    exec_time_ = msg->emergency_stop ? 0.0 :
        std::clamp((receipt_time - trajectory_origin).seconds(), 0.0, traj_duration_);
    if (have_p2b_identity_) publishAdmission("accepted", "controller_bspline_accepted", false);
    last_update_time_ = receipt_time;
    receive_traj_ = true;
    emergency_stop_ = msg->emergency_stop;
    if (emergency_stop_)
    {
      goal_xy_reached_ = false;
      publishExecutionFrozen(false);
      publishStop();
    }
    RCLCPP_INFO(get_logger(), "Received trajectory %lld, duration %.3fs",
                static_cast<long long>(traj_id_), traj_duration_);
  }

  void odomCallback(const nav_msgs::msg::Odometry::ConstSharedPtr msg)
  {
    odom_pos_ << msg->pose.pose.position.x, msg->pose.pose.position.y, msg->pose.pose.position.z;
    odom_yaw_ = tf2::getYaw(msg->pose.pose.orientation);
    have_odom_ = true;
  }

  void cmdCallback()
  {
    if (emergency_stop_)
    {
      publishExecutionFrozen(false);
      publishStop();
      return;
    }
    if (!receive_traj_ || !have_odom_)
    {
      publishExecutionFrozen(false);
      publishStop();
      return;
    }
    const auto current_time = now();
    if (goalIdentityMatches())
    {
      const bool within_xy = (goal_pos_ - odom_pos_).head<2>().norm() <= goal_xy_tolerance_;
      const bool within_z = std::abs(goal_pos_.z() - odom_pos_.z()) <= goal_z_tolerance_;
      if (within_xy && within_z) goal_xy_reached_ = true;
      // Nav2 stateful goal checking: once in XY tolerance, align final yaw.
      // The backend rechecks measured XYZ/yaw after causal stopped dwell.
      if (goal_xy_reached_ && within_z)
      {
        const double error = normalizeAngle(goal_yaw_ - odom_yaw_);
        if (std::abs(error) <= goal_yaw_tolerance_ && !within_xy)
          goal_xy_reached_ = false; // Reacquire strict final XY after yaw drift.
        else
        {
          publishExecutionFrozen(true);
          publishStop(std::abs(error) <= goal_yaw_tolerance_ ? 0.0 : kp_yaw_ * error);
          last_update_time_ = current_time;
          return;
        }
      }
    }
    double dt = (current_time - last_update_time_).seconds();
    if (dt < 0.0 || dt > 0.2) dt = 0.0;
    const double t_eval = std::min(exec_time_, traj_duration_);
    Eigen::Vector3d pos_des = traj_[0].evaluateDeBoorT(t_eval);
    const double yaw_error = normalizeAngle(estimateDesiredYaw(t_eval, pos_des) - odom_yaw_);
    const double yaw_command = std::clamp(kp_yaw_ * yaw_error, -max_vyaw_, max_vyaw_);
    if (std::abs(yaw_error) > heading_error_threshold_)
    {
      publishExecutionFrozen(true);
      publishStop(yaw_command);
      last_update_time_ = current_time;
      return;
    }

    publishExecutionFrozen(false);
    exec_time_ = std::min(traj_duration_, exec_time_ + dt);
    last_update_time_ = current_time;
    pos_des = traj_[0].evaluateDeBoorT(exec_time_);
    const Eigen::Vector3d vel_des = traj_[1].evaluateDeBoorT(exec_time_);
    const Eigen::Vector2d pos_error(pos_des.x() - odom_pos_.x(), pos_des.y() - odom_pos_.y());
    const Eigen::Vector2d vel_world = clampNorm(
        Eigen::Vector2d(vel_des.x(), vel_des.y()) + kp_pos_ * pos_error,
        std::max(max_vx_, max_vy_));
    const double c = std::cos(odom_yaw_);
    const double s = std::sin(odom_yaw_);
    geometry_msgs::msg::Twist command;
    command.linear.x = std::clamp(c * vel_world.x() + s * vel_world.y(), -max_vx_, max_vx_);
    command.linear.y = std::clamp(-s * vel_world.x() + c * vel_world.y(), -max_vy_, max_vy_);
    command.angular.z = yaw_command;
    if (exec_time_ >= traj_duration_ && pos_error.norm() < finish_dist_)
      command = geometry_msgs::msg::Twist();
    publishTaggedCommand(command);
  }

  rclcpp::Publisher<scan_planner_msgs::msg::P2BStampedTwist>::SharedPtr raw_cmd_pub_;
  rclcpp::Publisher<scan_planner_msgs::msg::P2BAdmission>::SharedPtr p2b_admission_pub_;
  rclcpp::Subscription<scan_planner_msgs::msg::P2BCancel>::SharedPtr p2b_cancel_sub_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr execution_frozen_pub_;
  rclcpp::Subscription<scan_planner_msgs::msg::Bspline>::SharedPtr bspline_sub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  rclcpp::Subscription<scan_planner_msgs::msg::P2BRoute>::SharedPtr goal_sub_;
  scan_planner_msgs::msg::P2BRoute::ConstSharedPtr goal_route_;
  Eigen::Vector3d goal_pos_{Eigen::Vector3d::Zero()};
  double goal_yaw_{0.0};
  bool goal_xy_reached_{false};
  double goal_xy_tolerance_, goal_yaw_tolerance_, goal_z_tolerance_;
  rclcpp::TimerBase::SharedPtr cmd_timer_;
  bool receive_traj_{false};
  bool emergency_stop_{false};
  bool have_odom_{false};
  std::vector<UniformBspline> traj_;
  double traj_duration_{0.0};
  std::int64_t traj_id_{0};
  bool have_p2b_identity_{false};
  std::int64_t max_generation_seen_{0};
  std::int64_t cancelled_generation_high_water_{0};
  std::string run_id_, request_id_, goal_id_, route_id_, command_id_, map_epoch_;
  std::int64_t epoch_{0}, generation_{0}, map_revision_{0};
  Eigen::Vector3d odom_pos_{Eigen::Vector3d::Zero()};
  double odom_yaw_{0.0};
  double exec_time_{0.0};
  rclcpp::Time last_update_time_{0, 0, RCL_ROS_TIME};
  double time_forward_, heading_error_threshold_, kp_pos_, kp_yaw_;
  double max_vx_, max_vy_, max_vyaw_, finish_dist_;
};
}  // namespace scan_planner

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<scan_planner::ClosedLoopController>());
  rclcpp::shutdown();
  return 0;
}
