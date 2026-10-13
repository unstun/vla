#include <plan_env/grid_map.h>
#include <bspline_opt/full_trajectory_collision.h>
#include <rcl/time.h>
#include <openssl/sha.h>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include "map_meter.h"
namespace fs = std::filesystem;
#include "recorded_readers.h"
#include "map_digest.h"

int main(int argc,char **argv) {
  const fs::path input(std::getenv("V82_INPUT"));
  rclcpp::init(argc,argv);
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  const auto clock=[&](int64_t ns) {
    auto handle=node->get_clock()->get_clock_handle();
    if(rcl_enable_ros_time_override(handle)!=RCL_RET_OK || rcl_set_ros_time_override(handle,ns)!=RCL_RET_OK)
      throw std::runtime_error("Clock override failed");
  };
  int checks=0;
  const auto require=[&](bool value,const char *name) {
    if(!value) throw std::runtime_error(name);
    ++checks;
  };
  const auto wait=[&](const auto &condition) {
    const auto limit=std::chrono::steady_clock::now()+std::chrono::seconds(5);
    while(!condition()) {
      if(std::chrono::steady_clock::now()>limit) throw std::runtime_error("Contract wait failed");
      std::this_thread::sleep_for(std::chrono::microseconds(200));
    }
  };
  clock(1000000000);
  GridMap map;
  map.initMap(node.get());map.occ_timer_->cancel();map.vis_timer_->cancel();
  auto nav=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"navigation.f32",true));
  auto surface=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"surface.f32",true));
  auto physical=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"physical_floor.f32",true));
  nav->header.stamp=surface->header.stamp=physical->header.stamp=rclcpp::Time(1000000000LL,RCL_ROS_TIME);
  map.reactiveTomogramCallback(nav);map.reactiveSurfaceGroundCallback(surface);map.reactivePhysicalFloorCallback(physical);
  require(map.reactiveSurfaceGroundReady(),"Original paired support inputs");
  map.startAsyncMapping();
  require(map.async_mapping_!=nullptr,"Background writer started");
  try { map.resetBuffer();require(false,"Reader mutation was allowed"); }
  catch(const std::logic_error &) { ++checks; }
  std::ifstream list(input/"scans.txt");
  int index;int64_t ns;std::string body_name,sensor_name,cloud_name;
  require(bool(list>>index>>ns>>body_name>>sensor_name>>cloud_name),"Recorded first scan");
  auto body=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/body_name));
  auto sensor=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sensor_name));
  auto cloud=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cloud_name,false));
  const auto submit=[&](int64_t stamp,bool pose=true) {
    clock(stamp);
    body->header.stamp=sensor->header.stamp=cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    map.slidingMapFrameCallback(std::make_shared<nav_msgs::msg::Odometry>(*body));
    if(pose)map.sensorPoseCallback(std::make_shared<nav_msgs::msg::Odometry>(*sensor));
    map.cloudCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(*cloud));
  };
  const auto await_stamp=[&](int64_t stamp) {
    wait([&] {map.adoptMappingSnapshot();return map.mapState().reactive_cloud_ready_ &&
      std::abs(map.mapState().reactive_cloud_stamp_s_-double(stamp)*1e-9)<1e-8;});
  };
  submit(ns);await_stamp(ns);
  // Restore the recorded history before demanding an observed clear footprint;
  // one initial scan does not establish that evidence around the robot.
  int recorded_index;int64_t recorded_ns;std::string bn,sn,cn;
  while(list>>recorded_index>>recorded_ns>>bn>>sn>>cn) {
    body=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/bn));
    sensor=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sn));
    cloud=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cn,false));
    submit(recorded_ns);await_stamp(recorded_ns);
    ns=recorded_ns;
  }
  auto retained=map.read_state_;
  GridMap old;old.read_state_=retained;
  const auto original_digest=map_digest(old);
  const auto original_revision=map.mapRevision();
  require(original_revision>0,"Monotonic completed revision");
  const auto original_count=map.async_mapping_->latest->applied_clouds;

  // A cloud without an exact matching pose must not be transformed with the
  // preceding pose, and must not advance the last-applied cloud timestamp.
  submit(ns+100000000LL,false);
  std::this_thread::sleep_for(std::chrono::milliseconds(50));map.adoptMappingSnapshot();
  require(map.async_mapping_->latest->applied_clouds==original_count,"Unpaired cloud retained");
  require(std::abs(map.mapState().reactive_cloud_stamp_s_-double(ns)*1e-9)<1e-8,"Unpaired cloud not restamped");
  map.sensorPoseCallback(std::make_shared<nav_msgs::msg::Odometry>(*sensor));await_stamp(ns+100000000LL);
  require(map.mapRevision()>original_revision,"Exact pair publishes a new revision");
  require(map_digest(old)==original_digest,"Retained snapshot immutable");

  // Publication lease spans final full-curve validation through Bspline publish.
  // A newly computed map cannot invalidate that transaction halfway through.
  auto lease=map.beginPublication();
  const auto pinned_revision=map.mapRevision();
  submit(ns+200000000LL);
  std::this_thread::sleep_for(std::chrono::milliseconds(200));
  require(map.async_mapping_->latest->revision==pinned_revision,"Publication revision pinned");
  require(map.mapRevision()==pinned_revision,"Reader unchanged during publication");
  lease.reset();await_stamp(ns+200000000LL);
  require(map.mapRevision()>pinned_revision,"Newest completed snapshot adopted after publish");
  require(map_digest(old)==original_digest,"Concurrent old view still immutable");

  Eigen::Vector3d clear_point;
  bool found=false;
  const Eigen::Vector3d body_position(body->pose.pose.position.x,body->pose.pose.position.y,body->pose.pose.position.z);
  if(map.getInflateOccupancy(body_position,map.collisionSegmentYaw(body_position,body_position))==0) {clear_point=body_position;found=true;}
  {
    GridMap::RawContributorCacheScope cache(map);
    for(int x=-8;x<=8 && !found;++x)for(int y=-8;y<=8 && !found;++y)for(int z=-4;z<=4 && !found;++z) {
      const auto p=body_position+Eigen::Vector3d(x*.15,y*.15,z*.05);
      if((p-body_position).norm()<.15)continue;
      const double yaw=map.collisionSegmentYaw(p,p);
      if(map.getInflateOccupancy(p,yaw)==0) {clear_point=p;found=true;}
    }
  }
  if(!found) {
    std::cout << "V82_CLEAR_FIXTURE body=" << body_position.transpose() << " ray=" << map.mapState().md_.ray_pos_.transpose()
      << " stamp=" << map.mapState().reactive_cloud_stamp_s_ << " now=" << node->now().seconds()
      << " body_stamp=" << map.reactive_body_stamp_s_ << " support=" << map.reactiveSurfaceGroundReady()
      << " own_occupancy=" << map.getInflateOccupancy(body_position,map.collisionSegmentYaw(body_position,body_position)) << std::endl;
  }
  require(found,"Find a body footprint accepted by the original rules");
  Eigen::MatrixXd points(3,6);
  for(int i=0;i<6;++i)points.col(i)=clear_point;
  scan_planner::UniformBspline curve(points,3,.1);
  const auto check_curve=[&] {
    return reactive_stair::checkFullCubicTrajectory(curve,0,map.getResolution(),GridMap::collision_heading_lookahead_s,
      [&](const auto &p,const auto &ahead,const auto &velocity){return map.collisionTrajectoryYaw(p,ahead,velocity);},
      [&](const auto &p,double yaw){return map.getInflateOccupancy(p,yaw)!=0;});
  };
  require(check_curve().clear(),"Original complete-curve collision check passes");
  auto obstacle=std::make_shared<sensor_msgs::msg::PointCloud2>(*cloud);
  obstacle->width=1;obstacle->height=1;obstacle->row_step=obstacle->point_step;
  obstacle->data.resize(obstacle->point_step);
  const Eigen::Vector3d local=map.mapState().md_.ray_q_.conjugate()*(clear_point-map.mapState().md_.ray_pos_);
  const float xyz[]={float(local.x()),float(local.y()),float(local.z())};
  std::memcpy(obstacle->data.data(),xyz,sizeof(xyz));
  for(int i=1;i<=3;++i) {
    const int64_t stamp=ns+200000000LL+i*1000000LL;
    clock(stamp);body->header.stamp=sensor->header.stamp=obstacle->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    map.slidingMapFrameCallback(std::make_shared<nav_msgs::msg::Odometry>(*body));
    map.sensorPoseCallback(std::make_shared<nav_msgs::msg::Odometry>(*sensor));
    map.cloudCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(*obstacle));await_stamp(stamp);
  }
  {
    auto newest=map.beginPublication();
    require(!check_curve().clear(),"Newest occupancy rejects the previously clear complete curve");
  }
  const double checked_cloud_stamp=map.mapState().reactive_cloud_stamp_s_;

  // The existing freshness rule still blocks a completed map whose original
  // scan timestamp has aged. No snapshot publication grants a newer timestamp.
  clock(ns+1000000000LL);
  const Eigen::Vector3d point=map.mapState().md_.ray_pos_+Eigen::Vector3d(1,0,1);
  require(map.getInflateOccupancy(point,0)!=0,"Old scan freshness rejection retained");
  require(map.mapState().reactive_cloud_stamp_s_==checked_cloud_stamp,"Stale timestamp not extended");
  clock(ns+100000000LL);
  require(map.getInflateOccupancy(point,0)!=0,"Future scan freshness rejection retained");
  clock(ns+200000000LL);

  const auto support_revision=map.mapRevision();
  auto invalid=std::make_shared<sensor_msgs::msg::PointCloud2>(*physical);
  invalid->header.frame_id="wrong_physical_source";
  map.reactivePhysicalFloorCallback(invalid);
  wait([&] {map.adoptMappingSnapshot();return map.mapRevision()>support_revision;});
  require(!map.reactiveSurfaceGroundReady(),"Changed support source rejected");
  const auto invalid_revision=map.mapRevision();
  map.reactivePhysicalFloorCallback(physical);
  wait([&] {map.adoptMappingSnapshot();return map.mapRevision()>invalid_revision;});
  require(map.reactiveSurfaceGroundReady(),"Original support source restored");

  const auto before_failure=map_digest(map);
  map.enqueueMapping({999,ns+300000000LL,nullptr,nullptr});
  wait([&] {return !map.mapperHealthy();});
  map.adoptMappingSnapshot();
  require(map_digest(map)==before_failure,"Worker failure publishes no partial map");
  require(map.getInflateOccupancy(point,0)!=0,"Failed mapper cannot grant safety");
  require(!map.bodyEndpointMayBeObserved(clear_point),"Failed mapper cannot grant endpoint evidence");
  map.stopAsyncMapping();
  require(map.async_mapping_==nullptr,"Owned mapper joined on shutdown");
  require(map_digest(old)==original_digest,"Retained snapshot valid after shutdown");
  std::cout<<"V82_ASYNC_CONTRACT_PASS checks="<<checks<<std::endl;
  rclcpp::shutdown();
}
