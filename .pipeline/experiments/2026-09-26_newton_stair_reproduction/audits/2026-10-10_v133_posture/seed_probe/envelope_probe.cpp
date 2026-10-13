#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/timed_cubic_initialization.h>
#include <bspline_opt/full_trajectory_collision.h>
#include <plan_manage/minimum_cruise.h>
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
  std::ifstream seed(input/"seed.txt"); double interval; int n; seed>>interval>>n;
  std::vector<Eigen::Vector3d> points(n),boundary(4);
  for(auto &p:points)seed>>p.x()>>p.y()>>p.z();
  for(auto &p:boundary)seed>>p.x()>>p.y()>>p.z();
  if(!seed)throw std::runtime_error("Missing seed");
  auto *manager=fsm.planner_manager_.get();
  for(int iteration=0;iteration<8;++iteration){
    Eigen::MatrixXd controls;
    if(!reactive_stair::fitCubicBoundaryPva(interval,points,boundary,controls))throw std::runtime_error("fit");
    scan_planner::UniformBspline curve(controls,3,interval);
    curve.setPhysicalLimits(manager->pp_.max_vel_,manager->pp_.max_acc_,manager->pp_.feasibility_tolerance_);
    double ratio;bool dynamics=curve.checkFeasibility(ratio,false)&&manager->checkDynamicFeasibility(curve);
    const auto collision=reactive_stair::checkFullCubicTrajectory(curve,0.0,map->getResolution(),GridMap::collision_heading_lookahead_s,
      [&](const Eigen::Vector3d&p,const Eigen::Vector3d&a,const Eigen::Vector3d&v){return map->collisionTrajectoryYaw(p,a,v);},
      [&](const Eigen::Vector3d&p,double yaw){return map->getInflateOccupancy(p,yaw)!=0;});
    const auto cruise=scan_planner::measureMinimumCruise(curve,manager->min_cruise_speed_,manager->pp_.max_acc_,manager->pp_.max_jerk_);
    std::cout<<"SEED_RESULT iteration="<<iteration<<" interval="<<interval<<" dynamics="<<dynamics<<" ratio="<<ratio<<" collision_clear="<<collision.clear()<<" collision_t="<<collision.first_time_s<<" cruise="<<cruise.passed<<" min_speed="<<cruise.minimum_speed<<std::endl;
    interval*=1.1;
  }
  rclcpp::shutdown();return 0;
}
