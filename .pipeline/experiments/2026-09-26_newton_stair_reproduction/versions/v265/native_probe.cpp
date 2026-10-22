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
  auto field=std::make_shared<reactive_stair::EnvironmentalField>(std::getenv("ENVIRONMENT_INPUT"),std::getenv("ENVIRONMENT_FNV"));
  metrics<<"scan_initialization_s="<<seconds(began)<<'\n';
  if(std::getenv("SCREEN_POSES")) {
    std::ifstream poses(std::getenv("SCREEN_POSES"));std::ofstream csv(out/"screen.csv");
    csv<<std::setprecision(17)<<"id,x,y,z,yaw,static_verdict,floor_known,edge_margin,atlas_solid_margin,exact_solid_margin\n";
    std::string id;Eigen::Vector3d p;double yaw;
    while(poses>>id>>p.x()>>p.y()>>p.z()>>yaw) {
      const auto a=field->assess(p,yaw,map->mapState().mp_.support_gap_mask_.get());csv<<id<<','<<p.x()<<','<<p.y()<<','<<p.z()<<','<<yaw<<','
        <<int(map->staticTraversability(p,yaw))<<','<<a.floor_known<<','<<a.edge_margin<<','<<a.solid_margin<<','<<map->supportState().static_solid_->assess(p,yaw).margin<<'\n';
    }
    rclcpp::shutdown();return 0;
  }
  Eigen::Vector3d a,b;double yaw,goal_yaw=0.;std::ifstream endpoints(input/"endpoints.txt");
  endpoints>>a.x()>>a.y()>>a.z()>>b.x()>>b.y()>>b.z()>>yaw;
  if(!endpoints)throw std::runtime_error("Missing case endpoints");
  const bool explicit_goal=bool(endpoints>>goal_yaw);
  // Preserve legacy requests with unspecified heading through RouteSession's
  // existing inference contract. The v262 benchmark independently requires
  // eight endpoint values and an explicit goal yaw in every frozen case.
  geometry_msgs::msg::PoseStamped start,goal;start.header.frame_id=goal.header.frame_id="world";
  start.pose.position.x=a.x();start.pose.position.y=a.y();start.pose.position.z=a.z();
  start.pose.orientation.z=std::sin(yaw/2);start.pose.orientation.w=std::cos(yaw/2);
  goal.pose.position.x=b.x();goal.pose.position.y=b.y();goal.pose.position.z=b.z();goal.pose.orientation.z=std::sin(goal_yaw/2);goal.pose.orientation.w=std::cos(goal_yaw/2);
  metrics<<"requested_start_static_verdict="<<int(map->staticTraversability(a,yaw))
    <<"\nrequested_start_solid_margin="<<map->supportState().static_solid_->assess(a,yaw).margin
    <<"\nrequested_goal_yaw_explicit="<<explicit_goal<<'\n';
  if(explicit_goal)metrics<<"requested_goal_static_verdict="<<int(map->staticTraversability(b,goal_yaw))
    <<"\nrequested_goal_solid_margin="<<map->supportState().static_solid_->assess(b,goal_yaw).margin<<'\n';
  std::atomic<unsigned> requests{0},rejected{0};
  using Service=lite3_nav2_interfaces::srv::CheckTraversability;
  auto service=node->create_service<Service>("/scan/check_traversability",
    [&](const std::shared_ptr<Service::Request> request,std::shared_ptr<Service::Response> reply) {
      if(request->mode!=Service::Request::STATIC_ONLY) {
        // This stage deliberately precedes the paired local fixture. Native
        // optional feedback remains unavailable and cannot replace static review.
        reply->ready=false;reply->message="native_snapshot_unavailable";return;
      }
      reply->ready=true;reply->map_revision=map->mapRevision();const auto n=++requests;unsigned bad=0;
      std::ofstream csv(out/("static_request_"+std::to_string(n)+".csv"));
      csv<<std::setprecision(17)<<"x,y,z,yaw,verdict\n";
      for(const auto &pose:request->poses) {
        const double y=lite3_nav2::planarYaw(pose);
        const auto v=map->staticTraversability({pose.position.x,pose.position.y,pose.position.z},y);
        reply->verdicts.push_back(uint8_t(v));bad+=v!=reactive_stair::Verdict::Free;
        csv<<pose.position.x<<','<<pose.position.y<<','<<pose.position.z<<','<<y<<','<<int(v)<<'\n';
      }
      rejected+=bad;std::cout<<"STATIC_REQUEST number="<<n<<" samples="<<request->poses.size()<<" rejected="<<bad<<std::endl;
    });
  rclcpp::NodeOptions po;po.use_global_arguments(false);
  auto parent=std::make_shared<rclcpp_lifecycle::LifecycleNode>("case_pct",po);
  parent->declare_parameter("PCT.map_bundle",std::string(std::getenv("PCT_INPUT")));
  const bool legacy_control=std::getenv("LEGACY_CONTROL")!=nullptr;
  parent->declare_parameter("PCT.reference_height",legacy_control?.35:.3);
  parent->declare_parameter("PCT.shared_traversability",true);
  parent->declare_parameter("PCT.environmental_path",std::string(std::getenv("ENVIRONMENT_INPUT")));
  parent->declare_parameter("PCT.environmental_fnv64",std::string(std::getenv("ENVIRONMENT_FNV")));
  parent->declare_parameter("PCT.static_support_path",std::string(std::getenv("STATIC_SUPPORT_INPUT")));
  parent->declare_parameter("PCT.static_support_fnv64",std::string(std::getenv("STATIC_SUPPORT_FNV")));
  parent->declare_parameter("PCT.static_solid_path",std::string(std::getenv("RAW_FIELD")));
  parent->declare_parameter("PCT.static_solid_fnv64",std::string(std::getenv("RAW_FNV")));
  pluginlib::ClassLoader<nav2_core::GlobalPlanner> loader("nav2_core","nav2_core::GlobalPlanner");
  metrics<<"pct_plugin_library="<<loader.getClassLibraryPath("lite3_nav2/PCTPlanner")<<'\n';
  const auto pct_setup=std::chrono::steady_clock::now();
  auto planner=loader.createSharedInstance("lite3_nav2/PCTPlanner");planner->configure(parent,"PCT",nullptr,nullptr);planner->activate();
  metrics<<"pct_initialization_s="<<seconds(pct_setup)<<"\ninitialization_s="<<seconds(began)<<'\n';
  rclcpp::executors::SingleThreadedExecutor executor;executor.add_node(node);executor.add_node(parent->get_node_base_interface());
  std::thread worker([&]{executor.spin();});
  // Native mission contract: infer the terminal tangent through RouteSession.
  auto client_node=std::make_shared<rclcpp::Node>("case_session_client",po);
  if(!legacy_control) {
  using Session=lite3_nav2_interfaces::srv::RouteSession;
  auto client=client_node->create_client<Session>("/lite3_nav2/route_session");
  if(!client->wait_for_service(std::chrono::seconds(3)))throw std::runtime_error("No route-session service");
  auto request=std::make_shared<Session::Request>();request->operation=Session::Request::BEGIN;
  request->session_id="fresh_case";request->goal=goal;request->infer_heading=!explicit_goal;
  auto future=client->async_send_request(request);
  if(rclcpp::spin_until_future_complete(client_node,future)!=rclcpp::FutureReturnCode::SUCCESS || !future.get()->accepted)
    throw std::runtime_error("Route-session refused");
  }
  nav_msgs::msg::Path route;bool admitted=false;std::string error;
  auto t=std::chrono::steady_clock::now();
  try {route=planner->createPlan(start,goal);admitted=true;}catch(const std::exception&e){error=e.what();}
  metrics<<"global_s="<<seconds(t)<<"\nglobal_admitted="<<admitted<<"\nglobal_error="<<error
    <<"\nstatic_requests="<<requests<<"\nstatic_rejected_samples="<<rejected<<'\n';
  executor.cancel();worker.join();planner->deactivate();planner->cleanup();planner.reset();parent.reset();
  if(!admitted){metrics<<"scan_evaluated=0\nscan_published=0\n";rclcpp::shutdown();return 0;}
  std::ofstream path(out/"route.csv");path<<std::setprecision(17)<<"x,y,z,yaw\n";
  for(const auto&p:route.poses)path<<p.pose.position.x<<','<<p.pose.position.y<<','<<p.pose.position.z<<','<<lite3_nav2::planarYaw(p.pose)<<'\n';
  if(std::getenv("GLOBAL_ONLY")){rclcpp::shutdown();return 0;}
  void *raw=makePointField("/task/environment_score_v224/fixtures/building/environment03.env","4316416882194453309",false);
  std::ofstream margins(out/"route_margins.csv");margins<<std::setprecision(17)<<"x,y,z,yaw,floor_known,edge_margin,atlas_solid_margin,raw_edge_margin,legacy_raw_solid_margin,native_solid_margin\n";
  for(const auto&p:lite3_nav2::sampleReference(route,start.pose)) {
    const double y=lite3_nav2::planarYaw(p);Eigen::Vector3d q(p.position.x,p.position.y,p.position.z);
    const auto v=field->assess(q,y,map->mapState().mp_.support_gap_mask_.get());double exact[4];pointAssessment(raw,q.x(),q.y(),q.z(),y,exact);
    margins<<q.x()<<','<<q.y()<<','<<q.z()<<','<<y<<','<<v.floor_known<<','<<v.edge_margin<<','<<v.solid_margin<<','<<exact[0]<<','<<exact[1]<<','<<map->supportState().static_solid_->assess(q,y).margin<<'\n';
  }
  freePointField(raw);
  // Fresh paired sensor evidence for this case only; no history/warm trajectory.
  t=std::chrono::steady_clock::now();std::ifstream scans(input/"scans.txt");
  int index;int64_t stamp;std::string bf,sf,cf;unsigned count=0;
  std::vector<Eigen::Vector3d> observed_solid;
  while(scans>>index>>stamp>>bf>>sf>>cf) {
    RecordedScan s{index,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/bf)),
      std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sf)),
      std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cf,false))};
    s.body->header.stamp=s.sensor->header.stamp=s.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);
    apply_scan(*map,*node,s);fsm.odometryCallback(s.body);++count;
    const auto &sp=s.sensor->pose.pose;
    const Eigen::Vector3d origin(sp.position.x,sp.position.y,sp.position.z);
    const Eigen::Quaterniond rotation(sp.orientation.w,sp.orientation.x,sp.orientation.y,sp.orientation.z);
    const auto &parameters=map->mapState().mp_;
    for(size_t k=0;k<s.cloud->data.size();k+=12) {
      float coordinates[3];std::memcpy(coordinates,s.cloud->data.data()+k,12);
      const auto p=(rotation*Eigen::Vector3d(coordinates[0],coordinates[1],coordinates[2])+origin).eval();
      const auto delta=(p-origin).eval();
      if(!p.allFinite()||delta.norm()>parameters.max_ray_length_||
          (delta.cwiseAbs().array()>parameters.local_update_range_.array()).any()||!map->isInMap(p))continue;
      if(!map->reactiveTerrainReturn(p))observed_solid.push_back(p);
    }
  }
  fsm.applyDueOdometry();
  metrics<<"scan_fixture_count="<<count<<"\nfixture_apply_s="<<seconds(t)<<"\nscan_evaluated=1\n"
    <<"inputs_ready="<<map->planningInputsReady()<<"\nbody_age_s="<<map->queryNow().seconds()-map->reactive_body_stamp_s_
    <<"\ncloud_age_s="<<map->queryNow().seconds()-map->observationStamp()
    <<"\nobserved_nonterrain_returns="<<observed_solid.size()<<'\n';
  const double actual_yaw=map->measuredBodyYaw();
  metrics<<"start_static_verdict="<<int(map->staticTraversability(fsm.odom_pos_,actual_yaw))
    <<"\nstart_live_verdict="<<int(map->liveTraversability(fsm.odom_pos_,actual_yaw))
    <<"\ngoal_live_verdict="<<int(map->liveTraversability(b,lite3_nav2::planarYaw(route.poses.back().pose)))<<'\n';
  auto profile=map->planning_profile_.values;t=std::chrono::steady_clock::now();
  reference_began=t;reference_started=true;
  fsm.setReferencePath(std::make_shared<nav_msgs::msg::Path>(route));
  metrics<<"reference_admission_s="<<seconds(t)<<"\nreference_have_target="<<fsm.have_target_
    <<"\nreference_profile="<<map->planning_profile_.since(profile)<<'\n';
  const auto gs=map->planning_profile_.values[reactive_stair::PlanningProfile::GoalSearch];
  const auto oldgs=profile[reactive_stair::PlanningProfile::GoalSearch];
  metrics<<"reference_goal_search_calls="<<gs.calls-oldgs.calls<<"\nreference_goal_search_ms="<<gs.wall_ms-oldgs.wall_ms<<'\n';
  profile=map->planning_profile_.values;t=std::chrono::steady_clock::now();
  // Stop at the first genuine planning round. No success-seeking outer retry.
  for(int step=0;step<4 && !rounds;++step)fsm.execFSMCallback();
  metrics<<"scan_first_round_s="<<seconds(t)<<"\nscan_rounds="<<rounds<<"\nscan_successes="<<successes
    <<"\nscan_published="<<published<<"\nscan_emergency="<<emergencies<<"\nscan_first_publish_s="<<first_publish_s
    <<"\nscan_profile="<<map->planning_profile_.since(profile)<<'\n';
  if(published) {
    std::ofstream spline(out/"spline.txt");spline<<std::setprecision(17)<<publication.order<<' '<<rclcpp::Time(publication.start_time).seconds()<<' '<<publication.pos_pts.size()<<' '<<publication.knots.size()<<'\n';
    for(const auto&p:publication.pos_pts)spline<<p.x<<' '<<p.y<<' '<<p.z<<'\n';
    for(const auto k:publication.knots)spline<<k<<'\n';
    auto curve=fsm.planner_manager_->local_data_.position_traj_;
    const auto check=reactive_stair::checkFullCubicTrajectory(curve,0.,map->getResolution(),GridMap::collision_heading_lookahead_s,
      [&](const Eigen::Vector3d&p,const Eigen::Vector3d&q,const Eigen::Vector3d&v){return map->collisionTrajectoryYaw(p,q,v);},
      [&](const Eigen::Vector3d&p,double y){return map->getInflateOccupancy(p,y)!=0;});
    metrics<<"published_independent_status="<<int(check.status)<<"\npublished_duration_s="<<curve.getTimeSum()<<'\n';
    std::ofstream local(out/"local_samples.csv");local<<std::setprecision(17)<<"t,x,y,z,yaw,live_verdict,floor_known,edge_margin,atlas_solid_margin,observed_point_margin,centers_observed,centers_unknown,centers_outside,witness_x,witness_y,witness_z,witness_side,native_solid_margin\n";
    auto v=curve.getDerivative();
    for(double s=0.;s<=curve.getTimeSum()+1e-9;s+=.02) {
      const auto p=curve.evaluateDeBoorT(s),next=curve.evaluateDeBoorT(std::min(s+.1,curve.getTimeSum()));
      const double y=map->collisionTrajectoryYaw(p,next,v.evaluateDeBoorT(s));const auto e=field->assess(p,y,map->mapState().mp_.support_gap_mask_.get());
      double observed=.15,witness_side=0.;Eigen::Vector3d witness=Eigen::Vector3d::Zero();unsigned known=0,unknown=0,outside=0;
      for(double side:{-1.,1.}) {
        const Eigen::Vector3d center=p+side*.18*Eigen::Vector3d(std::cos(y),std::sin(y),0.);
        if(!map->isInMap(center))++outside;else if(map->isUnknown(center))++unknown;else ++known;
        for(const auto&point:observed_solid) {
          const double radial=std::hypot(point.x()-center.x(),point.y()-center.y())-.35;
          const double vertical=std::abs(point.z()-center.z()+.10)-.45;
          const double d=std::hypot(std::max(radial,0.),std::max(vertical,0.))+std::min(std::max(radial,vertical),0.);
          if(d<observed){observed=d;witness=point;witness_side=side;}
        }
      }
      local<<s<<','<<p.x()<<','<<p.y()<<','<<p.z()<<','<<y<<','<<int(map->liveTraversability(p,y))<<','<<e.floor_known<<','<<e.edge_margin<<','<<e.solid_margin<<',';
      if(!observed_solid.empty())local<<observed;
      local<<','<<known<<','<<unknown<<','<<outside<<','<<witness.x()<<','<<witness.y()<<','<<witness.z()<<','<<witness_side<<','<<map->supportState().static_solid_->assess(p,y).margin<<'\n';
    }
  }
  // Negative fixture control: original source ages remain decisive.
  const auto epoch=node->now().nanoseconds();set_clock(*node,epoch+360000000LL);
  metrics<<"stale_inputs_ready="<<map->planningInputsReady()<<"\nstale_start_verdict="<<int(map->liveTraversability(fsm.odom_pos_,actual_yaw))<<'\n';
  set_clock(*node,epoch);metrics<<"total_s="<<seconds(began)<<'\n';
  rclcpp::shutdown();return 0;
}
