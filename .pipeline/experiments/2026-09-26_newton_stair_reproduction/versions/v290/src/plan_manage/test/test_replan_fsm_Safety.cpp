#include <gtest/gtest.h>
#include <plan_manage/scan_replan_fsm.h>
#include <rcl/time.h>
#include <condition_variable>
#include <thread>

TEST(ReplanFsmSafety, LateCallbackCannotUndoNewerManualDrain) {
  rclcpp::init(0,nullptr);
  {
    auto node=std::make_shared<rclcpp::Node>("fsm_body_order_test");
    scan_planner::SCANReplanFSM fsm;
    fsm.node_=node.get();
    fsm.planner_manager_=std::make_unique<scan_planner::SCANPlannerManager>();
    fsm.planner_manager_->grid_map_=std::make_shared<GridMap>();
    fsm.navi_mode_=3;fsm.have_odom_=false;fsm.exec_state_=scan_planner::SCANReplanFSM::EXEC_TRAJ;
    fsm.self_inflation_z_up_=0.55;fsm.self_inflation_z_down_=0.35;
    fsm.self_double_cylinder_radius_=0.35;fsm.self_double_cylinder_offset_=0.18;
    fsm.self_inflation_pub_=node->create_publisher<visualization_msgs::msg::Marker>("body",10);
    auto clock=node->get_clock();
    ASSERT_EQ(rcl_enable_ros_time_override(clock->get_clock_handle()),RCL_RET_OK);
    ASSERT_EQ(rcl_set_ros_time_override(clock->get_clock_handle(),3000000000LL),RCL_RET_OK);
    auto pose=[](int sec){auto m=std::make_shared<nav_msgs::msg::Odometry>();
      m->header.stamp.sec=sec;m->pose.pose.position.x=sec;m->pose.pose.orientation.w=1.;return m;};
    std::mutex phase_mutex;std::condition_variable phase;bool taken=false;
    std::unique_lock<std::recursive_mutex> work(fsm.planner_manager_->grid_map_->lockMutex());
    std::thread callback([&]{auto t1=pose(1);
      {std::lock_guard<std::mutex> l(phase_mutex);taken=true;}phase.notify_one();
      fsm.callbackBoundary("late_callback",[&]{fsm.odometryCallback(t1);});
    });
    {std::unique_lock<std::mutex> l(phase_mutex);phase.wait(l,[&]{return taken;});}
    fsm.callbackBoundary("manual_drain",[&]{fsm.odometryCallback(pose(2));});
    work.unlock();callback.join();
    EXPECT_TRUE(fsm.have_odom_);EXPECT_DOUBLE_EQ(fsm.odom_pos_.x(),2.);
    EXPECT_TRUE(fsm.body_inputs_.healthy());EXPECT_EQ(fsm.body_inputs_.ignoredOlderSamples(),1u);
    fsm.callbackBoundary("next_callback",[&]{fsm.odometryCallback(pose(3));});
    EXPECT_TRUE(fsm.have_odom_);EXPECT_DOUBLE_EQ(fsm.odom_pos_.x(),3.);
    EXPECT_EQ(fsm.exec_state_,scan_planner::SCANReplanFSM::EXEC_TRAJ);
    EXPECT_TRUE(fsm.body_inputs_.healthy());
  }
  rclcpp::shutdown();
}
