#pragma once
#include <behaviortree_cpp_v3/decorator_node.h>
#include <geometry_msgs/msg/pose_stamped.hpp>
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
  : BT::DecoratorNode(name, config) {}

  static BT::PortsList providedPorts() {
    return {BT::InputPort<geometry_msgs::msg::PoseStamped>("goal")};
  }

  BT::NodeStatus tick() override {
    const auto input = getInput<geometry_msgs::msg::PoseStamped>("goal");
    if (!input) throw std::runtime_error("PlanOnGoalChange requires a goal");
    const auto &goal = input.value();
    // A refreshed timestamp is not a new destination. Frame and full pose are.
    if (!requested_ || requested_->header.frame_id != goal.header.frame_id ||
        requested_->pose != goal.pose) {
      resetChild(); // Cancels an in-flight old-goal action before replacement.
      requested_ = goal;
      planned_ = false;
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
    BT::DecoratorNode::halt();
  }

private:
  std::optional<geometry_msgs::msg::PoseStamped> requested_;
  bool planned_{false};
};
}
