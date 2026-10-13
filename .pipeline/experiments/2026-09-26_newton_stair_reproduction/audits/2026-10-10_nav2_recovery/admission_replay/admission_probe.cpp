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
  auto route = std::make_shared<scan_planner_msgs::msg::P2BRoute>();
  route->run_id="captured-admission-probe"; route->epoch=1; route->request_id="r"; route->goal_id="g";
  route->route_id="route"; route->command_id="command"; route->generation=1; route->map_epoch="map";
  route->map_revision=1; route->has_goal_pose=true; route->path.header.frame_id="world";
  route->path.header.stamp=rclcpp::Time(query_ns,RCL_ROS_TIME);
  int points; std::ifstream path(input/"route.txt"); path>>points;
  for (int p=0;p<points;++p) {
    geometry_msgs::msg::PoseStamped pose; pose.header=route->path.header; pose.pose.orientation.w=1;
    path>>pose.pose.position.x>>pose.pose.position.y>>pose.pose.position.z;
    route->path.poses.push_back(pose);
  }
  if(!path || points<2) throw std::runtime_error("Invalid captured route");
  route->goal_pose=read_pose(input/"goal.txt").pose.pose;
  set_clock(*node,query_ns); map->slidingMapFrameCallback(body);
  const auto digest = map_digest(*map);
  // No new sensor is fabricated. Static clocks ask whether the recorded geometry
  // can be admitted; advancing clocks test expiry while the same inputs age.
  for (int mode=0;mode<6;++mode) {
    const bool cache=mode%2==1, advancing=mode>=2 && mode<4;
    const int64_t now=query_ns+(mode>=4?300000000LL:0);
    set_clock(*node,now); map->slidingMapFrameCallback(body); fsm.odometryCallback(body); fsm.applyDueOdometry();
    fsm.start_pt_=fsm.odom_pos_; fsm.end_pt_.setZero(); fsm.end_vel_.setZero(); fsm.reference_neighbor_point_.setZero();
    fsm.exec_state_=scan_planner::SCANReplanFSM::WAIT_TARGET;
    fsm.have_target_=false; fsm.have_p2b_identity_=false; fsm.have_requested_goal_pose_=false;
    fsm.trigger_=false; fsm.p2b_route_generation_high_water_=0; fsm.p2b_cancelled_generation_high_water_=0;
    std::unique_ptr<GridMap::RawContributorCacheScope> scope;
    if(cache) scope=std::make_unique<GridMap::RawContributorCacheScope>(*map);
    std::atomic<bool> running{true};
    const auto begin=std::chrono::steady_clock::now();
    std::thread clock;
    if(advancing) clock=std::thread([&]{
      while(running) {
        const auto elapsed=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-begin).count();
        if(rcl_set_ros_time_override(node->get_clock()->get_clock_handle(),now+elapsed)!=RCL_RET_OK) std::terminate();
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
      }
    });
    fsm.p2bRouteCallback(route);
    running=false; if(clock.joinable())clock.join();
    const double wall=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
    const double stamp_now=node->now().seconds();
    std::cout<<std::setprecision(17)<<"ADMISSION_CASE mode="<<mode<<" cache="<<cache<<" advancing="<<advancing
      <<" accepted="<<fsm.have_target_<<" wall_ms="<<wall*1000<<" frontier="<<fsm.reference_frontier_time_
      <<" cloud_age="<<stamp_now-map->observationStamp()<<" body_age="<<stamp_now-body_ns*1e-9
      <<" raw_evaluations="<<map->raw_contributor_cache_evaluations_<<" raw_hits="<<map->raw_contributor_cache_hits_<<std::endl;
    scope.reset();
    if(map_digest(*map)!=digest)throw std::runtime_error("Admission changed reconstructed map");
  }
  std::cout<<"ADMISSION_COMPLETE scans="<<applied<<" map_digest="<<digest<<std::endl;
  rclcpp::shutdown();
}
