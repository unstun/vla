// Evaluation only: installed PCT plugin/service and cold SCAN FSM, no planner source.
#include "v84/recording.h"
#include "v232/tools/raw_reference.h"
#include <plan_manage/scan_replan_fsm.h>
#include <bspline_opt/full_trajectory_collision.h>
#include <lite3_nav2_plugins/shared_traversability.hpp>
#include <lite3_nav2_interfaces/srv/route_session.hpp>
#include <nav2_core/global_planner.hpp>
#include <pluginlib/class_loader.hpp>
#include <atomic>
#include <cstring>

double seconds(std::chrono::steady_clock::time_point t) {
  return std::chrono::duration<double>(std::chrono::steady_clock::now()-t).count();
}
int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  const fs::path input=std::getenv("CASE_INPUT"),out=std::getenv("PROBE_OUTPUT"),terrain=std::getenv("REPLAY_INPUT");
  fs::create_directories(out);
  std::ofstream metrics(out/"metrics.txt");metrics<<std::setprecision(17);
  const auto began=std::chrono::steady_clock::now();
  rclcpp::NodeOptions options;options.parameter_overrides({rclcpp::Parameter("grid_map.asynchronous_mapping",false),
    rclcpp::Parameter("grid_map.static_solid_path",std::string(std::getenv("RAW_FIELD"))),
    rclcpp::Parameter("grid_map.static_solid_fnv64",std::string(std::getenv("RAW_FNV")))});
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);set_clock(*node,1000000000LL);
  scan_planner::SCANReplanFSM fsm;
  int rounds=0,successes=0,published=0,emergencies=0;
  auto reference_began=began;bool reference_started=false;double first_publish_s=-1.;
  scan_planner_msgs::msg::Bspline publication;
  scan_planner::SCANReplanFSM::DirectIO direct;
  direct.planning_result=[&](bool success,int64_t){++rounds;successes+=success;};
  direct.spline=[&](const scan_planner_msgs::msg::Bspline &message) {
    if(message.emergency_stop)++emergencies;else {++published;publication=message;if(reference_started&&first_publish_s<0.)first_publish_s=seconds(reference_began);}
  };
  fsm.init(node.get(),nullptr,direct);auto map=fsm.nav2Map();
  fsm.exec_timer_->cancel();fsm.safety_timer_->cancel();map->occ_timer_->cancel();map->vis_timer_->cancel();
  for(auto name:{"navigation","surface","physical_floor"}) {
    auto cloud=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(terrain/(std::string(name)+".f32"),true));
    cloud->header.stamp=node->now();
    if(std::string(name)=="navigation")map->reactiveTomogramCallback(cloud);
    else if(std::string(name)=="surface")map->reactiveSurfaceGroundCallback(cloud);
    else map->reactivePhysicalFloorCallback(cloud);
  }
  if(!map->reactiveSurfaceGroundReady()||!map->hasEnvironmentalField())throw std::runtime_error("Terrain/ENV not ready");
  std::ifstream endpoints(input/"endpoints.txt");Eigen::Vector3d start,goal;double start_yaw,goal_yaw;
  if(!(endpoints>>start.x()>>start.y()>>start.z()>>goal.x()>>goal.y()>>goal.z()>>start_yaw>>goal_yaw))throw std::runtime_error("Missing explicit endpoints");
  std::ifstream scans(input/"scans.txt");
  int index;int64_t stamp;std::string bf,sf,cf;unsigned count=0;
  while(scans>>index>>stamp>>bf>>sf>>cf) {
    RecordedScan s{index,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/bf)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sf)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cf,false))};
    s.body->header.stamp=s.sensor->header.stamp=s.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    apply_scan(*map,*node,s);fsm.odometryCallback(s.body);++count;
  }
  fsm.applyDueOdometry();
  std::ifstream saved(std::getenv("SAVED_SPLINE"));int order,n,k;double epoch;
  if(!(saved>>order>>epoch>>n>>k)||n<4||k!=n+order+1)throw std::runtime_error("Invalid saved cubic");
  Eigen::MatrixXd controls(3,n);Eigen::VectorXd knots(k);
  for(int i=0;i<n;++i)for(int d=0;d<3;++d)saved>>controls(d,i);
  for(int i=0;i<k;++i)saved>>knots(i);
  if(!saved||!controls.allFinite()||!knots.allFinite())throw std::runtime_error("Invalid saved values");
  auto curve=fsm.planner_manager_->local_data_.position_traj_;curve.setUniformBspline(controls,order,1.);curve.setKnot(knots);
  auto velocity=curve.getDerivative();
  const auto check=reactive_stair::checkFullCubicTrajectory(curve,0.,map->getResolution(),GridMap::collision_heading_lookahead_s,
    [&](const Eigen::Vector3d &p,const Eigen::Vector3d &q,const Eigen::Vector3d &v){return map->collisionTrajectoryYaw(p,q,v);},
    [&](const Eigen::Vector3d &p,double yaw){return map->getInflateOccupancy(p,yaw)!=0;});
  auto field=std::make_shared<reactive_stair::EnvironmentalField>(std::getenv("ENVIRONMENT_INPUT"),std::getenv("ENVIRONMENT_FNV"));
  for(bool runtime:{false,true}){
    const double lookahead=runtime?GridMap::collision_heading_lookahead_s:.1;
    std::ofstream csv(out/(runtime?"runtime_samples.csv":"replica_samples.csv"));
    csv<<std::setprecision(17)<<"t,x,y,z,yaw,live_verdict,floor_known,edge_margin,native_solid_margin\n";
    for(double t=0.;t<=curve.getTimeSum()+1e-9;t+=.02){
      const auto p=curve.evaluateDeBoorT(t),q=curve.evaluateDeBoorT(std::min(t+lookahead,curve.getTimeSum()));
      const double yaw=map->collisionTrajectoryYaw(p,q,velocity.evaluateDeBoorT(t));
      const auto a=field->assess(p,yaw,map->mapState().mp_.support_gap_mask_.get());
      csv<<t<<','<<p.x()<<','<<p.y()<<','<<p.z()<<','<<yaw<<','<<int(map->liveTraversability(p,yaw))<<','<<a.floor_known<<','<<a.edge_margin<<','<<map->supportState().static_solid_->assess(p,yaw).margin<<'\n';
    }
  }
  if(rounds||published)throw std::runtime_error("Unexpected planning during saved-output audit");
  metrics<<"runtime_lookahead_s="<<GridMap::collision_heading_lookahead_s<<"\nfull_curve_status="<<int(check.status)<<"\nscan_fixtures="<<count<<"\nplanning_calls=0\nphysics_steps=0\n";
  rclcpp::shutdown();return 0;
}
