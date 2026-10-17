#include <gtest/gtest.h>
#include <behaviortree_cpp_v3/bt_factory.h>

namespace
{
int plans=0, follows=0;
class Plan : public BT::SyncActionNode
{
public:
  Plan(const std::string &name,const BT::NodeConfiguration &config): SyncActionNode(name,config) {}
  static BT::PortsList providedPorts() {
    return {BT::InputPort<std::string>("goal"),BT::OutputPort<std::string>("path"),
      BT::InputPort<std::string>("planner_id"),BT::InputPort<std::string>("server_name"),
      BT::InputPort<std::string>("server_timeout")};
  }
  BT::NodeStatus tick() override {++plans;setOutput("path",std::string("fixed"));return BT::NodeStatus::SUCCESS;}
};
class Follow : public BT::SyncActionNode
{
public:
  Follow(const std::string &name,const BT::NodeConfiguration &config): SyncActionNode(name,config) {}
  static BT::PortsList providedPorts() {
    return {BT::InputPort<std::string>("path"),BT::InputPort<std::string>("controller_id"),
      BT::InputPort<std::string>("server_name"),BT::InputPort<std::string>("server_timeout")};
  }
  BT::NodeStatus tick() override {++follows;return BT::NodeStatus::FAILURE;}
};
}

TEST(TerminalTree, FollowFailureExitsImmediatelyWithoutWaitOrRouteReplay)
{
  plans=0;follows=0;
  BT::BehaviorTreeFactory factory;
  factory.registerFromPlugin("/opt/ros/foxy/lib/libnav2_pipeline_sequence_bt_node.so");
  factory.registerFromPlugin("/opt/ros/foxy/lib/libnav2_rate_controller_bt_node.so");
  factory.registerNodeType<Plan>("ComputePathToPose");
  factory.registerNodeType<Follow>("FollowPath");
  auto blackboard=BT::Blackboard::create();blackboard->set("goal",std::string("target"));
  auto tree=factory.createTreeFromFile(NAVIGATION_TREE,blackboard);
  EXPECT_EQ(tree.tickRoot(),BT::NodeStatus::FAILURE);
  EXPECT_EQ(plans,1);EXPECT_EQ(follows,1);
}
