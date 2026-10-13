#include <plan_manage/scan_replan_fsm.h>
#include "v84/recording.h"
#include <atomic>
#include <memory>

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
  set_clock(*node,query_ns); map->slidingMapFrameCallback(body);
  const auto &p=body->pose.pose.position;const auto &q=body->pose.pose.orientation;
  const Eigen::Vector3d position(p.x,p.y,p.z);
  const double yaw=std::atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z));
  const int blocked=map->getInflateOccupancy(position,yaw);
  const bool expected=std::atoi(std::getenv("EXPECTED_BLOCKED"));
  std::cout<<"ENVELOPE_CASE trapped_pose_blocked="<<blocked<<" body="<<position.transpose()<<" yaw="<<yaw<<std::endl;
  if(blocked!=expected)throw std::runtime_error("Captured turn-clearance case mismatch");
  std::ofstream rows(std::getenv("QUERY_OUTPUT"));
  size_t clear=0,total=0;
  for(int ix=0;ix<=24;++ix)for(int iy=0;iy<=16;++iy)for(int h=0;h<16;++h) {
    const Eigen::Vector3d p(6.7+ix*.075,5.8+iy*.075,position.z());
    const double heading=-M_PI+h*(2*M_PI/16);
    const int verdict=map->getInflateOccupancy(p,heading);
    rows<<ix<<','<<iy<<','<<h<<','<<verdict<<'\n';++total;if(!verdict)++clear;
  }
  if(!clear)throw std::runtime_error("No clear query remains in fixture");
  std::cout<<"ENVELOPE_CASE clear="<<clear<<" total="<<total<<std::endl;
  std::cout<<"ENVELOPE_MAP_DIGEST "<<map_digest(*map)<<std::endl;
  rclcpp::shutdown();return 0;
}
