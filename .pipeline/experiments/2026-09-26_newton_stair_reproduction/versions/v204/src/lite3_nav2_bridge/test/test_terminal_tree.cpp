#include <gtest/gtest.h>
#include <behaviortree_cpp_v3/bt_factory.h>
#include <lite3_nav2_plugins/recovery_bt.hpp>
#include <thread>
#include <atomic>
using namespace std::chrono_literals;
namespace {
int plans=0,follows=0,waits=0,failures=99;bool plan_failure=false,terminal=false;
class Plan:public BT::SyncActionNode {
public:
  Plan(const std::string &n,const BT::NodeConfiguration &c):SyncActionNode(n,c){}
  static BT::PortsList providedPorts(){return {BT::InputPort<std::string>("goal"),BT::OutputPort<nav_msgs::msg::Path>("path"),BT::InputPort<std::string>("planner_id"),BT::InputPort<std::string>("server_name"),BT::InputPort<std::string>("server_timeout")};}
  BT::NodeStatus tick()override{++plans;setOutput("path",nav_msgs::msg::Path());return plan_failure?BT::NodeStatus::FAILURE:BT::NodeStatus::SUCCESS;}
};
class Follow:public BT::SyncActionNode {
public:
  Follow(const std::string &n,const BT::NodeConfiguration &c):SyncActionNode(n,c){}
  static BT::PortsList providedPorts(){return lite3_nav2::FollowPathWithFailure::providedPorts();}
  BT::NodeStatus tick()override{++follows;config().blackboard->set("terminal_settle_timeout",terminal);return follows<=failures?BT::NodeStatus::FAILURE:BT::NodeStatus::SUCCESS;}
};
class Wait:public BT::SyncActionNode {
public:
  Wait(const std::string &n,const BT::NodeConfiguration &c):SyncActionNode(n,c){}
  static BT::PortsList providedPorts(){return {BT::InputPort<double>("wait_duration"),BT::InputPort<std::string>("server_name"),BT::InputPort<std::string>("server_timeout")};}
  BT::NodeStatus tick()override{++waits;EXPECT_EQ(getInput<double>("wait_duration").value(),1.);return BT::NodeStatus::SUCCESS;}
};
void registerNodes(BT::BehaviorTreeFactory &factory,bool realFollow=false) {
  for(const auto *name:{"pipeline_sequence","rate_controller","recovery_node"})
    factory.registerFromPlugin(std::string("/opt/ros/foxy/lib/libnav2_")+name+"_bt_node.so");
  factory.registerNodeType<Plan>("ComputePathToPose");factory.registerNodeType<Wait>("Wait");
  factory.registerNodeType<lite3_nav2::RetryAllowed>("RetryAllowed");
  if(realFollow)factory.registerNodeType<lite3_nav2::FollowPathWithFailure>("FollowPathWithFailure");
  else {factory.registerNodeType<Follow>("FollowPathWithFailure");factory.registerNodeType<Follow>("FollowPath");}
}
BT::NodeStatus run(BT::Tree &tree) {
  BT::NodeStatus status=BT::NodeStatus::RUNNING;
  const auto until=std::chrono::steady_clock::now()+5s;
  while(status==BT::NodeStatus::RUNNING && std::chrono::steady_clock::now()<until) {
    status=tree.tickRoot();
    if(status==BT::NodeStatus::RUNNING)std::this_thread::sleep_for(1ms);
  }
  return status;
}
}
TEST(RecoveryTree, OrdinaryFailuresMatchFrozenTreeAndNextMissionResets) {
  for(bool planner:{false,true})for(int count:{2,99}) {
    std::vector<int> expected;
    for(const char *file:{LEGACY_TREE,NAVIGATION_TREE}) {
      plans=follows=waits=0;failures=count;plan_failure=planner;terminal=false;
      BT::BehaviorTreeFactory factory;registerNodes(factory);
      auto bb=BT::Blackboard::create();bb->set("goal",std::string("fixed"));
      auto tree=factory.createTreeFromFile(file,bb);
      const auto result=run(tree);
      std::vector<int> observed{plans,follows,waits,int(result)};
      if(expected.empty())expected=observed;else EXPECT_EQ(observed,expected);
      EXPECT_EQ(waits,planner||count==99?6:2);
      if(planner)EXPECT_EQ(plans,7);else EXPECT_EQ(follows,count==99?7:3);
    }
  }
}
TEST(RecoveryTree, TerminalTimeoutDoesNotWaitOrRetryAndFlagIsConsumed) {
  plans=follows=waits=0;failures=99;plan_failure=false;terminal=true;
  BT::BehaviorTreeFactory factory;registerNodes(factory);
  auto bb=BT::Blackboard::create();bb->set("goal",std::string("fixed"));
  auto tree=factory.createTreeFromFile(NAVIGATION_TREE,bb);
  EXPECT_EQ(run(tree),BT::NodeStatus::FAILURE);EXPECT_EQ(plans,1);EXPECT_EQ(follows,1);EXPECT_EQ(waits,0);
  EXPECT_FALSE(bb->get<bool>("terminal_settle_timeout"));
  tree.haltTree();terminal=false;plan_failure=true;plans=follows=waits=0;
  EXPECT_EQ(run(tree),BT::NodeStatus::FAILURE);EXPECT_EQ(plans,7);EXPECT_EQ(waits,6);
}
TEST(RecoveryTree, RealFollowPathActionQueriesItsOwnFailureUuid) {
  int argc=0;rclcpp::init(argc,nullptr);
  auto io=std::make_shared<rclcpp::Node>("failure_fixture");
  auto node=std::make_shared<rclcpp::Node>("failure_bt");
  using Action=nav2_msgs::action::FollowPath;using Handle=rclcpp_action::ServerGoalHandle<Action>;
  rclcpp_action::GoalUUID last{};bool terminal_reply=true;int queries=0;
  auto service=io->create_service<lite3_nav2_interfaces::srv::FollowPathFailure>("/lite3_nav2/follow_path_failure",
    [&](std::shared_ptr<lite3_nav2_interfaces::srv::FollowPathFailure::Request> req,
        std::shared_ptr<lite3_nav2_interfaces::srv::FollowPathFailure::Response> res){
      ++queries;EXPECT_EQ(req->goal_id,last);res->known=req->goal_id==last;res->terminal_timeout=terminal_reply;});
  auto server=rclcpp_action::create_server<Action>(io,"follow_path",
    [](const auto &,auto){return rclcpp_action::GoalResponse::ACCEPT_AND_EXECUTE;},
    [](auto){return rclcpp_action::CancelResponse::ACCEPT;},
    [&](std::shared_ptr<Handle> handle){last=handle->get_goal_id();handle->abort(std::make_shared<Action::Result>());});
  rclcpp::executors::SingleThreadedExecutor executor;executor.add_node(io);
  std::thread thread([&]{executor.spin();});
  {
    BT::BehaviorTreeFactory factory;registerNodes(factory,true);
    auto bb=BT::Blackboard::create();bb->set("node",node);bb->set("server_timeout",1000ms);
    bb->set("bt_loop_duration",10ms);bb->set("goal",std::string("fixed"));
    auto tree=factory.createTreeFromFile(NAVIGATION_TREE,bb);
    plans=follows=waits=0;plan_failure=false;
    EXPECT_EQ(run(tree),BT::NodeStatus::FAILURE);EXPECT_EQ(queries,1);EXPECT_EQ(plans,1);EXPECT_EQ(waits,0);
    tree.haltTree();terminal_reply=false;plans=waits=0;queries=0;
    EXPECT_EQ(run(tree),BT::NodeStatus::FAILURE);EXPECT_EQ(queries,7);EXPECT_EQ(plans,7);EXPECT_EQ(waits,6);
  }
  executor.cancel();thread.join();executor.remove_node(io);server.reset();service.reset();node.reset();io.reset();rclcpp::shutdown();
}
