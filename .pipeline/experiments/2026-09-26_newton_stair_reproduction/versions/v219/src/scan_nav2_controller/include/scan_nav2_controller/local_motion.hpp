#pragma once

#include <scan_nav2_controller/motion_exchange.hpp>
#include <geometry_msgs/msg/twist.hpp>
#include <std_msgs/msg/header.hpp>
#include <rclcpp/rclcpp.hpp>
#include <rclcpp_lifecycle/lifecycle_node.hpp>

namespace scan_planner {class TrackingNode;}

namespace scan_nav2_controller
{
class NativeWorker;

// Calls are serialized by the controller. The native worker sees only snapshots,
// never this object's mutable tracker, route or command state.
class LocalMotion
{
public:
  struct Tolerances {double xy,z,yaw;};
  LocalMotion(rclcpp_lifecycle::LifecycleNode::SharedPtr parent,
              rclcpp::Node::SharedPtr observations,const std::string &name);
  ~LocalMotion();
  void activate();
  void deactivate();
  bool setRoute(const nav_msgs::msg::Path &path); // Returns true for the same goal.
  void update();
  geometry_msgs::msg::Twist command(const geometry_msgs::msg::Pose &pose,
                                  const geometry_msgs::msg::Twist &velocity);
  geometry_msgs::msg::Twist brakeCommand();
  void cancel();
  bool hasRoute() const {return has_active_plan_;}
  Tolerances tolerances() const {return tolerances_;}
private:
  void acceptSpline(const MotionExchange::Output &output);
  void waitForExecutableSpline();
  rclcpp_lifecycle::LifecycleNode::SharedPtr parent_;
  rclcpp::Node::SharedPtr observations_;
  std::string name_,global_frame_,route_topic_;
  Tolerances tolerances_;
  std::shared_ptr<scan_planner::TrackingNode> tracker_;
  std::shared_ptr<rclcpp::executors::SingleThreadedExecutor> executor_;
  std::unique_ptr<NativeWorker> native_worker_;
  std::shared_ptr<MotionExchange> exchange_{std::make_shared<MotionExchange>()};
  rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr route_pub_;
  rclcpp::Publisher<std_msgs::msg::Header>::SharedPtr replan_pub_;
  bool replan_requested_{false};
  bool native_worker_enabled_{true},has_active_plan_{false},waiting_for_spline_{false};
  bool received_spline_{false};
  uint64_t generation_{0};
  double bspline_timeout_s_{5.0},trajectory_starvation_timeout_s_{0.75};
  rclcpp::Time waiting_for_spline_since_{0,0,RCL_ROS_TIME};
  nav_msgs::msg::Path reference_path_;
};
}  // namespace scan_nav2_controller
