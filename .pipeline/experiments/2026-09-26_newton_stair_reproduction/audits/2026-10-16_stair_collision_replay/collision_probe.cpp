// Diagnostic observer over the installed frozen map; no production source edits.
#include "v84/recording.h"
#include <plan_env/known_lite3_trunk.h>
#include <plan_env/raw_return_classification.h>
#include <array>

struct Explanation { int reason=0, occupancy=-1; double support_z=0; Eigen::Vector3d witness=Eigen::Vector3d::Zero(); };

void detail(GridMap &map,std::ostream &out,int frame,int id,int kind,int side,const Eigen::Vector3d &body,const Eigen::Vector3d &point,const Explanation &e) {
  const auto &s=map.mapState();const auto &support=map.supportState();
  auto nearest=[&](double x,double y,double target) {
    const auto &t=support.reactive_terrain_;
    const reactive_stair::Cell2 cell{int(std::floor((x-t.origin_x_m)/t.resolution_m)),int(std::floor((y-t.origin_y_m)/t.resolution_m))};
    double best=1e9,z=1e9;int label=-1;
    auto found=t.cells.find(cell);
    if(found!=t.cells.end())for(const auto &v:found->second)if(std::abs(v.elevation_m-target)<best){best=std::abs(v.elevation_m-target);z=v.elevation_m;label=int(v.support);}
    return std::array<double,3>{z,best,double(label)};
  };
  const auto b=nearest(body.x(),body.y(),body.z()-support.reactive_parameters_.body_clearance_m);
  const auto f=nearest(point.x(),point.y(),b[0]);
  Eigen::Vector3d witness=Eigen::Vector3d::Zero();int terrain=0,live_nonterrain=0,history=0,count=0;double distance=1e9;
  Eigen::Vector3i idc;map.posToIndex(point,idc);
  if(map.isInMap(idc))for(const auto &offset:s.md_.inflate_offsets_) {
    Eigen::Vector3i source=idc-offset;
    if(!map.isInMap(source)||s.md_.occupancy_buffer_[map.toAddress(source)]<=s.mp_.min_occupancy_log_)continue;
    auto key=std::make_tuple(source.x(),source.y(),source.z());
    int a=s.reactive_terrain_hits_.count(key),b=s.reactive_nonterrain_hits_.count(key),c=s.reactive_nonterrain_history_.count(key);
    if(reactive_stair::mayWaiveRawContributor(a,b,c))continue;
    ++count;Eigen::Vector3d xyz;map.indexToPos(source,xyz);double d=(xyz-point).norm();
    if(d<distance){distance=d;witness=xyz;terrain=a;live_nonterrain=b;history=c;}
  }
  out<<frame<<','<<id<<','<<kind<<','<<side<<','<<body.x()<<','<<body.y()<<','<<body.z()<<','<<point.x()<<','<<point.y()<<','<<point.z()<<','<<e.reason<<','<<e.occupancy<<','<<b[0]<<','<<b[1]<<','<<b[2]<<','<<f[0]<<','<<f[1]<<','<<f[2]<<','<<count<<','<<witness.x()<<','<<witness.y()<<','<<witness.z()<<','<<terrain<<','<<live_nonterrain<<','<<history<<'\n';
}

