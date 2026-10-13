// Actual GridMap source callbacks, recorded corner, manager and sequential accepted curves.
#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/full_trajectory_collision.h>
#include <bspline_opt/timed_cubic_initialization.h>
#include <rcl/time.h>
#include <rclcpp/serialization.hpp>
#include <fstream>
#include <cstring>
#include <iostream>
#include <iomanip>
using namespace scan_planner;
template<class T> T decode(const std::vector<char>&b){rclcpp::SerializedMessage s(b.size());auto&r=s.get_rcl_serialized_message();std::memcpy(r.buffer,b.data(),b.size());r.buffer_length=b.size();T m;rclcpp::Serialization<T>().deserialize_message(&s,&m);return m;}
sensor_msgs::msg::PointCloud2 ground(const char *path){std::ifstream f(path,std::ios::binary);sensor_msgs::msg::PointCloud2 m;m.data=std::vector<uint8_t>(std::istreambuf_iterator<char>(f),{});if(m.data.empty())throw std::runtime_error("missing ground");m.header.frame_id="world";m.header.stamp.sec=1;m.height=1;m.width=m.data.size()/16;m.point_step=16;m.row_step=m.data.size();for(int i=0;i<4;++i){sensor_msgs::msg::PointField p;p.name=std::vector<std::string>{"x","y","z","intensity"}[i];p.offset=4*i;p.datatype=p.FLOAT32;p.count=1;m.fields.push_back(p);}return m;}
int main(int argc,char**argv){
 rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");SCANReplanFSM fsm;fsm.init(node.get());fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();auto &manager=*fsm.planner_manager_;auto map=manager.grid_map_;map->occ_timer_->cancel();map->vis_timer_->cancel();
 auto clock=[&](int64_t ns){auto*h=node->get_clock()->get_clock_handle();if(rcl_enable_ros_time_override(h)!=RCL_RET_OK||rcl_set_ros_time_override(h,ns)!=RCL_RET_OK)throw std::runtime_error("clock");};clock(1000000000);
 int checks=0;auto check=[&](bool ok,const char *name){if(!ok)throw std::runtime_error(std::string("V56_NATIVE_FAIL ")+name);std::cout<<"V56_NATIVE_CHECK "<<name<<" PASS"<<std::endl;++checks;};
 auto nav=std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/versions/v36/tests/attempt09/v33_stand/converted_inputs/ground.f32"));
 auto surface=std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32"));
 auto physical=std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/versions/v56/assets/physical_floor.f32"));
 check(!map->physicalFloorReady(),"configured_input_missing_rejects_old_publisher_fallback");
 map->reactiveTomogramCallback(nav);map->reactiveSurfaceGroundCallback(surface);
 check(!map->physicalFloorReady(),"selected_inputs_alone_do_not_satisfy_physical_role");
 map->reactivePhysicalFloorCallback(physical);check(map->physicalFloorReady(),"exact_pinned_source_pair_and_grid_qualified");
 check(map->reactive_physical_floor_.cells.size()>0 && map->reactive_cost_limit_==20.0,"physical_snapshot_retains_cost_and_unchanged_traversal_limit");
 auto malformed=std::make_shared<sensor_msgs::msg::PointCloud2>(*physical);malformed->point_step=12;map->reactivePhysicalFloorCallback(malformed);check(!map->physicalFloorReady(),"malformed_layout_rejected");
 malformed=std::make_shared<sensor_msgs::msg::PointCloud2>(*physical);malformed->header.frame_id="other";map->reactivePhysicalFloorCallback(malformed);check(!map->physicalFloorReady(),"wrong_frame_rejected");
 malformed=std::make_shared<sensor_msgs::msg::PointCloud2>(*physical);malformed->data[16]^=1;map->reactivePhysicalFloorCallback(malformed);check(!map->physicalFloorReady(),"changed_source_content_rejected");
 malformed=std::make_shared<sensor_msgs::msg::PointCloud2>(*physical);malformed->header.stamp.sec=2;map->reactivePhysicalFloorCallback(malformed);check(!map->physicalFloorReady(),"future_physical_snapshot_rejected");
 map->reactivePhysicalFloorCallback(physical);const double origin=map->physical_floor_origin_x_m_;map->physical_floor_origin_x_m_+=.05;map->reactivePhysicalFloorCallback(physical);check(!map->physicalFloorReady(),"mismatched_origin_rejected");map->physical_floor_origin_x_m_=origin;map->reactivePhysicalFloorCallback(physical);
 const double res=map->physical_floor_resolution_m_;map->physical_floor_resolution_m_=.2;map->reactivePhysicalFloorCallback(physical);check(!map->physicalFloorReady(),"mismatched_resolution_rejected");map->physical_floor_resolution_m_=res;map->reactivePhysicalFloorCallback(physical);
 const double maxage=map->reactive_parameters_.terrain_max_age_s;map->reactive_parameters_.terrain_max_age_s=.5;clock(2000000000);check(!map->physicalFloorReady(),"stale_physical_snapshot_rejected");clock(1000000000);map->reactive_parameters_.terrain_max_age_s=maxage;
 const auto surface_id=map->reactive_surface_ground_.source_id;map->reactive_surface_ground_.source_id="changed";check(!map->physicalFloorReady(),"unpaired_selected_source_rejected");map->reactive_surface_ground_.source_id=surface_id;
 const auto nav_id=map->reactive_navigation_ground_.source_id;map->reactive_navigation_ground_.source_id="changed";check(!map->physicalFloorReady(),"unpaired_navigation_source_rejected");map->reactive_navigation_ground_.source_id=nav_id;
 // Reversed source callback order reaches exactly the same augmentation/scoring.
 const auto forward_ground=map->reactive_ground_,forward_score=map->reactive_terrain_;
 auto same=[](const reactive_stair::TerrainSnapshot &a,const reactive_stair::TerrainSnapshot&b){if(a.cells.size()!=b.cells.size())return false;for(const auto &e:a.cells){auto i=b.cells.find(e.first);if(i==b.cells.end()||e.second.size()!=i->second.size())return false;for(size_t n=0;n<e.second.size();++n)if(e.second[n].elevation_m!=i->second[n].elevation_m||e.second[n].support!=i->second[n].support)return false;}return true;};
 map->reactive_physical_floor_={};map->physical_floor_decoded_valid_=false;map->reactive_surface_ground_={};map->reactive_navigation_ground_={};map->reactive_ground_={};
 map->reactivePhysicalFloorCallback(physical);map->reactiveSurfaceGroundCallback(surface);map->reactiveTomogramCallback(nav);
 check(map->physicalFloorReady() && same(map->reactive_ground_,forward_ground) && same(map->reactive_terrain_,forward_score),"callback_order_produces_exact_same_ground_and_scores");
 nav_msgs::msg::Odometry body,sensor,cloud_sensor;sensor_msgs::msg::PointCloud2 cloud;std::ifstream stream("/archive/audits/2026-10-02_v52_corner_43s/attempt05/replay/events.bin",std::ios::binary);
 while(true){uint8_t type;int64_t ns;uint32_t size;if(!stream.read(reinterpret_cast<char*>(&type),1))throw std::runtime_error("missing late marker");stream.read(reinterpret_cast<char*>(&ns),8);stream.read(reinterpret_cast<char*>(&size),4);std::vector<char>b(size);stream.read(b.data(),size);clock(ns);
  if(type==0){body=decode<nav_msgs::msg::Odometry>(b);auto p=std::make_shared<nav_msgs::msg::Odometry>(body);map->slidingMapFrameCallback(p);fsm.odometryCallback(p);}
  else if(type==1){sensor=decode<nav_msgs::msg::Odometry>(b);map->sensorPoseCallback(std::make_shared<nav_msgs::msg::Odometry>(sensor));}
  else if(type==2){cloud=decode<sensor_msgs::msg::PointCloud2>(b);cloud_sensor=sensor;map->cloudCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(cloud));}
  else if(type==3)fsm.p2bRouteCallback(std::make_shared<scan_planner_msgs::msg::P2BRoute>(decode<scan_planner_msgs::msg::P2BRoute>(b)));
  else if(type==4){auto m=decode<scan_planner_msgs::msg::Bspline>(b);Eigen::MatrixXd p(3,m.pos_pts.size());for(size_t i=0;i<m.pos_pts.size();++i)p.col(i)<<m.pos_pts[i].x,m.pos_pts[i].y,m.pos_pts[i].z;Eigen::VectorXd k(m.knots.size());for(size_t i=0;i<m.knots.size();++i)k[i]=m.knots[i];UniformBspline c(p,3,k[4]-k[3]);c.setKnot(k);auto&l=manager.local_data_;l.position_traj_=c;l.velocity_traj_=c.getDerivative();l.acceleration_traj_=l.velocity_traj_.getDerivative();l.duration_=c.getTimeSum();l.start_time_=rclcpp::Time(m.start_time,RCL_ROS_TIME);l.traj_id_=m.traj_id;l.start_pos_=c.evaluateDeBoorT(0);fsm.have_new_target_=false;manager.accepted_warm_context_=fsm.warmStartIdentity();manager.accepted_warm_goal_=fsm.warmGoalContext();manager.accepted_warm_traj_id_=l.traj_id_;manager.accepted_warm_map_=map.get();}
  else if(type==5){uint32_t id;std::memcpy(&id,b.data(),4);if(id==2)break;}
 }
 const Eigen::Vector3d old_endpoint=manager.local_data_.position_traj_.evaluateDeBoorT(manager.local_data_.duration_);
 const double old_expiry=manager.local_data_.start_time_.seconds()+manager.local_data_.duration_;
 check(map->getInflateOccupancy(old_endpoint,.73619696)==0,"recorded_late_start_full_double_cylinder_is_now_supported");
 const Eigen::Vector3d rejected_center(7.45468530655,-3.68681144714,1.883030939);
 reactive_stair::Cell2 cell;reactive_stair::physicalFloorIndex(map->reactive_physical_floor_,rejected_center.x(),rejected_center.y(),cell);
 auto original_selected=map->reactive_surface_ground_;reactive_stair::Cell2 selected_cell{int(std::floor((rejected_center.x()-original_selected.origin_x_m)/original_selected.resolution_m)),int(std::floor((rejected_center.y()-original_selected.origin_y_m)/original_selected.resolution_m))};
 auto nofloor=[&](const reactive_stair::TerrainSnapshot&t){auto i=t.cells.find(selected_cell);if(i==t.cells.end())return true;return reactive_stair::nearestSurface(i->second,1.583030939,.12)<0;};
 check(nofloor(original_selected),"actual_cost_50_central_layer_remains_unselected");
 check(!map->reactiveTerrainReturn(Eigen::Vector3d(rejected_center.x(),rejected_center.y(),1.583030939)),"actual_cost_50_floor_not_used_to_classify_lidar_return");
 const auto history=map->reactive_nonterrain_history_;const auto labels=map->reactive_terrain_hits_;const bool cloud_ready=map->reactive_cloud_ready_;const double cloud_stamp=map->reactive_cloud_stamp_s_;
 {GridMap::RawContributorCacheScope cache(*map);map->getInflateOccupancy(old_endpoint,.73619696);map->reactivePhysicalFloorCallback(physical);check(map->terrain_cell_cache_.empty()&&map->raw_contributor_cache_.empty(),"physical_replacement_clears_borrowed_caches");}
 check(map->reactive_nonterrain_history_==history,"physical_replacement_retains_exact_nonterrain_history");
 check(map->reactive_terrain_hits_==labels && map->reactive_cloud_ready_==cloud_ready && map->reactive_cloud_stamp_s_==cloud_stamp,"physical_replacement_keeps_selected_labels_and_sensor_state");
 std::cout<<"V56_SEQUENCE_INPUT physical_ready="<<map->physicalFloorReady()<<" initial_occ="<<map->getInflateOccupancy(old_endpoint,.73619696)<<" global_duration="<<manager.global_data_.global_duration_<<" goal="<<fsm.end_pt_.transpose()<<" cloud_age="<<node->now().seconds()-map->reactive_cloud_stamp_s_<<std::endl;
 auto occupied=[&](const Eigen::Vector3d&p,double yaw){return map->getInflateOccupancy(p,yaw)!=0;};auto heading=[&](const Eigen::Vector3d&p,const Eigen::Vector3d&ahead,const Eigen::Vector3d&v){return map->collisionTrajectoryYaw(p,ahead,v);};
 const auto requested_goal=fsm.requested_goal_pose_;const auto reference_goal=fsm.end_pt_;
 for(int i=0;i<2;++i){
  const double age=std::clamp((node->now()-manager.local_data_.start_time_).seconds(),0.0,manager.local_data_.duration_);
  const auto p=manager.local_data_.position_traj_.evaluateDeBoorT(age),v=manager.local_data_.velocity_traj_.evaluateDeBoorT(age),a=manager.local_data_.acceleration_traj_.evaluateDeBoorT(age);
  auto begin=std::chrono::steady_clock::now();bool ok;{GridMap::RawContributorCacheScope cache(*map);ok=fsm.planFromCurrentTraj();}
  std::cout<<std::setprecision(17)<<"V56_SEQUENTIAL round="<<i<<" success="<<ok<<" wall_ms="<<std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count()<<" endpoint="<<manager.local_data_.position_traj_.evaluateDeBoorT(manager.local_data_.duration_).transpose()<<" expiry="<<manager.local_data_.start_time_.seconds()+manager.local_data_.duration_<<std::endl;
  check(ok,"actual_complete_native_corner_round_succeeds");
  auto accepted=manager.local_data_.position_traj_;const std::vector<Eigen::Vector3d> boundary={v,fsm.local_target_vel_,a,Eigen::Vector3d::Zero()};
  check(reactive_stair::matchesBoundaryPva(accepted,p,fsm.local_target_pt_,boundary),"published_pva_matches_fixed_start_and_native_target");
  check(reactive_stair::checkFullCubicTrajectory(accepted,0.0,map->getResolution(),GridMap::collision_heading_lookahead_s,heading,occupied).clear()&&manager.checkDynamicFeasibility(accepted),"published_whole_curve_and_dynamics_pass");
  check(fsm.requested_goal_pose_==requested_goal&&(fsm.end_pt_.array()==reference_goal.array()).all(),"final_goal_and_requested_yaw_unchanged");
  check(manager.local_data_.start_time_.seconds()+manager.local_data_.duration_>old_expiry && (accepted.evaluateDeBoorT(manager.local_data_.duration_)-old_endpoint).norm()>map->getResolution(),"new_spatial_endpoint_and_expiry_reserve_extend_beyond_expired_source");
  if(i==0)clock(node->now().nanoseconds()+40000000LL);
 }
 std::cout<<"V56_NATIVE_PHYSICAL_PASSED checks="<<checks<<std::endl;rclcpp::shutdown();
}
