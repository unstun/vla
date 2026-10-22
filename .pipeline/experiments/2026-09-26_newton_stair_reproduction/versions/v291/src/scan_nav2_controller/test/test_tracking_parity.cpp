#include <gtest/gtest.h>
#include <rcl/time.h>
#include <scan_nav2_controller/tracking_node.hpp>
#include "legacy_tracking_reference.hpp"

static void clockAt(rclcpp::Node &node,int64_t ns)
{
  auto clock=node.get_clock()->get_clock_handle();
  ASSERT_EQ(rcl_enable_ros_time_override(clock),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock,ns),RCL_RET_OK);
}

TEST(TrackingParity, PreservesStraightTrackingGeometryAndSettledCommandAcross300Samples)
{
  int argc=0; rclcpp::init(argc,nullptr);
  {
    rclcpp::NodeOptions options; options.use_global_arguments(false);
    scan_planner::ClosedLoopController original(options);
    scan_planner::TrackingNode extracted(options);
    const int64_t start=10000000000LL;
    clockAt(original,start); clockAt(extracted,start);
    auto spline=std::make_shared<scan_planner_msgs::msg::Bspline>();
    spline->order=3; spline->traj_id=1; spline->start_time=rclcpp::Time(start,RCL_ROS_TIME);
    for(int i=0;i<12;++i) { geometry_msgs::msg::Point p; p.x=0.4*i; p.y=0.0; p.z=0.42; spline->pos_pts.push_back(p); }
    for(int i=-3;i<13;++i) spline->knots.push_back(i);
    original.bsplineCallback(spline); extracted.bsplineCallback(spline);
    for(int i=0;i<300;++i) {
      const int64_t time=start+33333333LL*i;
      clockAt(original,time); clockAt(extracted,time);
      auto odom=std::make_shared<nav_msgs::msg::Odometry>();
      odom->header.frame_id="world"; odom->header.stamp=rclcpp::Time(time,RCL_ROS_TIME);
      odom->pose.pose.position.x=0.0; odom->pose.pose.position.y=0.0;
      odom->pose.pose.position.z=0.42;
      const double yaw=0.0;
      odom->pose.pose.orientation.w=std::cos(yaw/2); odom->pose.pose.orientation.z=std::sin(yaw/2);
      original.odomCallback(odom); original.cmdCallback();
      geometry_msgs::msg::PoseStamped pose; pose.header=odom->header; pose.pose=odom->pose.pose;
      const auto command=extracted.sample(pose);
      if (i>60) EXPECT_EQ(command,original.recorded_command_) << "settled sample " << i;
      EXPECT_DOUBLE_EQ(extracted.exec_time_,original.exec_time_) << "sample " << i;
    }
    EXPECT_EQ(extracted.raw_cmd_pub_,nullptr);
    EXPECT_EQ(extracted.cmd_timer_,nullptr);
  }
  rclcpp::shutdown();
}
