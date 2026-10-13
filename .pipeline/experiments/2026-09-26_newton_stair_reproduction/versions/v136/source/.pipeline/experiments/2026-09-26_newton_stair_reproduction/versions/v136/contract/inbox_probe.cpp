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
  fsm.odometryCallback(body);fsm.applyDueOdometry();
  auto producer=std::make_shared<rclcpp::Node>("mission_inbox_producer");
  auto pub=producer->create_publisher<scan_planner_msgs::msg::P2BRoute>("/p2b/route",rclcpp::QoS(1).reliable());
  auto cancels=producer->create_publisher<scan_planner_msgs::msg::P2BCancel>("/p2b/scan_cancel",10);
  const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(5);
  while(pub->get_subscription_count()<1||cancels->get_subscription_count()<1) {
    if(std::chrono::steady_clock::now()>deadline)throw std::runtime_error("No actual DDS match");
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
  // Model the observed executor choosing planner work while mission DDS is queued.
  // Only actual timer entry drains messages; no manual route callback in this case.
  fsm.exec_state_=scan_planner::SCANReplanFSM::WAIT_TARGET;
  fsm.trigger_=false;fsm.have_target_=false;
  pub->publish(*route);std::this_thread::sleep_for(std::chrono::milliseconds(100));
  fsm.execFSMCallback();
  const bool processed=fsm.p2b_route_generation_high_water_==1;
  std::cout<<"INBOX_CASE queued_route_processed="<<processed<<std::endl;
  // An ordinary route callback may also run during the old emergency exit.
  // The replacement must survive that exit, not be accepted and then erased.
  auto next=std::make_shared<scan_planner_msgs::msg::P2BRoute>(*route);
  next->generation=2;next->command_id="replacement";
  fsm.exec_state_=scan_planner::SCANReplanFSM::EMERGENCY_STOP;
  fsm.flag_escape_emergency_=false;fsm.need_hover_stop_=true;
  fsm.have_target_=false;fsm.trigger_=false;
  fsm.p2bRouteCallback(next);
  const bool accepted_before_tick=fsm.have_target_ && fsm.active_p2b_identity_.generation==2;
  std::cout<<"INBOX_CASE emergency_target_before_exit="<<accepted_before_tick<<std::endl;
  fsm.execFSMCallback();
  const bool survives=fsm.have_target_ && fsm.active_p2b_identity_.generation==2;
  std::cout<<"INBOX_CASE emergency_replacement_survives="<<survives<<std::endl;
  const bool expected=std::atoi(std::getenv("EXPECTED_FIXED"));
  if(processed!=expected||survives!=expected)throw std::runtime_error("Inbox regression mismatch");
  if(accepted_before_tick==expected)throw std::runtime_error("Emergency admission chronology mismatch");
  if(expected) {
    scan_planner_msgs::msg::P2BCancel stop;
    stop.run_id=next->run_id;stop.epoch=next->epoch;stop.request_id=next->request_id;
    stop.goal_id=next->goal_id;stop.route_id=next->route_id;stop.command_id=next->command_id;
    stop.generation=next->generation;stop.map_epoch=next->map_epoch;stop.map_revision=next->map_revision;
    stop.reason="queued_cancel_contract";
    cancels->publish(stop);pub->publish(*next);
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    fsm.execFSMCallback();fsm.execFSMCallback();
    const bool revoked=fsm.p2b_cancelled_generation_high_water_==2 && !fsm.have_target_;
    std::cout<<"INBOX_CASE cancellation_wins="<<revoked<<std::endl;
    if(!revoked)throw std::runtime_error("Canceled route revived");
  }
  rclcpp::shutdown();return 0;
}
