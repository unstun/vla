// Adapt the v81/v82 native publication negative to v240's non-adopting drain.
#include "v84/recording.h"
#include <bspline_opt/full_trajectory_collision.h>

int main(int argc, char **argv) {
  rclcpp::init(argc, argv);
  const fs::path input=std::getenv("REPLAY_INPUT"), output=std::getenv("CONTRACT_OUTPUT");
  fs::create_directories(output);
  rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("grid_map.asynchronous_mapping",false)});
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);
  set_clock(*node,1000000000LL);
  GridMap map;map.initMap(node.get());map.occ_timer_->cancel();map.vis_timer_->cancel();
  auto nav=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"navigation.f32",true));
  auto surface=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"surface.f32",true));
  auto floor=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"physical_floor.f32",true));
  nav->header.stamp=surface->header.stamp=floor->header.stamp=rclcpp::Time(1000000000LL,RCL_ROS_TIME);
  map.reactiveTomogramCallback(nav);map.reactiveSurfaceGroundCallback(surface);map.reactivePhysicalFloorCallback(floor);
  int frame;int64_t ns,body_ns,cutoff;
  std::ifstream frames(input/"frames.txt");
  if(!(frames>>frame>>ns>>body_ns>>cutoff)||frame!=0)throw std::runtime_error("Missing original stair frame");
  std::ifstream list(input/"scans.txt");int index;int64_t stamp;std::string bf,sf,cf;size_t prefix=0;
  while(list>>index>>stamp>>bf>>sf>>cf) {
    if(stamp>cutoff)break;
    RecordedScan scan{index,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/bf)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sf)),std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cf,false))};
    scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    apply_scan(map,*node,scan);++prefix;
  }
  auto body=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/"query_0000.txt"));
  body->header.stamp=rclcpp::Time(body_ns,RCL_ROS_TIME);set_clock(*node,ns);map.slidingMapFrameCallback(body);
  const auto &p=body->pose.pose.position;const Eigen::Vector3d point(p.x,p.y,p.z);
  Eigen::MatrixXd controls(3,6);for(int i=0;i<6;++i)controls.col(i)=point;
  scan_planner::UniformBspline curve(controls,3,.1);
  const auto check=[&] {
    return reactive_stair::checkFullCubicTrajectory(curve,0,map.getResolution(),GridMap::collision_heading_lookahead_s,
      [&](const auto &a,const auto &b,const auto &v){return map.collisionTrajectoryYaw(a,b,v);},
      [&](const auto &a,double yaw){return map.getInflateOccupancy(a,yaw)!=0;});
  };
  if(!map.planningInputsReady()||!check().clear())throw std::runtime_error("Original fixture is not clear/fresh");
  const auto digest=map_digest(map);map.startAsyncMapping();const auto held=map.mapRevision();
  auto invalid=std::make_shared<sensor_msgs::msg::PointCloud2>(*floor);
  invalid->header.frame_id="wrong_physical_source";
  map.reactivePhysicalFloorCallback(invalid);
  const auto wait_revision=[&](uint64_t previous) {
    const auto limit=std::chrono::steady_clock::now()+std::chrono::seconds(3);
    while(std::chrono::steady_clock::now()<limit) {
      map.refreshSensorInputs("publication_contract_hold",-1,false);
      {std::lock_guard<std::mutex> lock(map.async_mapping_->publication_mutex);
       if(map.async_mapping_->latest->revision>previous)return map.async_mapping_->latest->revision;}
      std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    throw std::runtime_error("Support update did not complete");
  };
  const auto worker=wait_revision(held);
  if(map.mapRevision()!=held||map_digest(map)!=digest||!check().clear())throw std::runtime_error("Held search snapshot mutated");
  // These are the unchanged final-admission primitives used by PlannerManager.
  // This component negative does not claim to execute its whole optimizer.
  map.refreshSensorInputs("final_check");
  auto lease=map.beginPublication();
  if(map.mapRevision()!=worker||map.reactiveSurfaceGroundReady()||check().clear())throw std::runtime_error("Newest invalid support admitted the old clear curve");
  lease.reset();
  map.reactivePhysicalFloorCallback(floor);const auto restored=wait_revision(worker);
  map.refreshSensorInputs("final_check_restore");lease=map.beginPublication();
  if(map.mapRevision()!=restored||!map.reactiveSurfaceGroundReady()||!check().clear())throw std::runtime_error("Original support did not restore the clear curve");
  lease.reset();map.stopAsyncMapping();
  std::ofstream result(output/"publication_contract.json");
  result<<"{\"passed\":true,\"prefix_scans\":"<<prefix<<",\"held_revision\":"<<held
    <<",\"worker_revision\":"<<worker<<",\"restored_revision\":"<<restored
    <<",\"held_curve_clear\":true,\"newest_invalid_support_curve_rejected\":true,\"original_support_restored\":true,\"physics_steps\":0,\"scope\":\"Fixed-clock native final-admission primitives; no optimizer or physics\"}\n";
  rclcpp::shutdown();
}
