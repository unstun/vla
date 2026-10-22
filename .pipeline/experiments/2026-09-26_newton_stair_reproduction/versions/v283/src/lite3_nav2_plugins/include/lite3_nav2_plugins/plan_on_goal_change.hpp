#pragma once
#include <behaviortree_cpp_v3/decorator_node.h>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <nav_msgs/msg/path.hpp>
#include <std_msgs/msg/header.hpp>
#include <rclcpp/rclcpp.hpp>
#include <optional>
#include <stdexcept>

namespace lite3_nav2
{
// Keep a successful plan until its requested goal changes or the parent halts
// this branch (cancel, mission completion, or the existing recovery sequence).
class PlanOnGoalChange : public BT::DecoratorNode
{
public:
  PlanOnGoalChange(const std::string &name, const BT::NodeConfiguration &config)
  : BT::DecoratorNode(name, config) {
    // Foxy cannot attach one callback group to a private executor. Keep this
    // event listener separate from the BT action client's shared node.
    rclcpp::NodeOptions options;options.use_global_arguments(false);
    node_=std::make_shared<rclcpp::Node>("scan_replan_event_listener",options);
    request_=node_->create_subscription<std_msgs::msg::Header>("/scan/replan_request",rclcpp::QoS(1).reliable(),
      [this](std_msgs::msg::Header::ConstSharedPtr msg) {pending_=*msg;});
    executor_.add_node(node_);
  }

  static BT::PortsList providedPorts() {
    return {BT::InputPort<geometry_msgs::msg::PoseStamped>("goal"),BT::InputPort<nav_msgs::msg::Path>("reference")};
  }

  BT::NodeStatus tick() override {
    executor_.spin_some();
    // PipelineSequence resets successful children to IDLE without calling halt.
    // Recovery must invalidate that completed plan as well as running actions.
    if (status() == BT::NodeStatus::IDLE) { requested_.reset(); planned_ = false; }
    const auto input = getInput<geometry_msgs::msg::PoseStamped>("goal");
    if (!input) throw std::runtime_error("PlanOnGoalChange requires a goal");
    const auto &goal = input.value();
    // A refreshed timestamp is not a new destination. Frame and full pose are.
    if (!requested_ || requested_->header.frame_id != goal.header.frame_id ||
        requested_->pose != goal.pose) {
      resetChild(); // Cancels an in-flight old-goal action before replacement.
      requested_ = goal;
      planned_ = false;
      pending_.reset();
    }
    if (planned_ && pending_) {
      const auto path=getInput<nav_msgs::msg::Path>("reference");
      if (path && pending_->frame_id==path.value().header.frame_id && pending_->stamp==path.value().header.stamp) {
        // PipelineSequence keeps FollowPath running while this child replans.
        resetChild();planned_=false;
      }
      pending_.reset();
    }
    if (planned_) return BT::NodeStatus::SUCCESS;
    const auto result = child_node_->executeTick();
    if (result == BT::NodeStatus::SUCCESS) planned_ = true;
    // RUNNING continues the same action; FAILURE reaches the existing retry
    // owner. This decorator does not retry, alter the route, or renew a budget.
    return result;
  }

  void halt() override {
    requested_.reset();
    planned_ = false;
    pending_.reset();
    BT::DecoratorNode::halt();
  }

private:
  std::optional<geometry_msgs::msg::PoseStamped> requested_;
  bool planned_{false};
  rclcpp::Node::SharedPtr node_;
  rclcpp::Subscription<std_msgs::msg::Header>::SharedPtr request_;
  rclcpp::executors::SingleThreadedExecutor executor_;
  std::optional<std_msgs::msg::Header> pending_;
};
}