Explanation explain(GridMap &map,const Eigen::Vector3d &point,const Eigen::Vector3d &body) {
  Explanation out;const auto &s=map.mapState();const auto &p=s.mp_;const auto &support=map.supportState();
  if(!map.mapperHealthy()){out.reason=10;return out;}
  if(!map.reactiveSurfaceGroundReady()){out.reason=11;return out;}
  if(p.support_gap_mask_ && p.support_gap_mask_->blocks(point.x(),point.y(),point.z()-support.reactive_parameters_.body_clearance_m)) {out.reason=12;return out;}
  Eigen::Vector3d lower,upper;
  if(!point.allFinite() || !map.bodyCenterBounds(lower,upper) || (point.array()<lower.array()).any() || (point.array()>upper.array()).any()) {out.reason=13;return out;}
  reactive_stair::Query query{p.frame_id_,map.queryNow().seconds(),point.x(),point.y(),point.z(),map.isInMap(point)};
  reactive_stair::NonTerrainVoxel obstacle;
  obstacle.frame=p.frame_id_;obstacle.stamp_s=s.reactive_cloud_stamp_s_;
  if(s.reactive_cloud_ready_)obstacle.source_id="scan_lidar_cloud";
  Eigen::Vector3i id;map.posToIndex(point,id);const int address=map.toAddress(id);
  if(s.md_.occupancy_buffer_[address]<p.clamp_min_log_-1e-3)obstacle.occupancy=reactive_stair::Occupancy::Unknown;
  else if(s.md_.occupancy_buffer_inflate_[address]==0)obstacle.occupancy=reactive_stair::Occupancy::Free;
  else obstacle.occupancy=map.rawContributorOccupancy(id);
  if(s.reactive_known_trunk_enabled_ && map.reactive_body_stamp_s_>0) {
    const auto local=map.reactive_body_quaternion_.conjugate()*(point-map.queryBodyPosition());
    const bool inside=reactive_stair::knownNavigationFootprintInterior(local.x(),local.y(),local.z(),query.stamp_s,map.reactive_body_stamp_s_,p.double_cylinder_radius_,p.double_cylinder_offset_);
    obstacle.occupancy=reactive_stair::measuredTrunkQuery(obstacle.occupancy,s.md_.occupancy_buffer_inflate_[address]!=0,inside);
  }
  out.occupancy=int(obstacle.occupancy);
  if(!map.reactiveFootprintSupportQuery(body,obstacle,query)) {
    auto b=query;b.x_m=body.x();b.y_m=body.y();b.z_m=body.z();b.in_map=map.isInMap(body);
    auto free=obstacle;free.occupancy=reactive_stair::Occupancy::Free;
    const auto reason=support.reactive_decision_.decide(b,free);
    out.reason=reason==reactive_stair::Verdict::Free?26:100+int(reason);
    return out;
  }
  out.support_z=query.z_m;
  const auto verdict=support.reactive_decision_.decide(query,obstacle);
  out.reason=verdict==reactive_stair::Verdict::Free?0:100+int(verdict);
  if(obstacle.occupancy==reactive_stair::Occupancy::Occupied) {
    for(const auto &offset:s.md_.inflate_offsets_) {
      const Eigen::Vector3i source=id-offset;
      if(!map.isInMap(source)||s.md_.occupancy_buffer_[map.toAddress(source)]<=p.min_occupancy_log_)continue;
      const auto key=std::make_tuple(source.x(),source.y(),source.z());
      if(!reactive_stair::mayWaiveRawContributor(s.reactive_terrain_hits_.count(key),s.reactive_nonterrain_hits_.count(key),s.reactive_nonterrain_history_.count(key))) {
        map.indexToPos(source,out.witness);break;
      }
    }
  }
  return out;
}

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  const fs::path input=std::getenv("REPLAY_INPUT"),output=std::getenv("REPLAY_OUTPUT");
  fs::create_directories(output);
  rclcpp::NodeOptions options;options.use_global_arguments(true);
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);
  node->declare_parameter<bool>("grid_map.asynchronous_mapping",false);
  node->set_parameter(rclcpp::Parameter("grid_map.asynchronous_mapping",false));
  GridMap map;initialize_map(map,*node,input);
  std::ifstream listing(input/"scans.txt");
  std::vector<RecordedScan> scans;int i;int64_t stamp;std::string bf,sf,cf;
  while(listing>>i>>stamp>>bf>>sf>>cf) {
    RecordedScan scan{i,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/bf)),std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sf)),std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cf,false))};
    scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    scans.push_back(std::move(scan));
  }
  if(scans.empty())throw std::runtime_error("Empty prefix");
  std::ifstream frames(input/"frames.txt");int frame;int64_t query_ns,body_ns,cutoff;std::string bodyfile,queries;
  size_t applied=0,total=0;std::ofstream summary(output/"frames.csv");summary<<"frame,query_ns,cloud_ns,scans,queries,blocked,parity_errors\n";
  std::ofstream details(output/"details.csv");details<<std::setprecision(17)<<"frame,id,kind,side,body_x,body_y,body_z,query_x,query_y,query_z,reason,occupancy,body_ground,height_error,body_support,footprint_ground,footprint_delta,footprint_support,blocking_sources,witness_x,witness_y,witness_z,terrain_seen,nonterrain_now,nonterrain_history\n";
  while(frames>>frame>>query_ns>>body_ns>>cutoff>>bodyfile>>queries) {
    while(applied<scans.size()&&scans[applied].stamp<=cutoff){apply_scan(map,*node,scans[applied]);++applied;}
    if(!applied||scans[applied-1].stamp!=cutoff)throw std::runtime_error("Snapshot source cutoff mismatch");
    auto body=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/bodyfile));body->header.stamp=rclcpp::Time(body_ns,RCL_ROS_TIME);
    set_clock(*node,query_ns);map.slidingMapFrameCallback(body);
    std::ifstream points(input/queries);std::ofstream csv(output/("frame_"+std::to_string(frame)+".csv"));
    csv<<std::setprecision(17)<<"id,kind,x,y,z,yaw,native,original_same_map,front_reason,rear_reason,front_occupancy,rear_occupancy,front_support_z,rear_support_z,witness_x,witness_y,witness_z\n";
    GridMap::RawContributorCacheScope cache(map);
    int id,kind;double x,y,z,yaw;size_t count=0,blocked=0;
    while(points>>id>>kind>>x>>y>>z>>yaw) {
      const Eigen::Vector3d center(x,y,z),heading(std::cos(yaw),std::sin(yaw),0);
      const auto front=center+map.mapState().mp_.double_cylinder_offset_*heading;
      const auto rear=center-map.mapState().mp_.double_cylinder_offset_*heading;
      const int native=map.getInflateOccupancy(center,yaw);
      const int old_front=map.getInflateOccupancyFromBuffer(front,map.mapState().md_.occupancy_buffer_inflate_);
      const int original=old_front!=0?old_front:map.getInflateOccupancyFromBuffer(rear,map.mapState().md_.occupancy_buffer_inflate_);
      const auto a=explain(map,front,center),b=explain(map,rear,center);
      if(bool(native)!=bool(a.reason||b.reason))throw std::runtime_error("Explanation differs from frozen native decision");
      if(kind!=2){detail(map,details,frame,id,kind,0,center,front,a);detail(map,details,frame,id,kind,1,center,rear,b);}
      const auto witness=a.witness.squaredNorm()>0?a.witness:b.witness;
      csv<<id<<','<<kind<<','<<x<<','<<y<<','<<z<<','<<yaw<<','<<native<<','<<original<<','<<a.reason<<','<<b.reason<<','<<a.occupancy<<','<<b.occupancy<<','<<a.support_z<<','<<b.support_z<<','<<witness.x()<<','<<witness.y()<<','<<witness.z()<<'\n';
      ++count;blocked+=native!=0;
    }
    if(!points.eof()||!count)throw std::runtime_error("Invalid query file");
    summary<<frame<<','<<query_ns<<','<<cutoff<<','<<applied<<','<<count<<','<<blocked<<",0\n";summary.flush();total+=count;
    std::cout<<"AUDIT_FRAME "<<frame<<" queries="<<count<<" blocked="<<blocked<<" scans="<<applied<<std::endl;
  }
  std::cout<<"AUDIT_COMPLETE queries="<<total<<" parity_errors=0\n";
  rclcpp::shutdown();return 0;
}
