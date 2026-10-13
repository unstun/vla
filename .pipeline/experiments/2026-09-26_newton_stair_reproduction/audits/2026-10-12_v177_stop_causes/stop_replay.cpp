#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/full_trajectory_collision.h>
#include "v84/recording.h"

void inspect(GridMap &map,const Eigen::Vector3d &p,double yaw,const char *label) {
  std::cout<<std::setprecision(12)<<"STOP_POINT label="<<label<<" xyz="<<p.transpose()
           <<" yaw="<<yaw<<" occupied="<<map.getInflateOccupancy(p,yaw)<<std::endl;
  const Eigen::Vector3d h(std::cos(yaw),std::sin(yaw),0);
  for(double sign:{-1.,1.}) {
    const Eigen::Vector3d at=p+sign*map.mapState().mp_.double_cylinder_offset_*h;
    reactive_stair::Query q;q.frame=map.mapState().mp_.frame_id_;q.stamp_s=map.queryNow().seconds();
    q.x_m=at.x();q.y_m=at.y();q.z_m=at.z();q.in_map=map.isInMap(at);
    reactive_stair::NonTerrainVoxel o;o.frame=q.frame;o.stamp_s=map.mapState().reactive_cloud_stamp_s_;
    o.source_id="scan_lidar_cloud";o.occupancy=reactive_stair::Occupancy::Free;
    const bool support=map.reactiveFootprintSupportQuery(p,o,q);
    const bool gap=map.mapState().mp_.support_gap_mask_ && map.mapState().mp_.support_gap_mask_->blocks(
      at.x(),at.y(),at.z()-map.supportState().reactive_parameters_.body_clearance_m);
    Eigen::Vector3i id;map.posToIndex(at,id);const int address=map.toAddress(id);
    std::cout<<"STOP_CYLINDER label="<<label<<" sign="<<sign<<" xyz="<<at.transpose()
             <<" gap="<<gap<<" support="<<support<<" support_z="<<q.z_m
             <<" log_odds="<<map.mapState().md_.occupancy_buffer_[address]
             <<" inflated="<<int(map.mapState().md_.occupancy_buffer_inflate_[address])
             <<" raw="<<int(map.rawContributorOccupancy(id))
             <<" occupied="<<map.reactiveOccupancy(at,&p)<<std::endl;
  }
}

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);const fs::path input=std::getenv("REPLAY_INPUT");
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node");
  node->declare_parameter<bool>("grid_map.asynchronous_mapping",false);
  node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping",false));set_clock(*node,1000000000LL);
  scan_planner::SCANReplanFSM fsm;fsm.init(node.get());fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();
  auto map=fsm.planner_manager_->grid_map_;map->occ_timer_->cancel();map->vis_timer_->cancel();
  if(map->async_mapping_)throw std::runtime_error("Ordered reconstruction required");
  auto nav=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"navigation.f32",true));
  auto surface=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"surface.f32",true));
  auto floor=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"physical_floor.f32",true));
  nav->header.stamp=surface->header.stamp=floor->header.stamp=node->now();
  map->reactiveTomogramCallback(nav);map->reactiveSurfaceGroundCallback(surface);map->reactivePhysicalFloorCallback(floor);
  std::ifstream scans(input/"scans.txt");int i;int64_t stamp;std::string b,s,c;size_t applied=0;
  while(scans>>i>>stamp>>b>>s>>c) {
    RecordedScan scan{i,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/b)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/s)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/c,false))};
    scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    apply_scan(*map,*node,scan);++applied;
  }
  if(!scans.eof()||!applied)throw std::runtime_error("Invalid scans");
  int64_t query_ns,body_ns;std::ifstream qf(input/"query.txt");qf>>query_ns>>body_ns;
  if(!qf)throw std::runtime_error("Invalid query");
  auto body=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/"query_body.txt"));
  body->header.stamp=rclcpp::Time(body_ns,RCL_ROS_TIME);set_clock(*node,query_ns);map->slidingMapFrameCallback(body);
  const Eigen::Vector3d p=map->queryBodyPosition(),dir=map->reactive_body_quaternion_.toRotationMatrix().col(0);
  const double yaw=std::atan2(dir.y(),dir.x());
  std::cout<<"STOP_MAP healthy="<<map->mapperHealthy()<<" scans="<<applied<<" age="<<node->now().seconds()-map->observationStamp()<<std::endl;
  inspect(*map,p,yaw,"measured_body");
  size_t free_headings=0;
  for(int j=0;j<64;++j)if(map->getInflateOccupancy(p,2.0*std::acos(-1.0)*j/64.0)==0)++free_headings;
  std::cout<<"STOP_HEADINGS free="<<free_headings<<" tested=64"<<std::endl;
  if(fs::exists(input/"curve.txt")) {
    std::ifstream f(input/"curve.txt");size_t n;double phase;f>>n>>phase;Eigen::VectorXd knots(n+4);Eigen::MatrixXd pts(3,n);
    for(size_t j=0;j<n+4;++j)f>>knots(j);for(size_t j=0;j<n;++j)for(int k=0;k<3;++k)f>>pts(k,j);
    if(!f)throw std::runtime_error("Invalid curve");
    scan_planner::UniformBspline curve(pts,3,knots(4)-knots(3));curve.setKnot(knots);auto vel=curve.getDerivative();
    auto check=reactive_stair::checkFullCubicTrajectory(curve,phase,map->getResolution(),GridMap::collision_heading_lookahead_s,
      [&](const Eigen::Vector3d&p,const Eigen::Vector3d&a,const Eigen::Vector3d&v){return map->collisionTrajectoryYaw(p,a,v);},
      [&](const Eigen::Vector3d&p,double y){return map->getInflateOccupancy(p,y)!=0;});
    std::cout<<"STOP_CURVE status="<<int(check.status)<<" first="<<check.first_time_s<<" samples="<<check.samples<<std::endl;
    if(!check.clear() && check.status!=reactive_stair::TrajectoryCheckStatus::Collision)
      throw std::runtime_error("Invalid diagnostic curve; do not evaluate malformed input");
    const double t=check.clear()?std::min(phase,curve.getTimeSum()):check.first_time_s;
    const auto at=curve.evaluateDeBoorT(t),ahead=curve.evaluateDeBoorT(std::min(t+GridMap::collision_heading_lookahead_s,curve.getTimeSum()));
    inspect(*map,at,map->collisionTrajectoryYaw(at,ahead,vel.evaluateDeBoorT(t)),"curve_query");
    std::cout<<"STOP_TRACKING endpoint_error="<<(curve.evaluateDeBoorT(curve.getTimeSum())-p).head<2>().norm()<<std::endl;
  }
  std::cout<<"STOP_REPLAY_FINISHED"<<std::endl;rclcpp::shutdown();return 0;
}
