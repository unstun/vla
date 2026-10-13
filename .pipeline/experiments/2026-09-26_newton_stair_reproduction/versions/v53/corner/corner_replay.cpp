#include <plan_manage/scan_replan_fsm.h>
#include <rcl/time.h>
#include <rclcpp/serialization.hpp>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <cstring>
#include <stdexcept>
#include <bspline_opt/full_trajectory_collision.h>
using namespace scan_planner;
template<class T> T decode(const std::vector<char>&bytes) {
  rclcpp::SerializedMessage data(bytes.size());auto &raw=data.get_rcl_serialized_message();
  std::memcpy(raw.buffer,bytes.data(),bytes.size());raw.buffer_length=bytes.size();T msg;rclcpp::Serialization<T>().deserialize_message(&data,&msg);return msg;
}
sensor_msgs::msg::PointCloud2 ground(const char *path) {
  std::ifstream f(path,std::ios::binary);sensor_msgs::msg::PointCloud2 m;
  m.data=std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});if(m.data.empty())throw std::runtime_error("ground missing");
  m.header.frame_id="world";m.header.stamp.sec=1;m.point_step=16;m.height=1;m.width=m.data.size()/16;m.row_step=m.data.size();m.is_dense=true;
  for(int i=0;i<4;++i){sensor_msgs::msg::PointField x;x.name=std::vector<std::string>{"x","y","z","intensity"}[i];x.offset=4*i;x.datatype=x.FLOAT32;x.count=1;m.fields.push_back(x);}return m;
}
template<class T>std::string owner(const T&id){std::ostringstream s;s<<std::quoted(id.run_id)<<' '<<id.epoch<<' '<<std::quoted(id.request_id)<<' '<<std::quoted(id.goal_id)<<' '<<std::quoted(id.route_id)<<' '<<std::quoted(id.command_id)<<' '<<id.generation<<' '<<std::quoted(id.map_epoch)<<' '<<id.map_revision;return s.str();}

template<class T> auto context(T &fsm, int) -> decltype(fsm.warmStartIdentity()) {return fsm.warmStartIdentity();}
template<class T> std::string context(T &fsm, long) {return owner(fsm.active_p2b_identity_);}
template<class T> auto goalContext(T &fsm, int) -> decltype(fsm.warmGoalContext()) {return fsm.warmGoalContext();}
template<class T> Eigen::Vector3d goalContext(T &fsm, long) {return fsm.end_pt_;}
template<class T> auto worldWindow(T &fsm, int) -> decltype(fsm.feasible_window_.world_geometry_valid, void()) {
 auto &w=fsm.feasible_window_;auto &g=fsm.planner_manager_->global_data_;
 w.world_geometry_valid=true;w.endpoint_world=g.getPosition(w.projection+w.span);
 w.projection_world=g.getPosition(w.projection);w.measured_world=g.getPosition(w.measured_projection);w.growth_world=g.getPosition(w.growth_projection);
}
template<class T> void worldWindow(T &, long) {}

