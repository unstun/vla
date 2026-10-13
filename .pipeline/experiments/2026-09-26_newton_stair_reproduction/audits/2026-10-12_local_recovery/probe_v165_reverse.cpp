#include <plan_manage/scan_replan_fsm.h>
#include <plan_manage/reference_path_utils.h>
#include <bspline_opt/timed_cubic_initialization.h>
#include <bspline_opt/full_trajectory_collision.h>
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
  set_clock(*node,std::max(query_ns,body_ns)); map->slidingMapFrameCallback(body);
  const Eigen::Vector3d pos = map->queryBodyPosition();
  const Eigen::Vector3d direction = map->reactive_body_quaternion_.toRotationMatrix().col(0);
  const double measured_yaw = std::atan2(direction.y(), direction.x());
  double candidate_yaw; std::ifstream(input/"candidate_yaw.txt") >> candidate_yaw;
  std::cout << std::setprecision(12) << "FULL_ROUTE_MAP healthy=" << map->mapperHealthy()
            << " measured_yaw=" << measured_yaw << " candidate_yaw=" << candidate_yaw
            << " body=" << pos.transpose() << std::endl;
  for (double yaw : {measured_yaw, candidate_yaw, 0.0, 1.5707963267948966}) {
    std::cout << "FULL_ROUTE_HEADING yaw=" << yaw << " occupied=" << map->getInflateOccupancy(pos,yaw) << std::endl;
    const Eigen::Vector3d h(std::cos(yaw),std::sin(yaw),0.0);
    for (double sign : {-1.0,1.0}) {
      const Eigen::Vector3d p = pos + sign * map->mapState().mp_.double_cylinder_offset_ * h;
      reactive_stair::Query q; q.frame=map->mapState().mp_.frame_id_;q.stamp_s=node->now().seconds();q.x_m=p.x();q.y_m=p.y();q.z_m=p.z();q.in_map=map->isInMap(p);
      reactive_stair::NonTerrainVoxel o;o.frame=q.frame;o.stamp_s=map->mapState().reactive_cloud_stamp_s_;o.source_id="scan_lidar_cloud";o.occupancy=reactive_stair::Occupancy::Free;
      for (const Eigen::Vector3d at : {pos,p}) {
        auto &ground=map->supportState().reactive_ground_;
        reactive_stair::Cell2 cell{int(std::floor((at.x()-ground.origin_x_m)/ground.resolution_m)),int(std::floor((at.y()-ground.origin_y_m)/ground.resolution_m))};
        auto raw=ground.cells.find(cell);auto scored=map->supportState().reactive_terrain_.cells.find(cell);
        std::cout << "FULL_ROUTE_LAYERS xy=" << at.x() << " " << at.y() << " cell=" << cell.x << " " << cell.y;
        if(raw!=ground.cells.end()) for(size_t i=0;i<raw->second.size();++i) std::cout << " layer=" << raw->second[i].elevation_m << ":" << int(raw->second[i].support) << ":" << (scored!=map->supportState().reactive_terrain_.cells.end()&&i<scored->second.size()?int(scored->second[i].support):-1);
        std::cout << std::endl;
      }
      const bool supported=map->reactiveFootprintSupportQuery(pos,o,q);
      std::cout << "FULL_ROUTE_CYLINDER sign=" << sign << " p=" << p.transpose() << " support=" << supported << " adjusted_z=" << q.z_m << " occupied=" << map->reactiveOccupancy(p,&pos) << " gap_veto=" << (map->mapState().mp_.support_gap_mask_ && map->mapState().mp_.support_gap_mask_->blocks(p.x(),p.y(),p.z()-map->supportState().reactive_parameters_.body_clearance_m)) << std::endl;
      Eigen::Vector3i id;map->posToIndex(p,id);size_t printed=0,contributors=0;
      for (const auto &off : map->mapState().md_.inflate_offsets_) {
        const Eigen::Vector3i source=id-off;
        if(!map->isInMap(source)||map->mapState().md_.occupancy_buffer_[map->toAddress(source)]<=map->mapState().mp_.min_occupancy_log_)continue;
        ++contributors;if(printed++>=12)continue;
        Eigen::Vector3d xyz;map->indexToPos(source,xyz);auto key=std::make_tuple(source.x(),source.y(),source.z());
        std::cout << "FULL_ROUTE_CONTRIBUTOR xyz=" << xyz.transpose() << " terrain=" << map->mapState().reactive_terrain_hits_.count(key) << " nonterrain=" << map->mapState().reactive_nonterrain_hits_.count(key) << " history=" << map->mapState().reactive_nonterrain_history_.count(key) << std::endl;
      }
      std::cout << "FULL_ROUTE_CONTRIBUTORS count=" << contributors << std::endl;
    }
  }
  for(int dx=-2;dx<=2;++dx)for(int dy=-2;dy<=2;++dy){
    if((dx==0&&dy==0)||(std::abs(dx)==2&&dy==0)||(std::abs(dy)==2&&dx==0)||(std::abs(dx)==2&&std::abs(dy)==2))continue;
    const Eigen::Vector3d target=pos+map->getResolution()*Eigen::Vector3d(dx,dy,0);
    const double yaw=std::atan2(double(dy),double(dx));
    std::cout<<"V156_START_EDGE dx="<<dx<<" dy="<<dy<<" yaw="<<yaw
      <<" start_free="<<(map->getInflateOccupancy(pos,yaw)==0)
      <<" segment_free="<<map->collisionFreeSegment(pos,target)<<std::endl;
  }
  for(double distance : {.05,.1,.2,.3}) {
    size_t normal_count=0,fixed_count=0;
    for(int angle_index=-1;angle_index<64;++angle_index) {
      const double yaw=angle_index<0?measured_yaw:angle_index*2.0*std::acos(-1.0)/64.0;
      const Eigen::Vector3d delta(distance*std::cos(yaw),distance*std::sin(yaw),0);
      const bool normal=map->collisionFreeSegment(pos,pos+delta);
      bool fixed=true;
      for(int j=0;j<=100;++j) if(map->getInflateOccupancy(pos+delta*(j/100.0),measured_yaw)!=0){fixed=false;break;}
      normal_count+=normal;fixed_count+=fixed;
      if(normal||fixed||angle_index<0)std::cout<<"V156_CONTINUOUS_DIRECTION distance="<<distance<<" yaw="<<yaw<<" path_heading_free="<<normal<<" fixed_body_yaw_free="<<fixed<<std::endl;
    }
    std::cout<<"V156_DIRECTION_COUNTS distance="<<distance<<" normal="<<normal_count<<" fixed="<<fixed_count<<std::endl;
  }
  map->logInitialSplineCollision(pos,candidate_yaw);
  std::cout<<"FULL_ROUTE_DIGEST "<<map_digest(*map)<<std::endl;
  if (std::getenv("PREFIX_BUDGET")) {
    fsm.odometryCallback(body);
    std::ifstream file(input/"route.txt");size_t n;file>>n;nav_msgs::msg::Path path;
    for(size_t i=0;i<n;++i){geometry_msgs::msg::PoseStamped pose;file>>pose.pose.position.x>>pose.pose.position.y>>pose.pose.position.z;path.poses.push_back(pose);}
    if(!file)throw std::runtime_error("Invalid recorded route");
    std::vector<Eigen::Vector3d> waypoints;std::string error;
    if(!scan_planner::prepareReferenceWaypoints(path,fsm.body_height_,fsm.reference_path_min_distance_,waypoints,&error,fsm.reference_path_simplify_tolerance_))throw std::runtime_error(error);
    const bool reference=fsm.planGlobalTrajByWaypoints(waypoints);
    std::cout<<"FULL_ROUTE_REFERENCE accepted="<<reference<<" points="<<waypoints.size()<<std::endl;
    if(!reference)throw std::runtime_error("Recorded reference admission failed");
    fsm.start_pt_=pos;fsm.start_vel_.setZero();fsm.start_acc_.setZero();
    fsm.exec_state_=scan_planner::SCANReplanFSM::GEN_NEW_TRAJ;
    int budget=std::atoi(std::getenv("PREFIX_BUDGET"));const int original=budget;
    const bool accepted=fsm.callReboundReplan(true,false,original>0?&budget:nullptr);
    std::cout<<"FULL_ROUTE_PREFIX budget="<<original<<" accepted="<<accepted<<" remaining="<<budget<<" target="<<fsm.local_target_pt_.transpose()<<std::endl;
    if(accepted){
      auto curve=fsm.planner_manager_->local_data_.position_traj_;
      std::vector<Eigen::Vector3d> boundary{fsm.start_vel_,fsm.local_target_vel_,fsm.start_acc_,Eigen::Vector3d::Zero()};
      auto checked=reactive_stair::checkFullCubicTrajectory(curve,0.0,map->getResolution(),GridMap::collision_heading_lookahead_s,[&](const Eigen::Vector3d&p,const Eigen::Vector3d&a,const Eigen::Vector3d&v){return map->collisionTrajectoryYaw(p,a,v);},[&](const Eigen::Vector3d&p,double y){return map->getInflateOccupancy(p,y)!=0;});
      if(!checked.clear()||!reactive_stair::matchesBoundaryPva(curve,pos,fsm.local_target_pt_,boundary)||!fsm.planner_manager_->checkDynamicFeasibility(curve))throw std::runtime_error("Prefix violated original gates");
      std::cout<<"FULL_ROUTE_PREFIX_VALIDATED duration="<<curve.getTimeSum()<<" samples="<<checked.samples<<std::endl;
    }
  }
  const Eigen::Vector3d backward=pos-map->getResolution()*Eigen::Vector3d(std::cos(measured_yaw),std::sin(measured_yaw),0);
  auto &manager=fsm.planner_manager_;
  manager->invalidateWarmStart();
  bool accepted=manager->reboundReplan(pos,Eigen::Vector3d::Zero(),Eigen::Vector3d::Zero(),backward,Eigen::Vector3d::Zero(),true,false);
  std::cout<<"REVERSE_DIAGNOSTIC accepted="<<accepted<<" target="<<backward.transpose()<<" fixed_yaw="<<measured_yaw<<std::endl;
  if(accepted) {
    auto curve=manager->local_data_.position_traj_;
    auto fixed=reactive_stair::checkFullCubicTrajectory(curve,0.,map->getResolution(),GridMap::collision_heading_lookahead_s,
      [&](const Eigen::Vector3d&,const Eigen::Vector3d&,const Eigen::Vector3d&){return measured_yaw;},
      [&](const Eigen::Vector3d&p,double yaw){return map->getInflateOccupancy(p,yaw)!=0;});
    std::vector<Eigen::Vector3d> boundary(4,Eigen::Vector3d::Zero());
    bool pva=reactive_stair::matchesBoundaryPva(curve,pos,backward,boundary);
    bool dynamics=manager->checkDynamicFeasibility(curve);
    std::cout<<"REVERSE_DIAGNOSTIC_VALIDATED fixed_clear="<<fixed.clear()<<" samples="<<fixed.samples<<" pva="<<pva<<" dynamics="<<dynamics<<" duration="<<curve.getTimeSum()<<std::endl;
    if(!fixed.clear()||!pva||!dynamics)throw std::runtime_error("Backward proposal did not pass all unchanged checks");
  }
  rclcpp::shutdown();return 0;
}
