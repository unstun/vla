#include <gtest/gtest.h>
#include <lite3_nav2_plugins/pct_route_planner.hpp>
#include <nav2_core/global_planner.hpp>
#include <nav2_core/exceptions.hpp>
#include <pluginlib/class_loader.hpp>
#include <cstdlib>
#include <fstream>
#include <limits>
#include <thread>

class PCTTest : public ::testing::Test
{
protected:
  static void SetUpTestCase(){int argc=0;rclcpp::init(argc,nullptr);}
  static void TearDownTestCase(){rclcpp::shutdown();}
  void SetUp() override {
    ASSERT_NE(std::getenv("PCT_TEST_MAP"),nullptr);
    bundle=std::getenv("PCT_TEST_MAP");
    parent=std::make_shared<rclcpp_lifecycle::LifecycleNode>("pct_direct_test");
    parent->declare_parameter("PCT.map_bundle",bundle);
    loader=std::make_unique<pluginlib::ClassLoader<nav2_core::GlobalPlanner>>("nav2_core","nav2_core::GlobalPlanner");
    plugin=loader->createSharedInstance("lite3_nav2/PCTPlanner");
    plugin->configure(parent,"PCT",nullptr,nullptr);
    plugin->activate();
    start.header.frame_id=goal.header.frame_id="world";
    start.pose.orientation.w=goal.pose.orientation.w=1.;
    start.pose.position.x=.5;start.pose.position.y=-4.;start.pose.position.z=.5;
    goal.pose.position.x=3.5;goal.pose.position.y=-2.;goal.pose.position.z=.5;
  }
  void TearDown() override {
    if(plugin){plugin->deactivate();plugin->cleanup();}
    plugin.reset();loader.reset();parent.reset();
  }
  std::string bundle;
  rclcpp_lifecycle::LifecycleNode::SharedPtr parent;
  std::unique_ptr<pluginlib::ClassLoader<nav2_core::GlobalPlanner>> loader;
  nav2_core::GlobalPlanner::Ptr plugin;
  geometry_msgs::msg::PoseStamped start,goal;
};

TEST_F(PCTTest, PlansDirectlyWithNoMissionServiceAndPreservesZeroYaw)
{
  const auto services=parent->get_service_names_and_types();
  EXPECT_EQ(services.count("/lite3_nav2/plan_route"),0u);
  const auto path=plugin->createPlan(start,goal);
  ASSERT_GT(path.poses.size(),2u);EXPECT_EQ(path.header.frame_id,"world");
  EXPECT_EQ(path.poses.back().pose,goal.pose);
  for(const auto &pose:path.poses) {
    EXPECT_EQ(pose.header,path.header);
    EXPECT_NEAR(pose.pose.position.z,.5,0.01); // No discarded +0.5 m wrapper offset.
  }
}
TEST_F(PCTTest, FailureNeverReturnsPreviousOptimizerRoute)
{
  ASSERT_GT(plugin->createPlan(start,goal).poses.size(),2u);
  EXPECT_THROW(plugin->createPlan(goal,goal),nav2_core::PlannerException);
  ASSERT_GT(plugin->createPlan(start,goal).poses.size(),2u);
}
TEST_F(PCTTest, ChangedGoalAndExplicitYawAreImmediatelyRespected)
{
  plugin->createPlan(start,goal);
  goal.pose.position.x=3.25;goal.pose.orientation.z=std::sin(.35);goal.pose.orientation.w=std::cos(.35);
  const auto path=plugin->createPlan(start,goal);
  EXPECT_EQ(path.poses.back().pose,goal.pose);
}
TEST_F(PCTTest, InactiveAndMalformedRequestsAreRejected)
{
  plugin->deactivate();EXPECT_THROW(plugin->createPlan(start,goal),nav2_core::PlannerException);
  plugin->activate();auto bad=start;bad.header.frame_id="map";
  EXPECT_THROW(plugin->createPlan(bad,goal),nav2_core::PlannerException);
  bad=start;bad.pose.position.x=std::numeric_limits<double>::quiet_NaN();
  EXPECT_THROW(plugin->createPlan(bad,goal),nav2_core::PlannerException);
  bad=start;bad.pose.orientation.w=2.;
  EXPECT_THROW(plugin->createPlan(bad,goal),nav2_core::PlannerException);
  bad=start;bad.pose.position.x=500.;
  EXPECT_THROW(plugin->createPlan(bad,goal),nav2_core::PlannerException);
}
TEST_F(PCTTest, MapBundleMustBePresentAndVersioned)
{
  EXPECT_THROW(lite3_nav2::PCTRoutePlanner("/not/a/pct/map",.35),std::runtime_error);
  const auto invalid=bundle+".invalid";
  {std::ofstream out(invalid);out<<"PCTMAP00";}
  EXPECT_THROW(lite3_nav2::PCTRoutePlanner(invalid,.35),std::runtime_error);
  std::remove(invalid.c_str());
}
