#pragma once

#include <atomic>
#include <mutex>
#include <nav2_core/controller.hpp>
#include <nav2_core/goal_checker.hpp>
#include <scan_nav2_controller/execution_control.hpp>
#include <scan_nav2_controller/local_motion.hpp>
#include <scan_nav2_controller/terminal_completion.hpp>

namespace scan_nav2_controller
{

struct State
{
  std::mutex mutex;
  bool active{false}, goal_reached{false}, stopped{false};
  bool has_goal_pose{false}, pose_valid{false};
  geometry_msgs::msg::Pose goal_pose, pose;
  geometry_msgs::msg::Twist velocity;
  double xy_tolerance{0.25}, z_tolerance{0.20}, yaw_tolerance{0.25};
  TerminalCompletion completion;
};

class Controller : public nav2_core::Controller, public ExecutionControl
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
  void stop(const std::string &reason) override;
  bool terminalPhase() const override;

private:
  void onExecution(lite3_nav2_interfaces::msg::RobotExecutionState::ConstSharedPtr message);
  void spinBridge();
  bool withinGoalPosition(const geometry_msgs::msg::Pose &pose) const;
  bool withinGoalYaw(const geometry_msgs::msg::Pose &pose, bool braking = false) const;
  geometry_msgs::msg::TwistStamped stampedCommand(const geometry_msgs::msg::Twist &command);

  rclcpp_lifecycle::LifecycleNode::SharedPtr parent_;
  rclcpp::Node::SharedPtr bridge_;
  std::unique_ptr<LocalMotion> motion_;
  std::shared_ptr<State> state_;
  std::shared_ptr<rclcpp::executors::SingleThreadedExecutor> executor_;
  std::string name_,global_frame_,base_frame_;
  bool goal_braking_{false};
  rclcpp::Subscription<lite3_nav2_interfaces::msg::RobotExecutionState>::SharedPtr execution_sub_;
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
  rclcpp::Clock::SharedPtr clock_;
};
}  // namespace scan_nav2_controller
