#pragma once

#include <atomic>
#include <mutex>
#include <nav2_core/controller.hpp>
#include <nav2_core/goal_checker.hpp>
#include <scan_nav2_controller/command_output.hpp>
#include <scan_nav2_controller/tracking_node.hpp>

namespace scan_nav2_controller
{
class NativeWorker;

struct State
{
  std::mutex mutex;
  bool active{false}, goal_reached{false}, stopped{false};
  bool has_goal_pose{false}, pose_valid{false};
  geometry_msgs::msg::Pose goal_pose, pose;
  geometry_msgs::msg::Twist velocity;
  double xy_tolerance{0.25}, z_tolerance{0.20}, yaw_tolerance{0.25};
};

class Controller : public nav2_core::Controller, public CommandOutput
{
public:
  Controller();
  ~Controller() override;
  void configure(const rclcpp_lifecycle::LifecycleNode::SharedPtr &parent,
    std::string name, const std::shared_ptr<tf2_ros::Buffer> &tf,
    const std::shared_ptr<nav2_costmap_2d::Costmap2DROS> &costmap) override;
  void cleanup() override;
  void activate() override;
  void deactivate() override;
  void setPlan(const nav_msgs::msg::Path &path) override;
  // Foxy's Controller interface has two arguments. The overload also supports
  // callers that explicitly supply a goal checker.
  geometry_msgs::msg::TwistStamped computeVelocityCommands(
    const geometry_msgs::msg::PoseStamped &pose,
    const geometry_msgs::msg::Twist &velocity) override;
  geometry_msgs::msg::TwistStamped computeVelocityCommands(
    const geometry_msgs::msg::PoseStamped &pose,
    const geometry_msgs::msg::Twist &velocity, nav2_core::GoalChecker *);
  void bindOutputOwner() override;
  void publishCommand(const geometry_msgs::msg::TwistStamped &command) override;
  void publishCommand(const geometry_msgs::msg::Twist &command);
  void stop(const std::string &reason) override;

private:
  void onSpline(scan_planner_msgs::msg::Bspline::ConstSharedPtr message);
  void spinBridge();
  void serviceNativeWork();
  bool withinGoalPosition(const geometry_msgs::msg::Pose &pose) const;
  bool withinGoalYaw(const geometry_msgs::msg::Pose &pose) const;
  geometry_msgs::msg::TwistStamped stampedCommand(const geometry_msgs::msg::Twist &command);

  rclcpp_lifecycle::LifecycleNode::SharedPtr parent_;
  rclcpp::Node::SharedPtr bridge_;
  std::shared_ptr<scan_planner::TrackingNode> tracker_;
  std::shared_ptr<State> state_;
  std::shared_ptr<rclcpp::executors::SingleThreadedExecutor> executor_;
  std::unique_ptr<NativeWorker> native_worker_;
  std::string name_, global_frame_, base_frame_, route_topic_;
  bool native_worker_enabled_{true};
  bool has_active_plan_{false}, terminal_timeout_started_{false};
  double bspline_timeout_s_{5.0};
  rclcpp::Time route_sent_at_{0, 0, RCL_ROS_TIME};
  rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr route_pub_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr command_pub_;
  rclcpp::Subscription<scan_planner_msgs::msg::Bspline>::SharedPtr spline_sub_;
};

class GoalChecker : public nav2_core::GoalChecker
{
public:
  void initialize(const rclcpp_lifecycle::LifecycleNode::SharedPtr &parent,
    const std::string &name) override;
  void reset() override;
  bool isGoalReached(const geometry_msgs::msg::Pose &query,
    const geometry_msgs::msg::Pose &goal, const geometry_msgs::msg::Twist &velocity) override;
private:
  std::shared_ptr<State> state_;
};
}  // namespace scan_nav2_controller
