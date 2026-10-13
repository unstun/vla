#include <plan_manage/scan_replan_fsm.h>
#include "v84/recording.h"
#include <atomic>
#include <memory>

static rclcpp::Node *search_clock = nullptr;
static int64_t search_after_ns = 0;
static int search_calls = 0;

// Controlled long-search failure at the real FSM/helper seam. Geometry,
// body queue, ROS clock, freshness checks and subsequent native queries are real.
ASTAR_RET AStar::AstarSearch(const double, Eigen::Vector3d, Eigen::Vector3d, bool, double) {
  if(!search_clock) throw std::runtime_error("Search hook not armed");
  ++search_calls;
  if(rcl_set_ros_time_override(search_clock->get_clock()->get_clock_handle(), search_after_ns)!=RCL_RET_OK)
    throw std::runtime_error("Search clock advance failed");
  return ASTAR_RET::SEARCH_ERR;
}


int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  const fs::path input = std::getenv("REPLAY_INPUT");
  auto node = std::make_shared<rclcpp::Node>("scan_planner_node");
  node->declare_parameter<bool>("grid_map.asynchronous_mapping", false);
  node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping", false));
  set_clock(*node, 1000000000LL);
  scan_planner::SCANReplanFSM fsm; fsm.init(node.get());
  fsm.exec_timer_->cancel(); fsm.safety_timer_->cancel();
  auto map = fsm.planner_manager_->grid_map_;
  map->occ_timer_->cancel(); map->vis_timer_->cancel();
  if (map->async_mapping_) throw std::runtime_error("Requires ordered synchronous reconstruction");
  auto nav = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "navigation.f32", true));
  auto surface = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "surface.f32", true));
  auto floor = std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input / "physical_floor.f32", true));
  nav->header.stamp = surface->header.stamp = floor->header.stamp = node->now();
  map->reactiveTomogramCallback(nav); map->reactiveSurfaceGroundCallback(surface); map->reactivePhysicalFloorCallback(floor);
  if (!map->reactiveSurfaceGroundReady()) throw std::runtime_error("Original support not ready");
  std::ifstream scans(input / "scans.txt"); int i; int64_t stamp; std::string body_file, sensor_file, cloud_file;
  size_t applied = 0;
  while (scans >> i >> stamp >> body_file >> sensor_file >> cloud_file) {
    RecordedScan scan{i, stamp, std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/body_file)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sensor_file)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cloud_file, false))};
    scan.body->header.stamp = scan.sensor->header.stamp = scan.cloud->header.stamp = rclcpp::Time(stamp, RCL_ROS_TIME);
    apply_scan(*map, *node, scan); ++applied;
  }
  if (!scans.eof() || applied == 0) throw std::runtime_error("Invalid captured scan prefix");
  int64_t query_ns, body_ns; std::ifstream query(input/"query.txt"); query >> query_ns >> body_ns;
  if (!query) throw std::runtime_error("Invalid query clocks");
  auto body = std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/"query_body.txt"));
  body->header.stamp = rclcpp::Time(body_ns, RCL_ROS_TIME);
  set_clock(*node,query_ns); map->slidingMapFrameCallback(body); fsm.odometryCallback(body); fsm.applyDueOdometry();
  fsm.start_pt_=fsm.odom_pos_; fsm.end_pt_.setZero(); fsm.end_vel_.setZero(); fsm.reference_neighbor_point_.setZero();
  fsm.exec_state_=scan_planner::SCANReplanFSM::WAIT_TARGET;
  map->startAsyncMapping();
  const int mode=std::stoi(std::getenv("REFRESH_CASE"));
  auto future=std::make_shared<nav_msgs::msg::Odometry>(*body);
  search_after_ns=query_ns+120000000LL;
  future->header.stamp=rclcpp::Time(search_after_ns+(mode==2?1:0),RCL_ROS_TIME);
  if(mode!=1) map->slidingMapFrameCallback(future);
  if(map->reactive_body_stamp_s_>query_ns*1e-9+1e-9)throw std::runtime_error("Future body applied prematurely");
  const Eigen::Vector3d begin=fsm.odom_pos_;
  search_clock=node.get(); search_calls=0;
  const bool accepted=fsm.planGlobalTrajByWaypoints({begin,begin+Eigen::Vector3d(0,0,0.6)});
  if(search_calls!=1)throw std::runtime_error("Actual helper did not reach the controlled search boundary");
  const bool due_body=std::abs(map->reactive_body_stamp_s_-search_after_ns*1e-9)<1e-10;
  std::cout<<std::setprecision(17)<<"REFRESH_CASE mode="<<mode<<" accepted="<<accepted
    <<" due_body_applied="<<due_body<<" body_age="<<node->now().seconds()-map->reactive_body_stamp_s_
    <<" observation_age="<<node->now().seconds()-map->observationStamp()
    <<" search_calls="<<search_calls<<" frontier="<<fsm.reference_frontier_time_<<std::endl;
  map->stopAsyncMapping(); rclcpp::shutdown();
}
