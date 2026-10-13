#include <gtest/gtest.h>
#include <behaviortree_cpp_v3/bt_factory.h>
#include <behaviortree_cpp_v3/action_node.h>
#include <nav2_behavior_tree/plugins/control/recovery_node.hpp>
#include <rcl/time.h>
#include "../src/progress_recovery.hpp"

class ScriptAction : public BT::ActionNodeBase {
public:
 ScriptAction(const std::string&name,const BT::NodeConfiguration&config):BT::ActionNodeBase(name,config){}
 static BT::PortsList providedPorts(){return {};}
 BT::NodeStatus tick()override{return config().blackboard->get<std::function<BT::NodeStatus()>>(name())();}
 void halt()override{setStatus(BT::NodeStatus::IDLE);}
};
class ProgressRecoveryTest : public ::testing::Test {
protected:
  rclcpp::Node::SharedPtr node;
  std::shared_ptr<tf2_ros::Buffer> tf;
  BT::BehaviorTreeFactory factory;
  BT::Blackboard::Ptr board;
  bool fail_next=false, goal=false, stop_ready=true, stop_failed=false;
  int stop_calls=0;
  double now_s=10.0;
  void SetUp() override {
    int argc=0;char **argv=nullptr;rclcpp::init(argc,argv);
    rclcpp::NodeOptions options;options.use_global_arguments(false);
    node=std::make_shared<rclcpp::Node>("recovery_budget_test",options);
    ASSERT_EQ(rcl_enable_ros_time_override(node->get_clock()->get_clock_handle()),RCL_RET_OK);
    tf=std::make_shared<tf2_ros::Buffer>(node->get_clock());
    board=BT::Blackboard::create();board->set("node",node);board->set("tf_buffer",tf);
    factory.registerNodeType<lite3_nav2::MeasuredProgressRecovery>("MeasuredProgressRecovery");
    factory.registerNodeType<nav2_behavior_tree::RecoveryNode>("RecoveryNode");
    factory.registerNodeType<ScriptAction>("Navigate");
    factory.registerNodeType<ScriptAction>("MeasuredStop");
    board->set<std::function<BT::NodeStatus()>>("Navigate",[this](){
      if(goal)return BT::NodeStatus::SUCCESS;
      if(fail_next){fail_next=false;return BT::NodeStatus::FAILURE;}
      return BT::NodeStatus::RUNNING;
    });
    board->set<std::function<BT::NodeStatus()>>("MeasuredStop",[this](){
      ++stop_calls;
      if(stop_failed)return BT::NodeStatus::FAILURE;
      return stop_ready?BT::NodeStatus::SUCCESS:BT::NodeStatus::RUNNING;
    });
  }
  void TearDown() override {board.reset();tf.reset();node.reset();rclcpp::shutdown();}
  BT::Tree tree(const std::string &type="MeasuredProgressRecovery") {
    return factory.createTreeFromText("<root main_tree_to_execute=\"Main\"><BehaviorTree ID=\"Main\"><"+
      type+" number_of_retries=\"6\"><Navigate/><MeasuredStop/></"+type+
      "></BehaviorTree></root>",board);
  }
  void pose(double x,double y=0,double z=0,double age=0.01) {
    now_s+=1.0;
    ASSERT_EQ(rcl_set_ros_time_override(node->get_clock()->get_clock_handle(),int64_t(now_s*1e9)),RCL_RET_OK);
    geometry_msgs::msg::TransformStamped p;
    p.header.frame_id="world";p.child_frame_id="base_link";
    p.header.stamp=rclcpp::Time(int64_t((now_s-age)*1e9));
    p.transform.rotation.w=1.0;p.transform.translation.x=x;
    p.transform.translation.y=y;p.transform.translation.z=z;
    ASSERT_TRUE(tf->setTransform(p,"captured-body-test",false));
  }
  BT::NodeStatus stop(BT::Tree &t) {fail_next=true;return t.tickRoot();}
};

