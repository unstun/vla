#include "../v84/recording.h"
#include <plan_manage/scan_replan_fsm.h>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  scan_planner::SCANReplanFSM fsm;fsm.init(node.get());
  fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();
  const fs::path input=std::getenv("V109_INPUT");
  auto map=std::make_shared<GridMap>();
  auto map_node=std::make_shared<rclcpp::Node>("scan_planner_node");
  initialize_map(*map,*map_node,input);
  fsm.planner_manager_->grid_map_=map;
  std::ifstream listing(input/"scans.txt");
  int index;int64_t stamp,later_stamp;std::string body,sensor,cloud,later_body;
  listing>>index>>stamp>>body>>sensor>>cloud>>later_stamp>>later_body;
  RecordedScan scan{index,stamp,
    std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/body)),
    std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sensor)),
    std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cloud,false))};
  scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
  apply_scan(*map,*map_node,scan);set_clock(*node,stamp);fsm.odometryCallback(scan.body);
  fsm.have_p2b_identity_=true;fsm.active_p2b_identity_.run_id="actual_map_replan_regression";
  auto &info=fsm.planner_manager_->local_data_;
  Eigen::MatrixXd controls(3,4);
  for(int i=0;i<4;++i) controls.col(i)=fsm.odom_pos_;
  info.position_traj_=scan_planner::UniformBspline(controls,3,1.0);
  info.start_time_=node->now();info.duration_=1.0;info.traj_id_=7;
  fsm.go2_execution_frozen_=false;
  auto reader=std::make_shared<rclcpp::Node>("safety_probe_reader");
  scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr last;
  auto sub=reader->create_subscription<scan_planner_msgs::msg::P2BExecutionSafety>(
    "/planning/execution_safety",10,[&](scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr message) {last=message;});
  rclcpp::executors::SingleThreadedExecutor exec;exec.add_node(reader);
  for(int i=0;i<200 && fsm.nav2_safety_pub_->get_subscription_count()==0;++i)
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  const auto check=[&](scan_planner::SCANReplanFSM::FSM_EXEC_STATE state) {
    fsm.exec_state_=state;last.reset();fsm.checkCollisionCallback();
    for(int i=0;i<200 && !last;++i) {exec.spin_some();std::this_thread::sleep_for(std::chrono::milliseconds(1));}
    if(!last || last->binding.traj_id!=7)throw std::runtime_error("Missing exact-trajectory safety");
    return last->clear;
  };
  const bool executing=check(scan_planner::SCANReplanFSM::EXEC_TRAJ);
  const bool replanning=check(scan_planner::SCANReplanFSM::REPLAN_TRAJ);
  const bool stopped=!check(scan_planner::SCANReplanFSM::EMERGENCY_STOP);
  const bool waiting=!check(scan_planner::SCANReplanFSM::WAIT_TARGET);
  set_clock(*node,stamp+100000001);set_clock(*map_node,stamp+100000001);
  const bool stale=!check(scan_planner::SCANReplanFSM::REPLAN_TRAJ);
  std::cout<<"{\"executing_clear\":"<<executing<<",\"replanning_clear\":"<<replanning
    <<",\"emergency_blocked\":"<<stopped<<",\"waiting_blocked\":"<<waiting<<",\"stale_blocked\":"<<stale<<"}"<<std::endl;
  rclcpp::shutdown();return executing && replanning && stopped && waiting && stale?0:1;
}
