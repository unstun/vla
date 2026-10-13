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
int main(int argc,char**argv) {
 rclcpp::init(argc,argv);auto node=std::make_shared<rclcpp::Node>("scan_planner_node");SCANReplanFSM fsm;fsm.init(node.get());fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();auto &manager=*fsm.planner_manager_;auto map=manager.grid_map_;map->occ_timer_->cancel();map->vis_timer_->cancel();
 auto clock=[&](int64_t ns){auto*h=node->get_clock()->get_clock_handle();if(rcl_enable_ros_time_override(h)!=RCL_RET_OK||rcl_set_ros_time_override(h,ns)!=RCL_RET_OK)throw std::runtime_error("clock");};clock(1000000000);
 map->reactiveTomogramCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/versions/v36/tests/attempt09/v33_stand/converted_inputs/ground.f32")));
 map->reactiveSurfaceGroundCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(ground("/archive/audits/2026-09-27_dense_static_sampling/raw_ground.f32")));
 std::ifstream stream("/attempt/replay/events.bin",std::ios::binary);std::ofstream results("/attempt/tail_pairs.jsonl");int cases=0;
 while(true){uint8_t type;int64_t ns;uint32_t size;if(!stream.read(reinterpret_cast<char*>(&type),1))break;stream.read(reinterpret_cast<char*>(&ns),8);stream.read(reinterpret_cast<char*>(&size),4);std::vector<char> bytes(size);stream.read(bytes.data(),size);if(!stream)throw std::runtime_error("truncated replay");clock(ns);
  if(type==0){auto m=std::make_shared<nav_msgs::msg::Odometry>(decode<nav_msgs::msg::Odometry>(bytes));map->slidingMapFrameCallback(m);fsm.odometryCallback(m);}
  else if(type==1)map->sensorPoseCallback(std::make_shared<nav_msgs::msg::Odometry>(decode<nav_msgs::msg::Odometry>(bytes)));
  else if(type==2)map->cloudCallback(std::make_shared<sensor_msgs::msg::PointCloud2>(decode<sensor_msgs::msg::PointCloud2>(bytes)));
  else if(type==3)fsm.p2bRouteCallback(std::make_shared<scan_planner_msgs::msg::P2BRoute>(decode<scan_planner_msgs::msg::P2BRoute>(bytes)));
  else if(type==4){auto m=decode<scan_planner_msgs::msg::Bspline>(bytes);Eigen::MatrixXd p(3,m.pos_pts.size());for(size_t i=0;i<m.pos_pts.size();++i)p.col(i)<<m.pos_pts[i].x,m.pos_pts[i].y,m.pos_pts[i].z;Eigen::VectorXd k(m.knots.size());for(size_t i=0;i<m.knots.size();++i)k[i]=m.knots[i];if(!reactive_stair::validSplineLayout(p,k,3))throw std::runtime_error("archived curve invalid");UniformBspline c(p,3,k[4]-k[3]);c.setKnot(k);auto &l=manager.local_data_;l.position_traj_=c;l.velocity_traj_=c.getDerivative();l.acceleration_traj_=l.velocity_traj_.getDerivative();l.duration_=c.getTimeSum();l.start_time_=rclcpp::Time(m.start_time,RCL_ROS_TIME);l.traj_id_=m.traj_id;l.start_pos_=c.evaluateDeBoorT(0);fsm.have_new_target_=false;
   if(!m.emergency_stop && owner(m)==owner(fsm.active_p2b_identity_)){manager.accepted_warm_context_=owner(m);manager.accepted_warm_goal_=fsm.end_pt_;manager.accepted_warm_traj_id_=l.traj_id_;manager.accepted_warm_map_=map.get();}else manager.invalidateWarmStart();
  }else if(type==5){uint32_t id;std::memcpy(&id,bytes.data(),4);++cases;
   const auto saved_local=manager.local_data_;const auto saved_global=manager.global_data_;const auto saved_window=fsm.feasible_window_;const auto goal=fsm.end_pt_;const auto saved_context=manager.accepted_warm_context_;const auto saved_warm_goal=manager.accepted_warm_goal_;const auto saved_id=manager.accepted_warm_traj_id_;const auto saved_map=manager.accepted_warm_map_;
   auto restore=[&](){manager.local_data_=saved_local;manager.global_data_=saved_global;fsm.feasible_window_=saved_window;fsm.end_pt_=goal;fsm.have_new_target_=false;manager.accepted_warm_context_=saved_context;manager.accepted_warm_goal_=saved_warm_goal;manager.accepted_warm_traj_id_=saved_id;manager.accepted_warm_map_=saved_map;};
   Eigen::MatrixXd baseline_points;Eigen::VectorXd baseline_knots;bool baseline_ok=false;
   for(int rep=0;rep<3;++rep)for(bool optimized:{false,true}){restore();auto search=manager.bspline_optimizer_rebound_->a_star_;search->goal_region_precheck_enabled=optimized;const auto rejected=search->goal_region_rejections;const auto before=map->planning_profile_.values;const auto wall=std::chrono::steady_clock::now();const auto cpu=reactive_stair::PlanningProfile::cpuMs();bool ok;
    {GridMap::RawContributorCacheScope cache(*map);ok=fsm.planFromCurrentTraj();}
    const double elapsed=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-wall).count(),cpu_elapsed=reactive_stair::PlanningProfile::cpuMs()-cpu;
    auto curve=manager.local_data_.position_traj_;auto points=curve.getControlPoint();auto knots=curve.getKnot();bool same=true;
    if(!optimized){baseline_ok=ok;baseline_points=points;baseline_knots=knots;}
    else same=ok==baseline_ok && points.rows()==baseline_points.rows() && points.cols()==baseline_points.cols() && knots.size()==baseline_knots.size() && (points.array()==baseline_points.array()).all() && (knots.array()==baseline_knots.array()).all();
    if(!same)throw std::runtime_error("paired full-round geometry differs");
    if((fsm.end_pt_.array()!=goal.array()).any())throw std::runtime_error("final goal changed");
    results<<std::setprecision(15)<<"{\"case\":"<<id<<",\"simulation_s\":"<<ns*1e-9<<",\"repetition\":"<<rep<<",\"optimized\":"<<optimized<<",\"success\":"<<ok<<",\"same_geometry\":"<<same<<",\"wall_ms\":"<<elapsed<<",\"cpu_ms\":"<<cpu_elapsed<<",\"bounds_rejections\":"<<search->goal_region_rejections-rejected<<",\"profile\":"<<map->planning_profile_.since(before)<<"}\n";results.flush();
   }restore();manager.bspline_optimizer_rebound_->a_star_->goal_region_precheck_enabled=true;
  }
 }
 if(cases!=3)throw std::runtime_error("missing tail cases");std::cout<<"V50_TAIL_REPLAY_PASSED cases="<<cases<<std::endl;rclcpp::shutdown();
}