std::string xyz(const Eigen::Vector3d &p) {
 std::ostringstream s;s<<std::setprecision(17)<<"["<<p.x()<<","<<p.y()<<","<<p.z()<<"]";return s.str();
}
int main(int argc,char**argv) {
 rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");SCANReplanFSM fsm;fsm.init(node.get());fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();auto &manager=*fsm.planner_manager_;auto map=manager.grid_map_;map->occ_timer_->cancel();map->vis_timer_->cancel();
 auto clock=[&](int64_t ns){auto*h=node->get_clock()->get_clock_handle();if(rcl_enable_ros_time_override(h)!=RCL_RET_OK||rcl_set_ros_time_override(h,ns)!=RCL_RET_OK)throw std::runtime_error("clock");};clock(1000000000);
 map->reactiveTomogramCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/versions/v36/tests/attempt09/v33_stand/converted_inputs/ground.f32")));
 map->reactiveSurfaceGroundCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32")));
 std::ifstream stream("/attempt/replay/events.bin",std::ios::binary);std::ofstream results("/attempt/probes.jsonl");int cases=0;
 while(true){uint8_t type;int64_t ns;uint32_t size;if(!stream.read(reinterpret_cast<char*>(&type),1))break;stream.read(reinterpret_cast<char*>(&ns),8);stream.read(reinterpret_cast<char*>(&size),4);std::vector<char> bytes(size);stream.read(bytes.data(),size);if(!stream)throw std::runtime_error("truncated replay");clock(ns);
  if(type==0){auto m=std::make_shared<nav_msgs::msg::Odometry>(decode<nav_msgs::msg::Odometry>(bytes));map->slidingMapFrameCallback(m);fsm.odometryCallback(m);}
  else if(type==1)map->sensorPoseCallback(std::make_shared<nav_msgs::msg::Odometry>(decode<nav_msgs::msg::Odometry>(bytes)));
  else if(type==2)map->cloudCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(decode<sensor_msgs::msg::PointCloud2>(bytes)));
  else if(type==3)fsm.p2bRouteCallback(std::make_shared<scan_planner_msgs::msg::P2BRoute>(decode<scan_planner_msgs::msg::P2BRoute>(bytes)));
  else if(type==4){auto m=decode<scan_planner_msgs::msg::Bspline>(bytes);Eigen::MatrixXd p(3,m.pos_pts.size());for(size_t i=0;i<m.pos_pts.size();++i)p.col(i)<<m.pos_pts[i].x,m.pos_pts[i].y,m.pos_pts[i].z;Eigen::VectorXd k(m.knots.size());for(size_t i=0;i<m.knots.size();++i)k[i]=m.knots[i];if(!reactive_stair::validSplineLayout(p,k,3))throw std::runtime_error("archived curve invalid");UniformBspline c(p,3,k[4]-k[3]);c.setKnot(k);auto &l=manager.local_data_;l.position_traj_=c;l.velocity_traj_=c.getDerivative();l.acceleration_traj_=l.velocity_traj_.getDerivative();l.duration_=c.getTimeSum();l.start_time_=rclcpp::Time(m.start_time,RCL_ROS_TIME);l.traj_id_=m.traj_id;l.start_pos_=c.evaluateDeBoorT(0);fsm.have_new_target_=false;
   if(!m.emergency_stop && owner(m)==owner(fsm.active_p2b_identity_)){manager.accepted_warm_context_=context(fsm,0);manager.accepted_warm_goal_=goalContext(fsm,0);manager.accepted_warm_traj_id_=l.traj_id_;manager.accepted_warm_map_=map.get();}else manager.invalidateWarmStart();
  }else if(type==5){uint32_t id;std::memcpy(&id,bytes.data(),4);++cases;
   std::cout<<"CORNER_CASE "<<id<<" simulation_s="<<std::setprecision(17)<<ns*1e-9<<std::endl;
   if(id==0){auto &w=fsm.feasible_window_;w.valid=true;w.identity=fsm.active_p2b_identity_;w.map=map.get();w.goal=goalContext(fsm,0);w.span=.330816382937;w.projection=.525;w.measured_projection=.525;w.growth_projection=.525;w.stamp=42.338359833;worldWindow(fsm,0);}
   if(id==1) results << "{\"kind\":\"refresh_binding\",\"retained\":" << (manager.accepted_warm_traj_id_==manager.local_data_.traj_id_ && fsm.feasible_window_.valid) << "}\n";
   const auto saved_local=manager.local_data_;const auto saved_global=manager.global_data_;const auto saved_window=fsm.feasible_window_;const auto goal=fsm.end_pt_;const auto saved_context=manager.accepted_warm_context_;const auto saved_warm_goal=manager.accepted_warm_goal_;const auto saved_id=manager.accepted_warm_traj_id_;const auto saved_map=manager.accepted_warm_map_;const bool saved_new=fsm.have_new_target_;
   auto restore=[&](){manager.local_data_=saved_local;manager.global_data_=saved_global;fsm.feasible_window_=saved_window;fsm.end_pt_=goal;fsm.have_new_target_=saved_new;manager.accepted_warm_context_=saved_context;manager.accepted_warm_goal_=saved_warm_goal;manager.accepted_warm_traj_id_=saved_id;manager.accepted_warm_map_=saved_map;};
   const double t=std::clamp((id==3?42.353351593:node->now().seconds())-saved_local.start_time_.seconds(),0.0,saved_local.duration_);
   const Eigen::Vector3d p=saved_local.position_traj_.evaluateDeBoorT(t), v=saved_local.velocity_traj_.evaluateDeBoorT(t),acc=saved_local.acceleration_traj_.evaluateDeBoorT(t),endpoint=saved_local.position_traj_.evaluateDeBoorT(saved_local.duration_);
   results<<std::setprecision(17)<<"{\"case\":"<<id<<",\"kind\":\"state\",\"simulation_s\":"<<ns*1e-9<<",\"curve_start_s\":"<<saved_local.start_time_.seconds()<<",\"duration_s\":"<<saved_local.duration_<<",\"traj_id\":"<<saved_local.traj_id_<<",\"accepted_warm_id\":"<<saved_id<<",\"feasible_window_valid\":"<<saved_window.valid<<",\"start\":"<<xyz(p)<<",\"velocity\":"<<xyz(v)<<",\"acceleration\":"<<xyz(acc)<<",\"endpoint\":"<<xyz(endpoint)<<",\"odom\":"<<xyz(fsm.odom_pos_)<<",\"goal\":"<<xyz(goal)<<"}\n";
   fsm.start_pt_=p;fsm.start_vel_=v;fsm.start_acc_=acc;bool targetok=fsm.getLocalTarget();auto nominal=fsm.local_target_pt_;
   auto checkPoint=[&](const char *label,const Eigen::Vector3d &q,double yaw){
    const int blocked=map->getInflateOccupancy(q,yaw);
    results<<"{\"case\":"<<id<<",\"kind\":\"point\",\"label\":\""<<label<<"\",\"xyz\":"<<xyz(q)<<",\"yaw\":"<<yaw<<",\"blocked\":"<<blocked<<",\"caps\":[";
    for(int sign:{1,-1}){Eigen::Vector3d cap=q+sign*map->mp_.double_cylinder_offset_*Eigen::Vector3d(std::cos(yaw),std::sin(yaw),0);Eigen::Vector3i index;map->posToIndex(cap,index);auto addr=map->toAddress(index);reactive_stair::Query query;query.frame=map->mp_.frame_id_;query.stamp_s=node->now().seconds();query.x_m=cap.x();query.y_m=cap.y();query.z_m=cap.z();query.in_map=map->isInMap(cap);reactive_stair::NonTerrainVoxel free;free.frame=query.frame;free.stamp_s=map->reactive_cloud_stamp_s_;free.source_id="scan_lidar_cloud";free.occupancy=reactive_stair::Occupancy::Free;
     bool support=map->reactiveFootprintSupportQuery(q,free,query);auto bodyquery=query;bodyquery.x_m=q.x();bodyquery.y_m=q.y();bodyquery.z_m=q.z();bodyquery.in_map=map->isInMap(q);auto bodyverdict=map->reactive_decision_.decide(bodyquery,free);
     if(sign==-1)results<<",";results<<"{\"xyz\":"<<xyz(cap)<<",\"support_association\":"<<support<<",\"body_support_verdict\":"<<int(bodyverdict)<<",\"reactive_blocked\":"<<map->reactiveOccupancy(cap,&q)<<",\"log_odds\":"<<map->md_.occupancy_buffer_[addr]<<",\"inflation\":"<<int(map->md_.occupancy_buffer_inflate_[addr])<<",\"raw_contributors\":"<<int(map->rawContributorOccupancy(index))<<",\"layers\":[";
     const auto &raw=map->reactive_ground_;reactive_stair::Cell2 cell{int(std::floor((cap.x()-raw.origin_x_m)/raw.resolution_m)),int(std::floor((cap.y()-raw.origin_y_m)/raw.resolution_m))};auto layers=map->terrainCellLayers(cell);
     if(layers.raw && layers.scored){for(size_t i=0;i<layers.raw->size();++i){if(i)results<<",";results<<"{\"raw_z\":"<<(*layers.raw)[i].elevation_m<<",\"scored_z\":"<<(*layers.scored)[i].elevation_m<<",\"support\":"<<int((*layers.scored)[i].support)<<"}";}}
     
     results<<"],\"navigation_layers\":[";
     auto emitLayers=[&](const reactive_stair::TerrainSnapshot &src){auto ix=int(std::floor((cap.x()-src.origin_x_m)/src.resolution_m));auto iy=int(std::floor((cap.y()-src.origin_y_m)/src.resolution_m));auto f=src.cells.find({ix,iy});if(f!=src.cells.end())for(size_t j=0;j<f->second.size();++j){if(j)results<<",";results<<f->second[j].elevation_m;}};
     emitLayers(map->reactive_navigation_ground_);results<<"],\"evidence_layers\":[";emitLayers(map->reactive_surface_ground_);
     results<<"],\"nearby_drop_examples\":[";
     const auto &evidence=map->reactive_surface_ground_;int ex=int(std::floor((cap.x()-evidence.origin_x_m)/evidence.resolution_m)),ey=int(std::floor((cap.y()-evidence.origin_y_m)/evidence.resolution_m));auto center=evidence.cells.find({ex,ey});double level=q.z()-map->reactive_parameters_.body_clearance_m;
     if(center!=evidence.cells.end()){int layer=reactive_stair::nearestSurface(center->second,level,map->reactive_parameters_.body_height_tolerance_m);if(layer>=0)level=center->second[layer].elevation_m;}
     int count=0;const double resolution=evidence.resolution_m, radius=map->mp_.double_cylinder_radius_,step=reactive_stair::StepScoreParameters{}.critical_height_m;int reach=int(std::ceil(radius/resolution))+1;
     for(int dx=-reach;dx<=reach && count<3;++dx)for(int dy=-reach;dy<=reach && count<3;++dy){double gx=std::max(0,std::abs(dx)-1)*resolution,gy=std::max(0,std::abs(dy)-1)*resolution;if(gx*gx+gy*gy>radius*radius+1e-12)continue;auto cell=evidence.cells.find({ex+dx,ey+dy});bool lower=false,near=false;if(cell!=evidence.cells.end())for(const auto &l:cell->second){near|=std::abs(l.elevation_m-level)<=step;lower|=l.elevation_m<level-step;}bool drop=cell==evidence.cells.end()||(!near&&lower);if(!drop)continue;
      if(count++)results<<",";results<<"{\"xy\":["<<evidence.origin_x_m+(ex+dx+.5)*resolution<<","<<evidence.origin_y_m+(ey+dy+.5)*resolution<<"],\"reference_level\":"<<level<<",\"layers\":[";if(cell!=evidence.cells.end())for(size_t j=0;j<cell->second.size();++j){if(j)results<<",";results<<cell->second[j].elevation_m;}results<<"]}";
     }
     results<<"]}";
    }results<<"]}\n";
   };
   results<<"{\"case\":"<<id<<",\"kind\":\"target\",\"valid\":"<<targetok<<",\"time\":"<<fsm.local_target_time_<<",\"xyz\":"<<xyz(nominal)<<"}\n";
   checkPoint("planned_start_to_new_target",p,std::atan2(nominal.y()-p.y(),nominal.x()-p.x()));
   checkPoint("old_endpoint",endpoint,std::atan2(nominal.y()-p.y(),nominal.x()-p.x()));
   checkPoint("measured_same_yaw",fsm.odom_pos_,std::atan2(nominal.y()-p.y(),nominal.x()-p.x()));
   if(id==1 || id==3){for(double time:{1.75,.875,.4375}){auto q=manager.global_data_.getPosition(time);checkPoint("prefix",q,std::atan2(q.y()-p.y(),q.x()-p.x()));} }
   if(id==3){for(double query_time:{42.553241730,42.578227997})for(double prefix_time:{.875,.4375}){
    Eigen::Vector3d q=manager.global_data_.getPosition(prefix_time);reactive_stair::Query query;query.frame=map->mp_.frame_id_;query.stamp_s=query_time;query.x_m=q.x();query.y_m=q.y();query.z_m=q.z();query.in_map=map->isInMap(q);
    reactive_stair::NonTerrainVoxel obstacle;obstacle.frame=query.frame;obstacle.source_id="scan_lidar_cloud";obstacle.stamp_s=42.308;obstacle.occupancy=reactive_stair::Occupancy::Free;
    auto verdict=map->reactive_decision_.decide(query,obstacle);
    results<<"{\"case\":"<<id<<",\"kind\":\"freshness\",\"query_sim_s\":"<<query_time<<",\"prefix_time\":"<<prefix_time<<",\"cloud_stamp_s\":"<<obstacle.stamp_s<<",\"cloud_age_s\":"<<query_time-obstacle.stamp_s<<",\"cloud_max_age_s\":"<<map->reactive_parameters_.obstacle_max_age_s<<",\"verdict\":"<<int(verdict)<<",\"scope\":\"Recorded rounded cloud stamp; free obstacle isolates native freshness/support predicate\"}\n";
   }}
   if(id==2){checkPoint("live_collision_planned",endpoint,.73619696);checkPoint("live_collision_measured",fsm.odom_pos_,.73619696);}
   if(id<=1){for(bool old_target:{false,true}){restore();manager.accepted_warm_context_=context(fsm,0);manager.accepted_warm_goal_=goalContext(fsm,0);manager.accepted_warm_traj_id_=saved_local.traj_id_;manager.accepted_warm_map_=map.get();manager.setWarmStartContext(context(fsm,0),goalContext(fsm,0),t);std::vector<Eigen::Vector3d> path;double interval;std::string why;auto q=old_target?endpoint:nominal;bool ok=manager.makeWarmStartSeed(p,v,acc,q,path,interval,why);results<<"{\"case\":"<<id<<",\"kind\":\"warm_seed\",\"counterfactual_binding\":true,\"old_target\":"<<old_target<<",\"accepted\":"<<ok<<",\"reason\":\""<<why<<"\",\"target\":"<<xyz(q)<<",\"nodes\":"<<path.size()<<"}\n";}}
   for(int rep=0;rep<(id==3?0:2);++rep){restore();std::cout<<"CORNER_ROUND case="<<id<<" repetition="<<rep<<std::endl;const auto wall=std::chrono::steady_clock::now();bool ok;{GridMap::RawContributorCacheScope cache(*map);ok=fsm.planFromCurrentTraj();}results<<"{\"case\":"<<id<<",\"kind\":\"round\",\"repetition\":"<<rep<<",\"success\":"<<ok<<",\"wall_ms\":"<<std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-wall).count()<<"}\n";results.flush();}
   restore();
  }
 }
 if(cases!=4)throw std::runtime_error("missing cases");std::cout<<"CORNER_REPLAY_COMPLETE cases="<<cases<<std::endl;rclcpp::shutdown();
}
