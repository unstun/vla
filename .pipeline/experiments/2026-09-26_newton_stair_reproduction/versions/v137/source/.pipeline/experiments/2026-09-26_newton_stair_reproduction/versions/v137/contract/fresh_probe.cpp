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
  size_t applied = 0; std::vector<RecordedScan> delayed;
  while (scans >> i >> stamp >> body_file >> sensor_file >> cloud_file) {
    RecordedScan scan{i, stamp, std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/body_file)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sensor_file)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cloud_file, false))};
    scan.body->header.stamp = scan.sensor->header.stamp = scan.cloud->header.stamp = rclcpp::Time(stamp, RCL_ROS_TIME);
    if(stamp<=67194702148LL) {apply_scan(*map,*node,scan);++applied;} else delayed.push_back(scan);
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
  fsm.odometryCallback(body);fsm.applyDueOdometry();
  const bool expected=std::atoi(std::getenv("EXPECTED_FIXED"));
  fsm.exec_state_=scan_planner::SCANReplanFSM::WAIT_TARGET;
  fsm.trigger_=false;fsm.have_target_=false;
  if(node->now().seconds()-map->observationStamp()<=.25||delayed.empty())
    throw std::runtime_error("Missing real stale/fresh fixture");
  fsm.p2bRouteCallback(route);
  const bool pending=bool(fsm.deferred_p2b_route_);
  if(fsm.have_target_||fsm.p2b_route_generation_high_water_!=0||pending!=expected)
    throw std::runtime_error("Stale admission must not authorize a target");
  std::cout<<"FRESH_CASE stale_pending="<<pending<<" moving_target=0"<<std::endl;
  // Keep the newer recorded torso pose; late LiDAR/sensor poses retain their
  // original stamps. No clock rollback or source-time renewal is used.
  for(const auto &scan:delayed) {
    if(scan.stamp>query_ns)throw std::runtime_error("Future scan in due fixture");
    map->sensorPoseCallback(scan.sensor);map->cloudCallback(scan.cloud);
  }
  map->refreshSensorInputs("fresh_contract");
  fsm.execFSMCallback();
  const bool resumed=fsm.have_target_ && fsm.p2b_route_generation_high_water_==1;
  std::cout<<"FRESH_CASE original_route_resumed="<<resumed<<" observation_age="<<node->now().seconds()-map->observationStamp()<<std::endl;
  if(resumed!=expected)throw std::runtime_error("Fresh original input did not release pending admission");
  if(expected) {
    auto invalid=std::make_shared<scan_planner_msgs::msg::P2BRoute>(*route);
    invalid->generation=2;invalid->command_id="unsupported_height";
    for(auto &pose:invalid->path.poses)pose.pose.position.z+=10;
    invalid->goal_pose.position.z+=10;
    fsm.p2bRouteCallback(invalid);
    if(fsm.deferred_p2b_route_||fsm.p2b_route_generation_high_water_!=1)
      throw std::runtime_error("Fresh genuine bad geometry must reject, not wait");
    std::cout<<"FRESH_CASE fresh_bad_geometry_rejected=1"<<std::endl;
    auto pending_route=std::make_shared<scan_planner_msgs::msg::P2BRoute>(*route);
    pending_route->generation=3;pending_route->command_id="cancel_pending";
    set_clock(*node,query_ns+400000000LL); // Age existing input; never renew it.
    fsm.p2bRouteCallback(pending_route);
    if(!fsm.deferred_p2b_route_)throw std::runtime_error("Expected pending stale route");
    scan_planner_msgs::msg::P2BCancel stop;
    stop.run_id=pending_route->run_id;stop.epoch=pending_route->epoch;stop.request_id=pending_route->request_id;
    stop.goal_id=pending_route->goal_id;stop.route_id=pending_route->route_id;stop.command_id=pending_route->command_id;
    stop.generation=3;stop.map_epoch=pending_route->map_epoch;stop.map_revision=pending_route->map_revision;
    fsm.p2bCancelCallback(std::make_shared<scan_planner_msgs::msg::P2BCancel>(stop));
    fsm.exec_state_=scan_planner::SCANReplanFSM::WAIT_TARGET;
    fsm.execFSMCallback();
    if(fsm.deferred_p2b_route_||fsm.p2b_cancelled_generation_high_water_!=3||fsm.p2b_route_generation_high_water_!=1)
      throw std::runtime_error("Canceled pending route revived");
    std::cout<<"FRESH_CASE pending_cancellation_wins=1"<<std::endl;
  }
  rclcpp::shutdown();return 0;
}
