#pragma once
// v82 tracking geometry with v206 command continuity. See tracking_provenance.json.
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
#include <nav_msgs/msg/path.hpp>
#include <bspline_opt/full_trajectory_collision.h>
#include <rclcpp/rclcpp.hpp>
#include <algorithm>
#include <scan_planner_msgs/msg/bspline.hpp>
#include <std_msgs/msg/bool.hpp>
#include <tf2_geometry_msgs/tf2_geometry_msgs.h>
#include <tf2/utils.h>
#include <scan_nav2_controller/command_slew.hpp>

#include "bspline_opt/uniform_bspline.h"

namespace scan_planner
{
class TrackingNode : public rclcpp::Node
{
public:
  explicit TrackingNode(const rclcpp::NodeOptions &options = rclcpp::NodeOptions())
      : Node("scan_nav2_tracking", options)
  {
    time_forward_ = declare_parameter<double>("time_forward", 0.8);
    heading_error_threshold_ = declare_parameter<double>("heading_error_threshold", 1.0);
    heading_resume_threshold_ = declare_parameter<double>("heading_resume_threshold", 0.6);
    expired_min_walk_speed_ = declare_parameter<double>("expired_min_walk_speed", 0.20);
    slew_.linear_acceleration = declare_parameter<double>("linear_acceleration", 1.0);
    slew_.linear_deceleration = declare_parameter<double>("linear_deceleration", 2.0);
    slew_.angular_acceleration = declare_parameter<double>("angular_acceleration", 2.0);
    slew_.angular_deceleration = declare_parameter<double>("angular_deceleration", 3.0);
    for (double value : {heading_error_threshold_, heading_resume_threshold_, expired_min_walk_speed_,
        slew_.linear_acceleration, slew_.linear_deceleration,
        slew_.angular_acceleration, slew_.angular_deceleration})
      if (!std::isfinite(value) || value<=0.0)
        throw std::runtime_error("Command limits must be finite and positive");
    if (heading_resume_threshold_>=heading_error_threshold_ || heading_error_threshold_>M_PI)
      throw std::runtime_error("Heading resume threshold must be below the turn threshold");
    kp_pos_ = declare_parameter<double>("kp_pos", 0.8);
    kp_yaw_ = declare_parameter<double>("kp_yaw", 1.5);
    max_vx_ = declare_parameter<double>("max_vx", 0.75);
    max_vy_ = declare_parameter<double>("max_vy", 0.35);
    max_vyaw_ = std::min(declare_parameter<double>("max_vyaw", 1.0), kMaxVYawLimit);
    finish_dist_ = declare_parameter<double>("finish_dist", 0.15);
    goal_xy_tolerance_ = declare_parameter<double>("goal_xy_tolerance", 0.25);
    goal_yaw_tolerance_ = declare_parameter<double>("goal_yaw_tolerance", 0.25);
    goal_z_tolerance_ = declare_parameter<double>("goal_z_tolerance", 0.20);
    route_lookahead_heading_enabled_ = declare_parameter<bool>("route_lookahead_heading_enabled", false);
    route_lookahead_dist_ = declare_parameter<double>("route_lookahead_dist", 0.5);
    if (!std::isfinite(route_lookahead_dist_) || route_lookahead_dist_ <= 0.0)
      throw std::runtime_error("Route lookahead distance must be finite and positive");
    for (double tolerance : {goal_xy_tolerance_, goal_yaw_tolerance_, goal_z_tolerance_})
      if (!std::isfinite(tolerance) || tolerance <= 0.0)
        throw std::runtime_error("Goal tolerances must be finite and positive");
    // Nav2 owns control scheduling and command publication. No input callbacks
    // or command timer are created here; the plugin serializes explicit calls.
    execution_frozen_pub_ = create_publisher<std_msgs::msg::Bool>("planning/go2_execution_frozen", 10);
    last_update_time_ = now();
    RCLCPP_INFO(get_logger(), "SCAN tracking core: Nav2 owns scheduling; no standalone command timer");
  }

public:
  static constexpr double kMaxVYawLimit = 1.0;

  static bool validGoalPose(const geometry_msgs::msg::Pose &pose)
  {
    const auto &p = pose.position;
    const auto &q = pose.orientation;
    const double norm2 = q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w;
    return std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z) &&
        std::isfinite(norm2) && std::abs(norm2 - 1.0) <= 1e-6;
  }

