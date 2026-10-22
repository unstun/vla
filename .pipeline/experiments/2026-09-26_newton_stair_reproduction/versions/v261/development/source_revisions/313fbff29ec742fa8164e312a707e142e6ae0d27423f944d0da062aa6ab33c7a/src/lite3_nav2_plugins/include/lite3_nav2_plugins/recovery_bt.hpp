#pragma once
#include <nav2_behavior_tree/plugins/action/follow_path_action.hpp>
#include <lite3_nav2_interfaces/srv/follow_path_failure.hpp>
#include <behaviortree_cpp_v3/condition_node.h>

namespace lite3_nav2
{
// Foxy FollowPath has an empty result. Read the cause by the exact aborted UUID.
class FollowPathWithFailure : public nav2_behavior_tree::FollowPathAction
{
public:
  FollowPathWithFailure(const std::string &name, const BT::NodeConfiguration &config)
  : FollowPathAction(name, "follow_path", config) {
    failure_client_=node_->create_client<lite3_nav2_interfaces::srv::FollowPathFailure>(
      "/lite3_nav2/follow_path_failure");
  }
  void on_tick() override {
    config().blackboard->set("terminal_settle_timeout", false);
    FollowPathAction::on_tick();
  }
  BT::NodeStatus on_aborted() override {
    auto request=std::make_shared<lite3_nav2_interfaces::srv::FollowPathFailure::Request>();
    request->goal_id=goal_handle_->get_goal_id();
    if(!failure_client_->wait_for_service(server_timeout_))
      throw std::runtime_error("FollowPath failure service unavailable");
    auto future=failure_client_->async_send_request(request);
    if(rclcpp::spin_until_future_complete(node_,future,server_timeout_)!=rclcpp::FutureReturnCode::SUCCESS)
      throw std::runtime_error("FollowPath failure query timed out");
    const auto response=future.get();
    config().blackboard->set("terminal_settle_timeout",response->known && response->terminal_timeout);
    return BT::NodeStatus::FAILURE;
  }
private:
  rclcpp::Client<lite3_nav2_interfaces::srv::FollowPathFailure>::SharedPtr failure_client_;
};

class RetryAllowed : public BT::ConditionNode
{
public:
  RetryAllowed(const std::string &name,const BT::NodeConfiguration &config):ConditionNode(name,config) {}
  static BT::PortsList providedPorts() {return {};}
  BT::NodeStatus tick() override {
    bool terminal=false;
    config().blackboard->get("terminal_settle_timeout",terminal);
    // Consume it here, not in FollowPath::halt(): RecoveryNode halts the failed
    // child before this condition can inspect the cause.
    config().blackboard->set("terminal_settle_timeout",false);
    return terminal ? BT::NodeStatus::FAILURE : BT::NodeStatus::SUCCESS;
  }
};
}
