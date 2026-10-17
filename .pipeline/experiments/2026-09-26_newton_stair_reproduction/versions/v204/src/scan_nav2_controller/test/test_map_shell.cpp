#include <gtest/gtest.h>
#include <nav2_costmap_2d/costmap_2d_ros.hpp>
#include <nav2_util/node_thread.hpp>
#include <lifecycle_msgs/msg/state.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <cstdlib>

class MapShellTest : public ::testing::Test {
protected:
  static void SetUpTestCase() {
    const char *args[]={"map_shell_test","--ros-args","--params-file",std::getenv("TERRAIN_TEST_PROFILE")};
    rclcpp::init(4,args);
  }
  static void TearDownTestCase() {rclcpp::shutdown();}
};

TEST_F(MapShellTest, BothMapShellsActivateWithTfAndDisabledInputFreeLayer)
{
  for(const char *name:{"local_costmap","global_costmap"}) {
    auto map=std::make_shared<nav2_costmap_2d::Costmap2DROS>(name);
    nav2_util::NodeThread executor(map);
    EXPECT_EQ(map->get_parameter("plugins").as_string_array(),std::vector<std::string>{"map_shell"});
    map->configure();
    ASSERT_EQ(map->get_current_state().id(),lifecycle_msgs::msg::State::PRIMARY_STATE_INACTIVE);
    ASSERT_EQ(map->getLayeredCostmap()->getPlugins()->size(),1u);
    EXPECT_FALSE(map->get_parameter("map_shell.enabled").as_bool());
    EXPECT_TRUE(map->get_parameter("map_shell.observation_sources").as_string().empty());
    EXPECT_EQ(map->getCostmap()->getSizeInCellsX(),1u);
    EXPECT_EQ(map->getCostmap()->getSizeInCellsY(),1u);
    geometry_msgs::msg::TransformStamped tf;
    tf.header.frame_id="world";tf.child_frame_id="base";tf.header.stamp=map->now();
    tf.transform.rotation.w=1;
    ASSERT_TRUE(map->getTfBuffer()->setTransform(tf,"fixture",true));
    map->activate();
    EXPECT_EQ(map->get_current_state().id(),lifecycle_msgs::msg::State::PRIMARY_STATE_ACTIVE);
    EXPECT_TRUE(map->isCurrent());
    geometry_msgs::msg::PoseStamped pose;EXPECT_TRUE(map->getRobotPose(pose));
    EXPECT_EQ(pose.header.frame_id,"world");
    EXPECT_DOUBLE_EQ(map->get_parameter("publish_frequency").as_double(),0.0);
    map->deactivate();map->cleanup();
  }
}
