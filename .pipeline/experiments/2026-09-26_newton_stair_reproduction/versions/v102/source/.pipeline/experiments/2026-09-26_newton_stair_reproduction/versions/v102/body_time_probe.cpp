#include "../v84/recording.h"
#include <plan_manage/scan_replan_fsm.h>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  rclcpp::Node node("scan_planner_node");
  const fs::path input=std::getenv("V102_INPUT");
  GridMap map;initialize_map(map,node,input);
  std::ifstream listing(input/"scans.txt");
  int index;int64_t stamp,later_stamp;std::string body,sensor,cloud,later_body;
  listing>>index>>stamp>>body>>sensor>>cloud>>later_stamp>>later_body;
  auto present=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/body));
  present->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
  RecordedScan scan{index,stamp,present,
    std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sensor)),
    std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cloud,false))};
  scan.sensor->header.stamp=scan.cloud->header.stamp=present->header.stamp;
  apply_scan(map,node,scan);map.startAsyncMapping();
  auto future=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/later_body));
  future->header.stamp=rclcpp::Time(later_stamp,RCL_ROS_TIME);
  const auto old_position=map.queryBodyPosition();
  map.slidingMapFrameCallback(future);
  map.refreshSensorInputs("future_body_probe");
  const bool map_deferred=map.reactive_body_stamp_s_<=node.now().seconds() &&
    (map.queryBodyPosition()-old_position).norm()==0.0;
  set_clock(node,later_stamp);map.refreshSensorInputs("eligible_body_probe");
  const auto &p=future->pose.pose.position;
  const bool map_exact=map.reactive_body_stamp_s_==rclcpp::Time(future->header.stamp).seconds() &&
    (map.queryBodyPosition()-Eigen::Vector3d(p.x,p.y,p.z)).norm()==0.0;
  set_clock(node,later_stamp+100000001LL);
  const bool stale_rejected=!std::isfinite(map.collisionSegmentYaw(Eigen::Vector3d::Zero(),Eigen::Vector3d::Zero()));
  auto regressed=std::make_shared<nav_msgs::msg::Odometry>(*present);
  map.slidingMapFrameCallback(regressed);
  const bool map_fault_closed=!map.mapperHealthy() &&
    map.getInflateOccupancy(Eigen::Vector3d(p.x,p.y,p.z),0.0)!=0;
  map.stopAsyncMapping();

  rclcpp::Node fsm_node("scan_planner_node");set_clock(fsm_node,stamp);
  scan_planner::SCANReplanFSM fsm;fsm.init(&fsm_node);
  fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();
  fsm.odometryCallback(present);const auto old_odom=fsm.odom_pos_;
  fsm.odometryCallback(future);
  const bool fsm_deferred=(fsm.odom_pos_-old_odom).norm()==0.0;
  set_clock(fsm_node,later_stamp);fsm.execFSMCallback();
  const bool fsm_exact=(fsm.odom_pos_-Eigen::Vector3d(p.x,p.y,p.z)).norm()==0.0;
  fsm.odometryCallback(regressed);
  const bool fsm_fault_closed=!fsm.have_odom_ && fsm.exec_state_==scan_planner::SCANReplanFSM::EMERGENCY_STOP;
  std::cout<<"{\"map_future_deferred\":"<<map_deferred<<",\"map_exact_source_pose\":"<<map_exact
    <<",\"body_stale_rejected\":"<<stale_rejected<<",\"fsm_future_deferred\":"<<fsm_deferred
    <<",\"fsm_exact_source_pose\":"<<fsm_exact<<",\"map_regression_fails_closed\":"<<map_fault_closed
    <<",\"fsm_regression_fails_closed\":"<<fsm_fault_closed<<"}"<<std::endl;
  rclcpp::shutdown();
  return map_deferred && map_exact && stale_rejected && fsm_deferred && fsm_exact && map_fault_closed && fsm_fault_closed?0:1;
}
