#include "../v84/recording.h"
#include <plan_manage/scan_replan_fsm.h>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  set_clock(*node,1000000000LL);scan_planner::SCANReplanFSM fsm;fsm.init(node.get());
  fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();
  auto &manager=*fsm.planner_manager_;auto map=manager.grid_map_;
  map->occ_timer_->cancel();map->vis_timer_->cancel();
  if(map->async_mapping_)throw std::runtime_error("Probe expects ordered recorded-map initialization");
  const fs::path input=std::getenv("V113_INPUT");
  auto nav=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"navigation.f32",true));
  auto surface=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"surface.f32",true));
  auto floor=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"physical_floor.f32",true));
  nav->header.stamp=surface->header.stamp=floor->header.stamp=node->now();
  map->reactiveTomogramCallback(nav);map->reactiveSurfaceGroundCallback(surface);map->reactivePhysicalFloorCallback(floor);
  std::ifstream listing(input/"scans.txt");int index;int64_t stamp,later;std::string body,sensor,cloud,later_body;
  nav_msgs::msg::Odometry::SharedPtr last;
  while(listing>>index>>stamp>>body>>sensor>>cloud>>later>>later_body) {
    RecordedScan scan{index,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/body)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sensor)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cloud,false))};
    scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    apply_scan(*map,*node,scan);last=scan.body;
  }
  fsm.odometryCallback(last);fsm.have_p2b_identity_=true;fsm.active_p2b_identity_.run_id="publication-proof";
  fsm.active_p2b_identity_.command_id="verified-command";fsm.active_p2b_identity_.generation=1;
  const auto start=fsm.odom_pos_;const Eigen::Vector3d end(start.x()+.25,start.y()-.6,3.34),zero=Eigen::Vector3d::Zero();
  const auto checked_clock=node->now();const double observation=map->observationStamp();
  const bool success=manager.reboundReplan(start,zero,zero,end,zero,true,false);
  if(!success)throw std::runtime_error("Actual native fixture did not produce a validated trajectory");
  const auto certificate=manager.publication_check_;
  if(!certificate.clear || certificate.traj_id!=manager.local_data_.traj_id_ ||
     certificate.checked_at!=checked_clock || certificate.observation_stamp_s!=observation)
    throw std::runtime_error("Actual final validation evidence was not bound to the exact trajectory");
  auto reader=std::make_shared<rclcpp::Node>("publication_proof_reader");
  scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr received;
  auto sub=reader->create_subscription<scan_planner_msgs::msg::P2BExecutionSafety>("/planning/execution_safety",10,
    [&](scan_planner_msgs::msg::P2BExecutionSafety::ConstSharedPtr p){received=p;});
  for(int i=0;i<100 && fsm.nav2_safety_pub_->get_subscription_count()==0;++i)std::this_thread::sleep_for(std::chrono::milliseconds(5));
  set_clock(*node,checked_clock.nanoseconds()+20000000LL);
  fsm.publishExecutionSafety(certificate.traj_id,certificate.checked_at,certificate.observation_stamp_s,certificate.map_revision,true);
  for(int i=0;i<100 && !received;++i){rclcpp::spin_some(reader);std::this_thread::sleep_for(std::chrono::milliseconds(2));}
  if(!received || !received->clear || received->binding.traj_id!=certificate.traj_id ||
     received->binding.command_id!="verified-command" || rclcpp::Time(received->stamp)!=certificate.checked_at ||
     received->observation_stamp_s!=observation)throw std::runtime_error("Published proof changed the source times/identity");
  manager.publication_lease_.reset();set_clock(*node,checked_clock.nanoseconds()+300000000LL);
  const bool stale_success=manager.reboundReplan(start,zero,zero,end,zero,true,false);
  if(stale_success || manager.publication_check_.clear)throw std::runtime_error("Rejected solve retained a publishable proof");
  std::cout<<"V113_PUBLICATION_PROOF_PASS actual_final_check exact_trajectory original_check_and_map_times stale_solve_invalidates"<<std::endl;
  rclcpp::shutdown();
}
