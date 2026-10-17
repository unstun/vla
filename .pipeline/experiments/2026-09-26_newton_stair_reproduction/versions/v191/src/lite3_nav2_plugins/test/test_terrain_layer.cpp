#include <gtest/gtest.h>
#include <chrono>
#include <thread>
#include <nav2_costmap_2d/layer.hpp>
#include <nav2_costmap_2d/layered_costmap.hpp>
#include <nav2_util/lifecycle_node.hpp>
#include <nav_msgs/msg/occupancy_grid.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>
#include <pluginlib/class_loader.hpp>

TEST(TerrainLayer, NativeSliceOccupancyExpiryAndFloorMismatch)
{
  int argc=0; rclcpp::init(argc,nullptr);
  auto node=std::make_shared<nav2_util::LifecycleNode>("terrain_layer_test");
  auto io=std::make_shared<rclcpp::Node>("terrain_fixture");
  tf2_ros::Buffer tf(node->get_clock());
  geometry_msgs::msg::TransformStamped transform;
  transform.header.frame_id="world"; transform.header.stamp=node->now();
  transform.child_frame_id="base_link";
  transform.transform.translation.z=0.42; transform.transform.rotation.w=1;
  ASSERT_TRUE(tf.setTransform(transform,"fixture",true));
  nav2_costmap_2d::LayeredCostmap layers("world",false,true);
  layers.resizeMap(60,60,0.1,-3,-3);
  pluginlib::ClassLoader<nav2_costmap_2d::Layer> loader("nav2_costmap_2d","nav2_costmap_2d::Layer");
  auto layer=loader.createSharedInstance("lite3_nav2/TerrainLayer");
  layer->initialize(&layers,"terrain",&tf,node,io,io);
  auto pub=io->create_publisher<nav_msgs::msg::OccupancyGrid>("/nav2_scan/terrain_slice",1);
  rclcpp::executors::SingleThreadedExecutor executor;
  executor.add_node(node->get_node_base_interface()); executor.add_node(io);
  const auto spin=[&](int ms) {
    auto end=std::chrono::steady_clock::now()+std::chrono::milliseconds(ms);
    while(std::chrono::steady_clock::now()<end) {
      executor.spin_some(); std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
  };
  const auto update=[&] {
    double minx=1e9,miny=1e9,maxx=-1e9,maxy=-1e9;
    layer->updateBounds(0,0,0,&minx,&miny,&maxx,&maxy);
    layer->updateCosts(*layers.getCostmap(),0,0,60,60);
  };
  spin(100); update(); EXPECT_FALSE(layer->isCurrent());
  nav_msgs::msg::OccupancyGrid grid;
  grid.header.frame_id="world"; grid.header.stamp=node->now();
  grid.info.width=grid.info.height=60; grid.info.resolution=0.1;
  grid.info.origin.position.x=grid.info.origin.position.y=-3;
  grid.info.origin.position.z=0.42; grid.info.origin.orientation.w=1;
  grid.data.resize(3600,0); grid.data[30*60+40]=100;
  pub->publish(grid); spin(30); update();
  EXPECT_TRUE(layer->isCurrent());
  EXPECT_EQ(layers.getCostmap()->getCost(40,30),nav2_costmap_2d::LETHAL_OBSTACLE);
  EXPECT_EQ(layers.getCostmap()->getCost(20,20),nav2_costmap_2d::FREE_SPACE);
  spin(270); update(); EXPECT_FALSE(layer->isCurrent());
  // Republishing the same old stamp cannot make the layer current.
  pub->publish(grid); spin(20); update(); EXPECT_FALSE(layer->isCurrent());
  // Fresh evidence from another floor is still inapplicable.
  grid.header.stamp=node->now(); grid.info.origin.position.z=2.42;
  pub->publish(grid); spin(20); update(); EXPECT_FALSE(layer->isCurrent());
  layer.reset(); executor.remove_node(io); executor.remove_node(node->get_node_base_interface());
  io.reset(); node.reset(); rclcpp::shutdown();
}
