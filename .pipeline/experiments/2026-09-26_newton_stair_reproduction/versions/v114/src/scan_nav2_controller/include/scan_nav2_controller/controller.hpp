#pragma once

#include <mutex>
#include <map>
#include <thread>
#include <nav2_core/controller.hpp>
#include <nav2_core/goal_checker.hpp>
#include <scan_planner_msgs/msg/p2_b_execution_safety.hpp>
#include <scan_planner_msgs/msg/p2_b_stop_evidence.hpp>
#include <scan_nav2_controller/command_output.hpp>
#include <scan_nav2_controller/tracking_node.hpp>

namespace scan_nav2_controller
{
class NativeWorker;

struct State
{
  std::mutex mutex;
  scan_planner_msgs::msg::P2BRoute::ConstSharedPtr route;
  bool active{false}, stopping{false}, stopped{false};
  double stop_requested_s{0.0};
  double xy_tolerance{0.25}, z_tolerance{0.20}, yaw_tolerance{0.25};
};

class Controller : public nav2_core::Controller, public CommandOutput
{
public:
  ~Controller() override;
  void configure(const rclcpp_lifecycle::LifecycleNode::SharedPtr &parent,
    std::string name, const std::shared_ptr<tf2_ros::Buffer> &tf,
    const std::shared_ptr<nav2_costmap_2d::Costmap2DROS> &costmap) override;
  void cleanup() override;
  void activate() override;
  void deactivate() override;
  void setPlan(const nav_msgs::msg::Path &path) override;
  geometry_msgs::msg::TwistStamped computeVelocityCommands(
    const geometry_msgs::msg::PoseStamped &pose,
    const geometry_msgs::msg::Twist &velocity) override;
  void bindOutputOwner() override;
  void publishCommand(const geometry_msgs::msg::TwistStamped &command) override;
  void stop(const std::string &reason) override;

private:
  void stopLocked(const std::string &reason);
  void onBinding(scan_planner_msgs::msg::P2BRoute::ConstSharedPtr message);
  void onSpline(scan_planner_msgs::msg::Bspline::ConstSharedPtr message);
  void onCancel(scan_planner_msgs::msg::P2BCancel::ConstSharedPtr message);
  void onSafety(scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr message);
  void activateProvenCandidate(double now); // Caller holds state_->mutex; one decision time.
  void onStopEvidence(scan_planner_msgs::msg::P2BStopEvidence::ConstSharedPtr message);
  geometry_msgs::msg::TwistStamped ticket(const geometry_msgs::msg::Twist &command);

  rclcpp_lifecycle::LifecycleNode::SharedPtr parent_;
  rclcpp::Node::SharedPtr bridge_;
  std::shared_ptr<scan_planner::TrackingNode> tracker_;
  std::shared_ptr<State> state_;
  std::shared_ptr<rclcpp::executors::SingleThreadedExecutor> executor_;
  std::thread thread_;
  std::atomic<bool> thread_finished_{true};
  std::unique_ptr<NativeWorker> native_worker_;
  std::string name_, global_frame_, base_frame_;
  double binding_timeout_s_{2.0}, startup_timeout_s_{2.0};
  double pose_timeout_s_{0.1}, safety_timeout_s_{0.1}, observation_timeout_s_{0.25};
  double binding_received_s_{0.0}, plan_started_s_{0.0}, spline_received_s_{0.0};
  int64_t generation_high_water_{0};
  scan_planner_msgs::msg::P2BRoute::ConstSharedPtr pending_;
  scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr safety_;
  std::map<int64_t,scan_planner_msgs::msg::Bspline::ConstSharedPtr> candidate_curves_;
  std::map<int64_t,scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr> candidate_proofs_;
  double first_candidate_received_s_{0.0};
  geometry_msgs::msg::TwistStamped ticket_;
  scan_planner_msgs::msg::P2BStampedTwist ticket_identity_;
  double ticket_body_stamp_s_{0.0}; // Original body time, not the later ticket creation time.
  bool ticket_ready_{false};
  bool output_owner_bound_{false};
  rclcpp::Publisher<scan_planner_msgs::msg::P2BRoute>::SharedPtr route_pub_;
  rclcpp::Publisher<scan_planner_msgs::msg::P2BRoute>::SharedPtr binding_ready_pub_;
  rclcpp::Publisher<scan_planner_msgs::msg::P2BCancel>::SharedPtr cancel_pub_;
  rclcpp::Publisher<scan_planner_msgs::msg::P2BAdmission>::SharedPtr cancel_admission_pub_;
  rclcpp::Publisher<scan_planner_msgs::msg::P2BStampedTwist>::SharedPtr command_pub_;
  rclcpp::Subscription<scan_planner_msgs::msg::P2BRoute>::SharedPtr binding_sub_;
  rclcpp::Subscription<scan_planner_msgs::msg::Bspline>::SharedPtr spline_sub_;
  rclcpp::Subscription<scan_planner_msgs::msg::P2BCancel>::SharedPtr cancel_sub_;
  rclcpp::Subscription<scan_planner_msgs::msg::P2BExecutionSafety>::SharedPtr safety_sub_;
  rclcpp::Subscription<scan_planner_msgs::msg::P2BStopEvidence>::SharedPtr stopped_sub_;
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
