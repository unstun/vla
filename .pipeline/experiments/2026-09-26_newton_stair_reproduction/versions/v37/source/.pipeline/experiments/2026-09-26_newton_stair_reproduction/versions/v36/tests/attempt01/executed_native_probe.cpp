// Actual compiled FSM and controller; controlled ROS fixtures, no robot physics.
#define main controller_entry_unused
#include "/workspace/src/plan_manage/src/closed_loop_controller.cpp"
#undef main
#include <plan_manage/scan_replan_fsm.h>
#include <rcl/time.h>
#include <chrono>
#include <iostream>
#include <thread>

void check(bool value, const std::string &name)
{
  if (!value) throw std::runtime_error(name);
  std::cout << "V36_CHECK " << name << " PASS\n";
}

template<class T> void identity(T &msg)
{
  msg.run_id="run"; msg.epoch=1; msg.request_id="request"; msg.goal_id="goal";
  msg.route_id="route"; msg.command_id="command"; msg.generation=2;
  msg.map_epoch="map"; msg.map_revision=1;
}

int main(int argc, char **argv)
{
  rclcpp::init(argc, argv);
  try
  {
    auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
    scan_planner::SCANReplanFSM fsm;
    fsm.init(node.get());
    fsm.exec_timer_->cancel(); fsm.safety_timer_->cancel();
    auto clock = [&](double seconds) {
      auto *handle=node->get_clock()->get_clock_handle();
      if(rcl_enable_ros_time_override(handle)!=RCL_RET_OK ||
         rcl_set_ros_time_override(handle, std::llround(seconds*1e9))!=RCL_RET_OK)
        throw std::runtime_error("clock override");
    };
    check(fsm.replan_frequency_==30.0, "configured_local_30hz");
    clock(100.0); check(fsm.nominalReplanDue(true), "initial_attempt");
    int attempts=0;
    for(int i=1;i<=100;i++) { clock(100.+.01*i); if(fsm.nominalReplanDue(true)) attempts++; }
    check(attempts==30, "thirty_attempt_slots_per_ros_second_at_100hz_poll");
    check(!fsm.nominalReplanDue(true), "paused_clock_no_burst");
    clock(103.25); check(fsm.nominalReplanDue(true), "missed_slots_one_attempt");
    check(!fsm.nominalReplanDue(true), "missed_slots_no_catchup");
    clock(103.26); check(!fsm.nominalReplanDue(false), "observe_between_attempts");
    clock(103.255); check(!fsm.nominalReplanDue(true), "rollback_after_last_attempt_detected");
    clock(103.255+1./30); check(fsm.nominalReplanDue(true), "rollback_reanchors_one_period");
    Eigen::MatrixXd points(3,7);
    for(int i=0;i<7;i++) points.col(i)<<0.1*i,0.0,0.35;
    scan_planner::UniformBspline curve(points,3,0.5);
    auto &local=fsm.planner_manager_->local_data_;
    local.position_traj_=curve; local.velocity_traj_=curve.getDerivative();
    local.acceleration_traj_=local.velocity_traj_.getDerivative();
    local.duration_=curve.getTimeSum(); local.start_time_=node->now();
    local.start_pos_=curve.evaluateDeBoorT(0); local.traj_id_=7;
    fsm.exec_state_=scan_planner::SCANReplanFSM::EXEC_TRAJ;
    fsm.end_pt_=Eigen::Vector3d(10,0,.35); fsm.have_target_=true;
    fsm.odom_pos_=local.start_pos_; fsm.odom_pos_.x()=std::numeric_limits<double>::quiet_NaN();
    fsm.odom_vel_.setZero(); fsm.go2_execution_frozen_=false;
    fsm.last_freeze_update_time_=node->now();
    fsm.planner_manager_->global_data_.global_duration_=10.;
    fsm.planner_manager_->global_data_.last_progress_time_=1.;
    clock(103.4); fsm.execFSMCallback();
    check(fsm.replan_fail_count_==1, "periodic_trigger_attempt_same_callback_actual_rejection");
    fsm.go2_execution_frozen_=true;
    clock(103.5); fsm.execFSMCallback();
    check(fsm.replan_fail_count_==1, "queued_retry_suppressed_during_yaw_freeze");

    auto controller=std::make_shared<scan_planner::ClosedLoopController>();
    controller->cmd_timer_->cancel();
    auto observer=std::make_shared<rclcpp::Node>("v36_controller_observer");
    std::vector<double> stamps;
    scan_planner_msgs::msg::P2BStampedTwist last;
    auto sub=observer->create_subscription<scan_planner_msgs::msg::P2BStampedTwist>(
      "/quad_0/raw_scan_cmd_vel",1000,[&](scan_planner_msgs::msg::P2BStampedTwist::ConstSharedPtr msg) {
        last=*msg; stamps.push_back(std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count());
      });
    rclcpp::executors::SingleThreadedExecutor executor;
    executor.add_node(controller); executor.add_node(observer);
    auto spin=[&](double seconds) {
      const auto end=std::chrono::steady_clock::now()+std::chrono::duration<double>(seconds);
      while(std::chrono::steady_clock::now()<end) { executor.spin_some(); std::this_thread::sleep_for(std::chrono::milliseconds(1)); }
    };
    spin(.25);
    auto route=std::make_shared<scan_planner_msgs::msg::P2BRoute>(); identity(*route);
    route->has_goal_pose=true; route->path.poses.resize(2);
    route->goal_pose.position.x=10.; route->goal_pose.position.z=.35;
    route->goal_pose.orientation.z=std::sin(M_PI/4); route->goal_pose.orientation.w=std::cos(M_PI/4);
    controller->goalCallback(route);
    auto spline=std::make_shared<scan_planner_msgs::msg::Bspline>(); identity(*spline);
    spline->order=3; spline->traj_id=1;
    for(int i=0;i<7;i++) { geometry_msgs::msg::Point p; p.x=points(0,i); p.y=points(1,i); p.z=points(2,i); spline->pos_pts.push_back(p); }
    const auto knots=curve.getKnot();
    for(int i=0;i<knots.size();i++) spline->knots.push_back(knots(i));
    controller->bsplineCallback(spline);
    auto odom=std::make_shared<nav_msgs::msg::Odometry>();
    odom->pose.pose.position.x=10.; odom->pose.pose.position.z=.35; odom->pose.pose.orientation.w=1.;
    controller->odomCallback(odom);
    auto tick=[&]() { const auto before=stamps.size(); controller->cmdCallback(); spin(.05); check(stamps.size()>before,"actual_publication_received"); };
    tick();
    check(last.twist.linear.x==0 && last.twist.linear.y==0 && last.twist.angular.z>0,"goal_position_then_final_yaw");
    check(controller->goal_xy_reached_,"stateful_xy_latched");
    odom->pose.pose.orientation=route->goal_pose.orientation; controller->odomCallback(odom); tick();
    check(last.twist.angular.z==0 && last.twist.linear.x==0,"yaw_tolerance_publishes_stop");
    auto refreshed=std::make_shared<scan_planner_msgs::msg::P2BRoute>(*route);
    refreshed->goal_pose.orientation.z=0; refreshed->goal_pose.orientation.w=1;
    controller->goalCallback(refreshed);
    check(std::abs(controller->goal_yaw_-M_PI/2)<1e-9,"refresh_keeps_initial_goal_orientation");
    controller->goal_xy_reached_=false; odom->pose.pose.position.z=.70; controller->odomCallback(odom); tick();
    check(!controller->goal_xy_reached_,"wrong_floor_cannot_latch_arrival");
    odom->pose.pose.position.z=.35; odom->pose.pose.orientation.z=0; odom->pose.pose.orientation.w=1;
    controller->odomCallback(odom);
    stamps.clear(); controller->cmd_timer_->reset(); spin(3.2); controller->cmd_timer_->cancel();
    const double rate=(stamps.size()-1)/(stamps.back()-stamps.front());
    double max_gap=0;
    for(size_t i=1;i<stamps.size();i++) max_gap=std::max(max_gap,stamps[i]-stamps[i-1]);
    std::cout<<"V36_CONTROLLER_MEASURE samples="<<stamps.size()<<" hz="<<rate<<" max_wall_gap_s="<<max_gap<<"\n";
    check(rate>=29.0 && rate<=31.0 && max_gap<=.1,"actual_native_controller_30hz_component");
    auto cancel=std::make_shared<scan_planner_msgs::msg::P2BCancel>(); identity(*cancel); cancel->reason="test cancel";
    controller->p2bCancelCallback(cancel); spin(.05); tick();
    check(last.twist.angular.z==0 && last.twist.linear.x==0 && !controller->receive_traj_,"cancel_stops_final_rotation");
    controller->goalCallback(route); controller->bsplineCallback(spline);
    check(!controller->receive_traj_,"cancelled_generation_cannot_restart");
    std::cout<<"V36_NATIVE_PASSED\n";
    rclcpp::shutdown(); return 0;
  }
  catch(const std::exception &error) { std::cerr<<error.what()<<"\n"; rclcpp::shutdown(); return 1; }
}
