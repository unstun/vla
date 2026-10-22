#include <gtest/gtest.h>
#include <behaviortree_cpp_v3/bt_factory.h>
#include <behaviortree_cpp_v3/action_node.h>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <nav_msgs/msg/path.hpp>
#include <std_msgs/msg/header.hpp>
#include <rclcpp/rclcpp.hpp>
#include <thread>
#include <chrono>

namespace {
using Pose = geometry_msgs::msg::PoseStamped;
using Status = BT::NodeStatus;
int starts, ticks, cancels, follows, waits;
bool finish_plan, fail_plan, fail_follow, terminal;
Pose requested;

class Plan : public BT::ActionNodeBase {
public:
  Plan(const std::string &n, const BT::NodeConfiguration &c): ActionNodeBase(n,c) {}
  static BT::PortsList providedPorts() {
    return {BT::InputPort<Pose>("goal"), BT::OutputPort<nav_msgs::msg::Path>("path"),
      BT::InputPort<std::string>("planner_id"), BT::InputPort<std::string>("server_name"),
      BT::InputPort<std::string>("server_timeout")};
  }
  Status tick() override {
    ++ticks;
    if (status() != Status::RUNNING) { ++starts; requested = getInput<Pose>("goal").value(); }
    if (fail_plan) return Status::FAILURE;
    if (!finish_plan) return Status::RUNNING;
    nav_msgs::msg::Path path;path.header.frame_id="world";path.header.stamp.sec=starts;
    path.poses.push_back(requested); setOutput("path",path);
    return Status::SUCCESS;
  }
  void halt() override {if(status()==Status::RUNNING) ++cancels;setStatus(Status::IDLE);}
};
class Follow : public BT::ActionNodeBase {
public:
  Follow(const std::string &n,const BT::NodeConfiguration &c):ActionNodeBase(n,c){}
  static BT::PortsList providedPorts(){return {BT::InputPort<nav_msgs::msg::Path>("path"),
    BT::InputPort<std::string>("controller_id"),BT::InputPort<std::string>("server_name"),
    BT::InputPort<std::string>("server_timeout")};}
  Status tick() override {
    ++follows;config().blackboard->set("terminal_settle_timeout",terminal);
    return fail_follow ? Status::FAILURE : Status::RUNNING;
  }
  void halt() override {setStatus(Status::IDLE);}
};
class Wait : public BT::SyncActionNode {
public:
  Wait(const std::string &n,const BT::NodeConfiguration &c):SyncActionNode(n,c){}
  static BT::PortsList providedPorts(){return {BT::InputPort<double>("wait_duration"),
    BT::InputPort<std::string>("server_name"),BT::InputPort<std::string>("server_timeout")};}
  Status tick() override {++waits;EXPECT_EQ(getInput<double>("wait_duration").value(),1.);return Status::SUCCESS;}
};

class EventPlanning : public ::testing::Test {
protected:
  static void SetUpTestCase(){int argc=0;rclcpp::init(argc,nullptr);}
  static void TearDownTestCase(){rclcpp::shutdown();}
  rclcpp::Node::SharedPtr node;
  rclcpp::Publisher<std_msgs::msg::Header>::SharedPtr request;
  BT::BehaviorTreeFactory factory;
  BT::Blackboard::Ptr board;
  Pose goal;
  void SetUp() override {
    starts=ticks=cancels=follows=waits=0;
    finish_plan=true;fail_plan=fail_follow=terminal=false;
    for(const auto *name:{"pipeline_sequence","rate_controller","recovery_node"})
      factory.registerFromPlugin(std::string("/opt/ros/foxy/lib/libnav2_")+name+"_bt_node.so");
    // Load the installed production plugin, not a recompiled test-only copy.
    factory.registerFromPlugin("/work/install/lite3_nav2_plugins/lib/liblite3_nav2_route_bt.so");
    factory.unregisterBuilder("FollowPathWithFailure");
    factory.registerNodeType<Plan>("ComputePathToPose");
    factory.registerNodeType<Follow>("FollowPathWithFailure");
    factory.registerNodeType<Follow>("FollowPath");
    factory.registerNodeType<Wait>("Wait");
    board=BT::Blackboard::create();goal.header.frame_id="world";
    node=std::make_shared<rclcpp::Node>("test_event_requests");board->set("node",node);
    request=node->create_publisher<std_msgs::msg::Header>("/scan/replan_request",rclcpp::QoS(1).reliable());
    goal.pose.position.x=5.;goal.pose.orientation.w=1.;board->set("goal",goal);
  }
  BT::Tree tree(const char *file=NAVIGATION_TREE){return factory.createTreeFromFile(file,board);}
  void update(){board->set("goal",goal);}
};

TEST_F(EventPlanning, CurrentRouteFailureReplansWithoutStoppingFollowPath) {
  auto t=tree();t.tickRoot();
  const auto header=board->get<nav_msgs::msg::Path>("path").header;
  for(int i=0;i<100 && !request->get_subscription_count();++i)std::this_thread::sleep_for(std::chrono::milliseconds(5));
  ASSERT_GT(request->get_subscription_count(),0u);
  finish_plan=false;request->publish(header);
  for(int i=0;i<100 && starts==1;++i){t.tickRoot();std::this_thread::sleep_for(std::chrono::milliseconds(5));}
  ASSERT_EQ(starts,2);const int before=follows;
  for(int i=0;i<10;++i)t.tickRoot();
  EXPECT_GT(follows,before);EXPECT_EQ(cancels,0);EXPECT_EQ(waits,0);
  finish_plan=true;t.tickRoot();EXPECT_EQ(starts,2);
  request->publish(header); // Old route request cannot invalidate the replacement.
  for(int i=0;i<10;++i){t.tickRoot();std::this_thread::sleep_for(std::chrono::milliseconds(5));}
  EXPECT_EQ(starts,2);
}

TEST_F(EventPlanning, WrongRouteRequestDoesNotReplan) {
  auto t=tree();t.tickRoot();
  for(int i=0;i<100 && !request->get_subscription_count();++i)std::this_thread::sleep_for(std::chrono::milliseconds(5));
  auto header=board->get<nav_msgs::msg::Path>("path").header;header.stamp.sec+=10;
  request->publish(header);
  for(int i=0;i<20;++i){t.tickRoot();std::this_thread::sleep_for(std::chrono::milliseconds(5));}
  EXPECT_EQ(starts,1);
}

TEST_F(EventPlanning, NoPeriodicPlansWhileLocalTrackingKeepsTicking) {
  auto t=tree();ASSERT_EQ(t.tickRoot(),Status::RUNNING);
  for(int i=0;i<1000;++i) ASSERT_EQ(t.tickRoot(),Status::RUNNING);
  std::this_thread::sleep_for(std::chrono::milliseconds(1100));
  ASSERT_EQ(t.tickRoot(),Status::RUNNING);
  EXPECT_EQ(starts,1);EXPECT_EQ(ticks,1);EXPECT_EQ(follows,1002);EXPECT_EQ(waits,0);
}
TEST_F(EventPlanning, FrozenPeriodicTreeStillReplansAfterOneSecond) {
  auto t=tree(LEGACY_TREE);t.tickRoot();EXPECT_EQ(starts,1);
  std::this_thread::sleep_for(std::chrono::milliseconds(1100));t.tickRoot();
  EXPECT_EQ(starts,2);
}
TEST_F(EventPlanning, PositionOrientationAndFrameChangesEachPlanOnce) {
  auto t=tree();t.tickRoot();
  goal.pose.position.x+=1.;update();t.tickRoot();EXPECT_EQ(starts,2);
  goal.pose.orientation.z=.2;goal.pose.orientation.w=.98;update();t.tickRoot();EXPECT_EQ(starts,3);
  goal.header.frame_id="map";update();t.tickRoot();EXPECT_EQ(starts,4);
  for(int i=0;i<10;++i)t.tickRoot();EXPECT_EQ(starts,4);
}
TEST_F(EventPlanning, StampOnlyRefreshDoesNotPlan) {
  auto t=tree();t.tickRoot();
  for(int i=1;i<100;++i){goal.header.stamp.sec=i;update();t.tickRoot();}
  EXPECT_EQ(starts,1);
}
TEST_F(EventPlanning, InFlightGoalReplacementCancelsOldAndPublishesOnlyNewPath) {
  finish_plan=false;auto t=tree();
  for(int i=0;i<20;++i)EXPECT_EQ(t.tickRoot(),Status::RUNNING);
  EXPECT_EQ(starts,1);EXPECT_EQ(follows,0);
  goal.pose.position.y=2.;update();t.tickRoot();EXPECT_EQ(starts,2);EXPECT_EQ(cancels,1);
  finish_plan=true;t.tickRoot();
  EXPECT_EQ(board->get<nav_msgs::msg::Path>("path").poses.back(),goal);
  EXPECT_EQ(starts,2);EXPECT_EQ(follows,1);
}
TEST_F(EventPlanning, CancelAndNewMissionWithSamePoseMustPlanAgain) {
  auto t=tree();t.tickRoot();t.haltTree();t.tickRoot();EXPECT_EQ(starts,2);
  finish_plan=false;goal.pose.position.y=1.;update();t.tickRoot();
  t.haltTree();EXPECT_EQ(cancels,1);finish_plan=true;t.tickRoot();EXPECT_EQ(starts,4);
}
TEST_F(EventPlanning, OrdinaryFailureReplansWithUnchangedSixRetryBudget) {
  auto t=tree();t.tickRoot();fail_follow=true;
  Status result=Status::RUNNING;
  for(int i=0;i<100 && result==Status::RUNNING;++i)result=t.tickRoot();
  EXPECT_EQ(result,Status::FAILURE);EXPECT_EQ(starts,7);EXPECT_EQ(waits,6);
}
TEST_F(EventPlanning, PlanningFailureRetainsOriginalRetries) {
  fail_plan=true;auto t=tree();Status result=Status::RUNNING;
  for(int i=0;i<100 && result==Status::RUNNING;++i)result=t.tickRoot();
  EXPECT_EQ(result,Status::FAILURE);EXPECT_EQ(starts,7);EXPECT_EQ(waits,6);EXPECT_EQ(follows,0);
}
TEST_F(EventPlanning, TerminalStandTimeoutNeverReplans) {
  auto t=tree();t.tickRoot();terminal=true;fail_follow=true;
  EXPECT_EQ(t.tickRoot(),Status::FAILURE);EXPECT_EQ(starts,1);EXPECT_EQ(waits,0);
}
}