  void setReferencePath(const nav_msgs::msg::Path &path)
  {
    const bool same_goal = goal_pose_valid_ && !path.poses.empty() &&
        path.poses.back().pose == goal_pose_;
    reference_path_ = path;
    goal_pose_valid_ = !path.poses.empty() && validGoalPose(path.poses.back().pose);
    if (!same_goal) {
      goal_position_latched_ = false;
      turning_in_place_ = false;
      expired_braking_ = false;
    }
    if (!path.poses.empty()) {
      goal_pose_ = path.poses.back().pose;
      goal_pos_ << goal_pose_.position.x, goal_pose_.position.y, goal_pose_.position.z;
      if (goal_pose_valid_) goal_yaw_ = tf2::getYaw(goal_pose_.orientation);
    }
  }

  void pathCallback(nav_msgs::msg::Path::ConstSharedPtr msg)
  {
    if (msg) setReferencePath(*msg);
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

  bool estimateRouteLookaheadYaw(const Eigen::Vector3d &reference_pos, double &yaw_out) const
  {
    if (!route_lookahead_heading_enabled_ || !goal_pose_valid_ || reverse_motion_ ||
        goal_position_latched_ || !have_odom_ || reference_path_.poses.empty())
      return false;
    if ((goal_pos_ - odom_pos_).head<2>().norm() <= goal_xy_tolerance_ &&
        std::abs(goal_pos_.z() - odom_pos_.z()) <= goal_z_tolerance_)
      return false;

    const auto &poses = reference_path_.poses;
    const auto point = [&](size_t i) {
      const auto &p = poses[i].pose.position;
      return Eigen::Vector3d(p.x, p.y, p.z);
    };
    size_t best_seg = 0;
    double best_t = 0.0;
    double best_distance = std::numeric_limits<double>::infinity();
    // Use 3D projection so overlapping XY routes on different floors stay distinct.
    for (size_t i = 0; i + 1 < poses.size(); ++i)
    {
      const Eigen::Vector3d start = point(i);
      const Eigen::Vector3d segment = point(i + 1) - start;
      const double length2 = segment.squaredNorm();
      const double t = length2 > 0.0 ?
          std::clamp((reference_pos - start).dot(segment) / length2, 0.0, 1.0) : 0.0;
      const double distance = (start + t * segment - reference_pos).squaredNorm();
      if (distance < best_distance)
      {
        best_distance = distance;
        best_seg = i;
        best_t = t;
      }
    }
    Eigen::Vector3d carrot = point(best_seg);
    if (best_seg + 1 < poses.size())
      carrot += best_t * (point(best_seg + 1) - carrot);
    double remaining = route_lookahead_dist_;
    for (size_t i = best_seg; i + 1 < poses.size(); ++i)
    {
      const Eigen::Vector3d segment = point(i + 1) - carrot;
      const double length = segment.norm();
      if (length > 0.0 && remaining <= length)
      {
        carrot += (remaining / length) * segment;
        break;
      }
      remaining -= length;
      carrot = point(i + 1);
    }
    Eigen::Vector2d dir = (carrot - reference_pos).head<2>();
    if (dir.squaredNorm() < 1e-4)
      dir = (carrot - odom_pos_).head<2>();
    if (dir.squaredNorm() < 1e-4) return false;
    yaw_out = std::atan2(dir.y(), dir.x());
    return true;
  }

  double estimateDesiredYaw(double t_cur, const Eigen::Vector3d &pos_des,
                            bool *used_route_lookahead = nullptr) const
  {
    if (used_route_lookahead) *used_route_lookahead = false;
    const double t_look = std::min(traj_duration_, t_cur + time_forward_);
    Eigen::Vector3d direction = traj_[0].evaluateDeBoorT(t_look) - pos_des;
    if (direction.head<2>().squaredNorm() < 1e-4)
      direction = traj_[1].evaluateDeBoorT(t_cur);
    if (direction.head<2>().squaredNorm() < 1e-4)
    {
      double route_yaw = odom_yaw_;
      if (estimateRouteLookaheadYaw(pos_des, route_yaw))
      {
        if (used_route_lookahead) *used_route_lookahead = true;
        return route_yaw;
      }
      return odom_yaw_;
    }
    const double tangent=std::atan2(direction.y(),direction.x());
    return reverse_motion_?normalizeAngle(tangent+M_PI):tangent;
  }

  void publishVelocity(const geometry_msgs::msg::Twist &cmd)
  {
    // Do not let a limiter conceal invalid tracking output from LocalMotion.
    if (!std::isfinite(cmd.linear.x) || !std::isfinite(cmd.linear.y) || !std::isfinite(cmd.angular.z)) {
      sampled_command_=cmd;
      return;
    }
    sampled_command_ = slew_.update(cmd, now().nanoseconds());
  }

  void hardStop()
  {
    slew_.reset();
    sampled_command_ = geometry_msgs::msg::Twist();
  }

  void publishStop(double yaw_rate = 0.0)
  {
    geometry_msgs::msg::Twist cmd;
    cmd.angular.z = std::clamp(yaw_rate, -max_vyaw_, max_vyaw_);
    publishVelocity(cmd);
  }

  void publishExecutionFrozen(bool frozen)
  {
    execution_frozen_=frozen;
    execution_frozen_trajectory_=traj_id_;
    std_msgs::msg::Bool msg;
    msg.data = frozen;
    execution_frozen_pub_->publish(msg);
  }

  bool executionFrozen() const {return execution_frozen_;}
  int64_t executionFrozenTrajectory() const {return execution_frozen_trajectory_;}
  bool execution_frozen_{false};
  int64_t execution_frozen_trajectory_{-1};

  void bsplineCallback(const scan_planner_msgs::msg::Bspline::ConstSharedPtr msg)
  {
    if (!msg || msg->pos_pts.empty() || msg->knots.empty() || msg->order != 3)
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
    Eigen::MatrixXd points(3, msg->pos_pts.size());
    for (size_t i = 0; i < msg->pos_pts.size(); ++i)
      points.col(i) << msg->pos_pts[i].x, msg->pos_pts[i].y, msg->pos_pts[i].z;
    Eigen::VectorXd knots(msg->knots.size());
    for (size_t i = 0; i < msg->knots.size(); ++i) knots(i) = msg->knots[i];
    if (!reactive_stair::validSplineLayout(points, knots, 3)) {
      RCLCPP_WARN(get_logger(), "Ignoring malformed cubic B-spline");
      return;
    }
    UniformBspline position(points, msg->order, 0.1);
    position.setKnot(knots);
    traj_ = {position, position.getDerivative()};
    traj_.push_back(traj_[1].getDerivative());
    traj_duration_ = traj_[0].getTimeSum();
    traj_id_ = msg->traj_id;
    reverse_motion_ = msg->reverse_motion;
    // Consume the producer's sampled epoch once. Subsequent command ticks keep
    // the original incremental phase, including heading/final-yaw freezing.
    exec_time_ = msg->emergency_stop ? 0.0 :
        std::clamp((receipt_time - trajectory_origin).seconds(), 0.0, traj_duration_);
    last_update_time_ = receipt_time;
    receive_traj_ = true;
    expired_braking_ = false; // A new native curve can resume the same route.
    emergency_stop_ = msg->emergency_stop;
    if (emergency_stop_)
    {
      goal_position_latched_ = false;
      publishExecutionFrozen(false);
      turning_in_place_ = false;
      hardStop();
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
      hardStop();
      return;
    }
    if (!receive_traj_ || !have_odom_)
    {
      publishExecutionFrozen(false);
      hardStop();
      return;
    }
    const auto current_time = now();
    if (goal_pose_valid_ && !reverse_motion_)
    {
      const bool within_xy = (goal_pos_ - odom_pos_).head<2>().norm() <= goal_xy_tolerance_;
      const bool within_z = std::abs(goal_pos_.z() - odom_pos_.z()) <= goal_z_tolerance_;
      goal_position_latched_ = within_xy && within_z;
      // Nav2 stateful goal checking: once in XY tolerance, align final yaw.
      if (goal_position_latched_ && within_z)
      {
        const double error = normalizeAngle(goal_yaw_ - odom_yaw_);
        if (std::abs(error) <= goal_yaw_tolerance_ && !within_xy)
          goal_position_latched_ = false; // Reacquire strict final XY after yaw drift.
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
    bool used_route_lookahead = false;
    const double yaw_error = normalizeAngle(estimateDesiredYaw(t_eval, pos_des, &used_route_lookahead) - odom_yaw_);
    const double yaw_command = std::clamp(kp_yaw_ * yaw_error, -max_vyaw_, max_vyaw_);
    const double heading_error = std::abs(yaw_error);
    // Keep turning and translating together. Slow phase by the same effective
    // travel ratio so a turning robot does not chase a full-speed future point.
    const double u=std::clamp((heading_error-heading_resume_threshold_) /
        (heading_error_threshold_-heading_resume_threshold_),0.0,1.0);
    const double translation_scale=0.2+0.8*(1.0-u*u*(3.0-2.0*u));
    turning_in_place_=false;
    publishExecutionFrozen(false);
    exec_time_ = std::min(traj_duration_, exec_time_ + dt*translation_scale);
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
    const double unscaled_speed=std::hypot(command.linear.x,command.linear.y);
    command.linear.x*=translation_scale;
    command.linear.y*=translation_scale;
    // Only an expired curve may latch this stop. Small active corrections and
    // yaw-induced slowing are not classified as low-speed terminal creep.
    if (exec_time_ >= traj_duration_ &&
        (pos_error.norm() < finish_dist_ || unscaled_speed < expired_min_walk_speed_))
      expired_braking_ = true;
    if (expired_braking_)
    {
      command.linear.x = 0.0;
      command.linear.y = 0.0;
      command.linear.z = 0.0;
      command.angular.z = 0.0;
    }
    publishVelocity(command);
  }

  void clearTrajectory()
  {
    receive_traj_ = false;
    emergency_stop_ = false;
    goal_position_latched_ = false;
    traj_.clear();
    exec_time_ = 0.0;
    turning_in_place_ = false;
    expired_braking_ = false;
    hardStop();
    publishExecutionFrozen(false);
  }

  bool haveTrajectory() const { return receive_traj_ && !emergency_stop_ && !traj_.empty(); }
  // Expired-curve braking is not a usable route continuation. Final yaw
  // alignment still has an explicit goal and must not trigger route recovery.
  bool awaitingReplacement() const { return expired_braking_ && !goal_position_latched_; }

  struct CommandSample { bool valid{false}; geometry_msgs::msg::Twist twist; };
  CommandSample sampleCommand(const geometry_msgs::msg::Pose &pose,
                             const geometry_msgs::msg::Twist &, bool update)
  {
    if (!haveTrajectory() || !validGoalPose(pose)) return {};
    geometry_msgs::msg::PoseStamped stamped;
    stamped.pose = pose;
    stamped.header.stamp = now();
    if (update) return {true, sample(stamped)};
    return {true, sampled_command_};
  }

  geometry_msgs::msg::Twist sampled_command_;
  geometry_msgs::msg::Twist sample(const geometry_msgs::msg::PoseStamped &pose) {
    auto odom = std::make_shared<nav_msgs::msg::Odometry>();
    odom->header = pose.header;
    odom->pose.pose = pose.pose;
    odomCallback(odom);
    cmdCallback();
    return sampled_command_;
  }
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr raw_cmd_pub_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr execution_frozen_pub_;
  rclcpp::Subscription<scan_planner_msgs::msg::Bspline>::SharedPtr bspline_sub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr goal_sub_;
  nav_msgs::msg::Path reference_path_;
  geometry_msgs::msg::Pose goal_pose_;
  bool goal_pose_valid_{false};
  Eigen::Vector3d goal_pos_{Eigen::Vector3d::Zero()};
  double goal_yaw_{0.0};
  bool goal_position_latched_{false};
  double goal_xy_tolerance_, goal_yaw_tolerance_, goal_z_tolerance_;
  bool route_lookahead_heading_enabled_;
  double route_lookahead_dist_;
  rclcpp::TimerBase::SharedPtr cmd_timer_;
  bool receive_traj_{false};
  bool reverse_motion_{false};
  bool emergency_stop_{false};
  bool have_odom_{false};
  std::vector<UniformBspline> traj_;
  double traj_duration_{0.0};
  std::int64_t traj_id_{0};
  Eigen::Vector3d odom_pos_{Eigen::Vector3d::Zero()};
  double odom_yaw_{0.0};
  double exec_time_{0.0};
  rclcpp::Time last_update_time_{0, 0, RCL_ROS_TIME};
  double time_forward_, heading_error_threshold_, kp_pos_, kp_yaw_;
  double heading_resume_threshold_, expired_min_walk_speed_;
  bool turning_in_place_{false}, expired_braking_{false};
  scan_nav2_controller::CommandSlew slew_;
  double max_vx_, max_vy_, max_vyaw_, finish_dist_;
};
}  // namespace scan_planner