TEST_F(ProgressRecoveryTest, CapturedSevenStopsOldAbortsNewContinues) {
  // Actual cancellation poses from v169_mac_full_attempt01; preserved provenance
  // is in results/recorded_retry_trace.json. No synthetic pose is a runtime claim.
  const std::array<std::array<double,3>,7> positions{{
    {8.155710,6.125505,3.344102},{6.593930,-3.861042,3.351131},
    {6.604693,-3.940237,3.351151},{8.925307,2.381505,4.278710},
    {3.494378,2.332686,4.830008},{3.423001,2.234961,4.823999},
    {2.855366,0.035906,4.837882}}};
  auto old=tree("RecoveryNode");auto candidate=tree();
  pose(-5.545315,6.013189,0.198044);
  EXPECT_EQ(old.tickRoot(),BT::NodeStatus::RUNNING);
  EXPECT_EQ(candidate.tickRoot(),BT::NodeStatus::RUNNING);
  for(size_t i=0;i<positions.size();++i){
    const auto&p=positions[i];pose(p[0],p[1],p[2]);
    EXPECT_EQ(stop(old),i<6?BT::NodeStatus::RUNNING:BT::NodeStatus::FAILURE);
    EXPECT_EQ(stop(candidate),BT::NodeStatus::RUNNING);
  }
  goal=true;EXPECT_EQ(candidate.tickRoot(),BT::NodeStatus::SUCCESS);
}
TEST_F(ProgressRecoveryTest, StationaryAndDuplicatePoseKeepSixRetryLimit) {
  auto t=tree();pose(0);EXPECT_EQ(t.tickRoot(),BT::NodeStatus::RUNNING);
  for(int i=0;i<6;++i){pose(0);EXPECT_EQ(stop(t),BT::NodeStatus::RUNNING);}
  EXPECT_EQ(stop(t),BT::NodeStatus::FAILURE);EXPECT_EQ(stop_calls,6);
}
TEST_F(ProgressRecoveryTest, RevisitingCheckpointsCannotRenewBudget) {
  auto t=tree();pose(0);t.tickRoot();pose(3);EXPECT_EQ(stop(t),BT::NodeStatus::RUNNING);
  for(int i=0;i<5;++i){pose(i%2?3:0);EXPECT_EQ(stop(t),BT::NodeStatus::RUNNING);}
  pose(0);EXPECT_EQ(stop(t),BT::NodeStatus::FAILURE);
}
TEST_F(ProgressRecoveryTest, StaleOrFutureTransformsCannotRenewBudget) {
  auto t=tree();pose(0);t.tickRoot();
  for(int i=0;i<6;++i){pose(3*(i+1),0,0,i%2?-0.05:0.2);EXPECT_EQ(stop(t),BT::NodeStatus::RUNNING);}
  pose(30,0,0,0.2);EXPECT_EQ(stop(t),BT::NodeStatus::FAILURE);
}
TEST_F(ProgressRecoveryTest, PhysicalStopMustFinishAndFailureStillAborts) {
  auto t=tree();pose(0);t.tickRoot();stop_ready=false;
  EXPECT_EQ(stop(t),BT::NodeStatus::RUNNING);
  pose(3);EXPECT_EQ(t.tickRoot(),BT::NodeStatus::RUNNING);
  stop_failed=true;EXPECT_EQ(t.tickRoot(),BT::NodeStatus::FAILURE);
}
TEST_F(ProgressRecoveryTest, HaltStartsANewMissionBudget) {
  auto t=tree();pose(0);t.tickRoot();
  for(int i=0;i<6;++i)EXPECT_EQ(stop(t),BT::NodeStatus::RUNNING);
  t.haltTree();
  for(int i=0;i<6;++i)EXPECT_EQ(stop(t),BT::NodeStatus::RUNNING);
  EXPECT_EQ(stop(t),BT::NodeStatus::FAILURE);
}
