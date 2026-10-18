// Real native map/target/optimizer seams over the original full v237 scan prefix.
#include "v84/recording.h"
#include <plan_manage/scan_replan_fsm.h>
#include <plan_manage/reference_path_utils.h>
#include <bspline_opt/full_trajectory_collision.h>
#include <atomic>

int main(int argc,char **argv) {
  rclcpp::init(argc,argv);
  const fs::path input=std::getenv("REPLAY_INPUT"),output=std::getenv("REPLAY_OUTPUT");
  fs::create_directories(output);
  rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("grid_map.asynchronous_mapping",false)});
  auto node=std::make_shared<rclcpp::Node>("scan_planner_node",options);
  set_clock(*node,1000000000LL);
  scan_planner::SCANReplanFSM fsm; fsm.init(node.get());
  auto map=fsm.planner_manager_->grid_map_;
  map->occ_timer_->cancel();map->vis_timer_->cancel();
  if(map->async_mapping_)throw std::runtime_error("Expected ordered reconstruction");
  auto nav=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"navigation.f32",true));
  auto surface=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"surface.f32",true));
  auto floor=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/"physical_floor.f32",true));
  nav->header.stamp=surface->header.stamp=floor->header.stamp=rclcpp::Time(1000000000LL,RCL_ROS_TIME);
  map->reactiveTomogramCallback(nav);map->reactiveSurfaceGroundCallback(surface);map->reactivePhysicalFloorCallback(floor);
  if(!map->reactiveSurfaceGroundReady())throw std::runtime_error("Original terrain not paired");
  nav_msgs::msg::Path route; route.header.frame_id="world";
  std::ifstream route_file(input/"route.txt");Eigen::Vector3d point;
  while(route_file>>point.x()>>point.y()>>point.z()) {
    geometry_msgs::msg::PoseStamped p;p.header=route.header;
    p.pose.position.x=point.x();p.pose.position.y=point.y();p.pose.position.z=point.z();p.pose.orientation.w=1.;route.poses.push_back(p);
  }
  std::vector<Eigen::Vector3d> waypoints;std::string error;
  if(!scan_planner::prepareReferenceWaypoints(route,fsm.body_height_,fsm.reference_path_min_distance_,waypoints,&error,fsm.reference_path_simplify_tolerance_))throw std::runtime_error(error);
  std::vector<Eigen::Vector3d> tail(waypoints.begin()+1,waypoints.end());
  if(!fsm.planner_manager_->planGlobalTrajWaypoints(waypoints.front(),Eigen::Vector3d::Zero(),Eigen::Vector3d::Zero(),tail,Eigen::Vector3d::Zero(),Eigen::Vector3d::Zero()))throw std::runtime_error("Reference reconstruction failed");
  std::cout<<"REFERENCE_DURATION "<<std::setprecision(17)<<fsm.planner_manager_->global_data_.global_duration_<<std::endl;
  fsm.navi_mode_=scan_planner::SCANReplanFSM::REFERENCE_PATH;fsm.end_pt_=waypoints.back();fsm.route_generation_=1;fsm.have_odom_=true;
  std::ifstream listing(input/"scans.txt");std::vector<RecordedScan> scans;
  int index;int64_t stamp;std::string bf,sf,cf;
  while(listing>>index>>stamp>>bf>>sf>>cf) {
    RecordedScan scan{index,stamp,std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/bf)),std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/sf)),std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/cf,false))};
    scan.body->header.stamp=scan.sensor->header.stamp=scan.cloud->header.stamp=rclcpp::Time(stamp,RCL_ROS_TIME);scans.push_back(std::move(scan));
  }
  std::ofstream csv(output/"frames.csv");csv<<std::setprecision(17)<<"frame,time_s,cloud_s,body_verdict,spline_status,first_collision_s,target_ok,target_ms,goal_search_ms,goal_search_calls,target_x,target_y,target_z,plan_ok,plan_ms,post_spline_status,aged_body_verdict\n";
  std::ifstream frames(input/"frames.txt");int frame;int64_t ns,body_ns,cutoff;size_t applied=0;
  while(frames>>frame>>ns>>body_ns>>cutoff) {
    while(applied<scans.size()&&scans[applied].stamp<=cutoff){apply_scan(*map,*node,scans[applied]);++applied;}
    if(!applied||scans[applied-1].stamp!=cutoff)throw std::runtime_error("Missing prefix cutoff");
    std::ostringstream number;number<<std::setw(4)<<std::setfill('0')<<frame;
    auto body=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/("query_"+number.str()+".txt")));body->header.stamp=rclcpp::Time(body_ns,RCL_ROS_TIME);
    set_clock(*node,ns);map->slidingMapFrameCallback(body);fsm.applyOdometry(body);
    std::ifstream curve_file(input/("curve_"+number.str()+".txt"));double origin;int nc,nk;curve_file>>origin>>nc>>nk;
    Eigen::MatrixXd controls(3,nc);Eigen::VectorXd knots(nk);
    for(int i=0;i<nc;++i)curve_file>>controls(0,i)>>controls(1,i)>>controls(2,i);
    for(int i=0;i<nk;++i)curve_file>>knots(i);
    if(!curve_file)throw std::runtime_error("Bad curve");
    scan_planner::UniformBspline curve(controls,3,knots(4)-knots(3));curve.setKnot(knots);
    const double raw=ns*1e-9-origin;
    const auto check=[&](scan_planner::UniformBspline &c,double start) {
      return reactive_stair::checkFullCubicTrajectory(c,start,map->getResolution(),GridMap::collision_heading_lookahead_s,
        [&](const Eigen::Vector3d&p,const Eigen::Vector3d&a,const Eigen::Vector3d&v){return map->collisionTrajectoryYaw(p,a,v);},
        [&](const Eigen::Vector3d&p,double yaw){return map->getInflateOccupancy(p,yaw)!=0;});
    };
    const auto before=check(curve,raw);const int body_verdict=int(map->liveTraversability(fsm.odom_pos_,map->collisionSegmentYaw(fsm.odom_pos_,fsm.odom_pos_)));
    fsm.start_pt_=curve.evaluateDeBoorT(std::max(0.,std::min(raw,curve.getTimeSum())));
    fsm.start_vel_=curve.getDerivative().evaluateDeBoorT(std::max(0.,std::min(raw,curve.getTimeSum())));
    fsm.start_acc_=curve.getDerivative().getDerivative().evaluateDeBoorT(std::max(0.,std::min(raw,curve.getTimeSum())));
    bool warm_eligible=false, hint_present=false;double projection=0,selected=0,span=0,measured=0;
    std::ifstream state_file(input/("state_"+number.str()+".txt"));
    if(state_file)state_file>>warm_eligible>>hint_present>>projection>>selected>>span>>measured;
    auto &manager=*fsm.planner_manager_;
    manager.invalidateWarmStart();auto &local=manager.local_data_;
    local.position_traj_=curve;local.velocity_traj_=curve.getDerivative();local.acceleration_traj_=local.velocity_traj_.getDerivative();
    local.start_time_=rclcpp::Time(static_cast<int64_t>(std::llround(origin*1e9)),RCL_ROS_TIME);local.duration_=curve.getTimeSum();local.traj_id_=frame+1;
    if(warm_eligible)manager.restoreWarmStartBinding({fsm.warmStartIdentity(),fsm.warmGoalContext(),local.traj_id_,map.get()});
    fsm.feasible_window_.valid=hint_present;
    if(hint_present) {
      auto &hint=fsm.feasible_window_;hint.generation=fsm.route_generation_;hint.map=map.get();hint.goal=fsm.warmGoalContext();
      hint.span=span;hint.projection=projection;hint.measured_projection=measured;hint.growth_projection=measured;hint.stamp=ns*1e-9;
    }
#ifdef V240_CONTRACTS
    if(frame==0 && std::getenv("REPLAY_DRAIN_CONTRACT")) {
      if(applied>=scans.size())throw std::runtime_error("Missing original next scan");
      auto body_pub=node->create_publisher<nav_msgs::msg::Odometry>(map->sliding_map_frame_sub_->get_topic_name(),10);
      auto sensor_pub=node->create_publisher<nav_msgs::msg::Odometry>(map->lidar_pose_sub_->get_topic_name(),10);
      auto cloud_pub=node->create_publisher<sensor_msgs::msg::PointCloud2>(map->cloud_sub_->get_topic_name(),10);
      for(int wait=0;wait<200 && (!body_pub->get_subscription_count()||!sensor_pub->get_subscription_count()||!cloud_pub->get_subscription_count());++wait)
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
      if(!body_pub->get_subscription_count()||!sensor_pub->get_subscription_count()||!cloud_pub->get_subscription_count())throw std::runtime_error("Drain contract DDS discovery failed");
      const auto digest=map_digest(*map);map->startAsyncMapping();const auto revision=map->mapRevision();const auto old_stamp=map->observationStamp();
      sensor_pub->publish(*scans[applied].sensor);cloud_pub->publish(*scans[applied].cloud);
      const auto begin=std::chrono::steady_clock::now();uint64_t worker_revision=0;double worker_stamp=0.;
      while(std::chrono::steady_clock::now()-begin<std::chrono::seconds(2)) {
        const auto elapsed=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-begin).count();set_clock(*node,ns+elapsed);
        auto heartbeat=*body;heartbeat.header.stamp=node->now();body_pub->publish(heartbeat);
        map->refreshSensorInputs("drain_contract",-1,false);
        if(map->mapRevision()!=revision || map->observationStamp()!=old_stamp || map_digest(*map)!=digest)throw std::runtime_error("Non-adopting drain changed held map");
        {
          std::lock_guard<std::mutex> lock(map->async_mapping_->publication_mutex);
          worker_revision=map->async_mapping_->latest->revision;
          worker_stamp=map->async_mapping_->latest->state->reactive_cloud_stamp_s_;
        }
        if(std::abs(worker_stamp-scans[applied].stamp*1e-9)<1e-8)break;
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
      }
      if(!worker_revision || std::abs(worker_stamp-scans[applied].stamp*1e-9)>1e-8)throw std::runtime_error("Queued original scan did not reach mapper");
      set_clock(*node,std::max<int64_t>(node->now().nanoseconds(),cutoff+360000000LL));
      if(map->planningInputsReady())throw std::runtime_error("Queued newer cloud falsely freshened held evidence");
      map->refreshSensorInputs("drain_contract_adopt");
      if(map->mapRevision()<=revision || std::abs(map->observationStamp()-worker_stamp)>1e-8)throw std::runtime_error("Existing default drain did not adopt completed map");
      std::ofstream result(output/"drain_contract.json");result<<std::setprecision(17)<<"{\"passed\":true,\"held_revision\":"<<revision<<",\"worker_revision\":"<<worker_revision<<",\"old_source_stamp\":"<<old_stamp<<",\"new_source_stamp\":"<<worker_stamp<<",\"held_digest_unchanged\":true,\"stale_held_evidence_rejected\":true,\"default_adoption_passed\":true,\"physics_steps\":0}\n";
      map->stopAsyncMapping();rclcpp::shutdown();return 0;
    }
#endif
    const bool live_stairs=std::getenv("REPLAY_LIVE_STAIRS")!=nullptr;
    if(frame==(live_stairs?0:50) && std::getenv("REPLAY_LIVE_WINDOW")) {
      const int64_t replay_end=live_stairs?55050000000LL:114550000000LL;
      struct Event {int64_t clock,stamp;int kind;nav_msgs::msg::Odometry::SharedPtr pose;sensor_msgs::msg::PointCloud2::SharedPtr cloud;};
      std::vector<Event> events;std::ifstream stream(input/"stream.txt");int64_t due,source_stamp;int kind;std::string file;
      while(stream>>due>>kind>>source_stamp>>file) {
        if((kind==0 && source_stamp<=body_ns)||(kind!=0 && source_stamp<=cutoff))continue;
        Event e{due,source_stamp,kind,nullptr,nullptr};
        if(kind==2) {e.cloud=std::make_shared<sensor_msgs::msg::PointCloud2>(read_cloud(input/file,false));e.cloud->header.stamp=rclcpp::Time(source_stamp,RCL_ROS_TIME);}
        else {
          e.pose=std::make_shared<nav_msgs::msg::Odometry>(read_pose(input/file));e.pose->header.stamp=rclcpp::Time(source_stamp,RCL_ROS_TIME);
          if(kind==0) {
            std::ifstream values(input/file);double ignored;for(int k=0;k<7;++k)values>>ignored;
            auto &twist=e.pose->twist.twist;values>>twist.linear.x>>twist.linear.y>>twist.linear.z>>twist.angular.x>>twist.angular.y>>twist.angular.z;
            if(!values)throw std::runtime_error("Missing original live body velocity");
          }
        }
        events.push_back(std::move(e));
      }
      if(events.empty())throw std::runtime_error("No original due input stream");
      auto body_pub=node->create_publisher<nav_msgs::msg::Odometry>(map->sliding_map_frame_sub_->get_topic_name(),rclcpp::QoS(256).reliable());
      auto fsm_pub=std::string(fsm.odom_sub_->get_topic_name())==map->sliding_map_frame_sub_->get_topic_name()?body_pub:
          node->create_publisher<nav_msgs::msg::Odometry>(fsm.odom_sub_->get_topic_name(),rclcpp::QoS(256).reliable());
      auto sensor_pub=node->create_publisher<nav_msgs::msg::Odometry>(map->lidar_pose_sub_->get_topic_name(),rclcpp::QoS(256).reliable());
      auto cloud_pub=node->create_publisher<sensor_msgs::msg::PointCloud2>(map->cloud_sub_->get_topic_name(),rclcpp::QoS(256).reliable());
      for(int wait=0;wait<200 && (!body_pub->get_subscription_count() || !cloud_pub->get_subscription_count() || !sensor_pub->get_subscription_count());++wait)
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
      if(!body_pub->get_subscription_count() || !cloud_pub->get_subscription_count() || !sensor_pub->get_subscription_count())throw std::runtime_error("No original input subscribers");
      const auto initial_digest=map_digest(*map);map->startAsyncMapping();
      if(map_digest(*map)!=initial_digest)throw std::runtime_error("Synchronous-to-asynchronous map handoff changed prefix");
      fsm.exec_state_=scan_planner::SCANReplanFSM::REPLAN_TRAJ;fsm.flag_escape_emergency_=true;fsm.go2_execution_frozen_=false;
      fsm.have_target_=true;fsm.trigger_=true;fsm.have_new_target_=false;
      size_t rounds=0,successful=0,splines=0,emergencies=0;std::ofstream observations(output/"live_events.csv");
      std::ofstream contexts(output/"emergency_context.csv");contexts<<"ros_s,cloud_age_s,body_stamp_s,odom_x,odom_y,odom_z,seed_x,seed_y,seed_z,seed_body_distance,body_verdict,seed_verdict\n";
      std::ofstream coverage(output/"live_splines.csv");coverage<<"publication_s,start_s,duration_s,emergency\n";
      coverage<<std::setprecision(17)<<ns*1e-9<<','<<origin<<','<<curve.getTimeSum()<<",0\n";
      observations<<"kind,ros_s,success_or_emergency\n";
      fsm.direct_io_.spline=[&](const scan_planner_msgs::msg::Bspline &message){
        ++splines;emergencies+=message.emergency_stop;observations<<"spline,"<<std::setprecision(17)<<node->now().seconds()<<','<<message.emergency_stop<<'\n';
        const double trajectory_start=message.start_time.sec+message.start_time.nanosec*1e-9;
        const double trajectory_duration=message.knots.at(message.pos_pts.size())-message.knots.at(message.order);
        coverage<<std::setprecision(17)<<node->now().seconds()<<','<<trajectory_start<<','<<trajectory_duration<<','<<message.emergency_stop<<'\n';
        if(message.emergency_stop) {
          const double yaw=std::atan2(fsm.start_vel_.y(),fsm.start_vel_.x());
          contexts<<std::setprecision(17)<<node->now().seconds()<<','<<node->now().seconds()-map->observationStamp()<<','<<map->reactive_body_stamp_s_<<','
            <<fsm.odom_pos_.x()<<','<<fsm.odom_pos_.y()<<','<<fsm.odom_pos_.z()<<','<<fsm.start_pt_.x()<<','<<fsm.start_pt_.y()<<','<<fsm.start_pt_.z()<<','<<(fsm.start_pt_-fsm.odom_pos_).norm()<<','
            <<int(map->liveTraversability(fsm.odom_pos_,yaw))<<','<<int(map->liveTraversability(fsm.start_pt_,yaw))<<'\n';
        }
      };
      fsm.direct_io_.planning_result=[&](bool success,int64_t when){++rounds;successful+=success;observations<<"round,"<<std::setprecision(17)<<when*1e-9<<','<<success<<'\n';};
      rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(),2);executor.add_node(node);
      const auto begin=std::chrono::steady_clock::now();size_t released=0;std::array<size_t,3> counts{};
      std::thread publisher([&]{
        while(true) {
          const auto elapsed=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-begin).count();
          const auto now=std::min<int64_t>(replay_end,ns+elapsed);set_clock(*node,now);
          while(released<events.size() && events[released].clock<=now) {
            const auto &e=events[released++];++counts[e.kind];
            if(e.kind==0){body_pub->publish(*e.pose);if(fsm_pub!=body_pub)fsm_pub->publish(*e.pose);}
            else if(e.kind==1)sensor_pub->publish(*e.pose);else cloud_pub->publish(*e.cloud);
          }
          if(now>=replay_end)break;
          std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
        executor.cancel();
      });
      executor.spin();publisher.join();observations.close();contexts.close();coverage.close();map->stopAsyncMapping();
      std::ofstream result(output/"live_window.json");
      result<<"{\"rounds\":"<<rounds<<",\"successful\":"<<successful<<",\"splines\":"<<splines<<",\"emergency_messages\":"<<emergencies<<",\"body_messages\":"<<counts[0]<<",\"sensor_poses\":"<<counts[1]<<",\"clouds\":"<<counts[2]<<",\"initial_prefix_scans\":"<<applied<<",\"initial_digest\":\""<<initial_digest<<"\",\"physics_steps\":0}\n";
      rclcpp::shutdown();return 0;
    }
    if(frame==90 && std::getenv("REPLAY_LIVE_TRIGGER")) {
      // Controlled starvation regression: hold the real map while both versions
      // receive fresh body heartbeats. Advance ROS time at real wall speed.
      // This isolates callback compute time; no future scan is restamped/granted.
      auto body_pub=node->create_publisher<nav_msgs::msg::Odometry>(map->sliding_map_frame_sub_->get_topic_name(),10);
      auto fsm_pub=std::string(fsm.odom_sub_->get_topic_name())==map->sliding_map_frame_sub_->get_topic_name()
          ?body_pub:node->create_publisher<nav_msgs::msg::Odometry>(fsm.odom_sub_->get_topic_name(),10);
      for(int wait=0;wait<200 && (!body_pub->get_subscription_count() || !fsm_pub->get_subscription_count());++wait)
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
      if(!body_pub->get_subscription_count() || !fsm_pub->get_subscription_count())throw std::runtime_error("No native heartbeat subscribers");
      bool emergency_message=false;fsm.direct_io_.spline=[&](const scan_planner_msgs::msg::Bspline &message){emergency_message|=message.emergency_stop;};
      fsm.exec_state_=scan_planner::SCANReplanFSM::REPLAN_TRAJ;fsm.flag_escape_emergency_=true;fsm.go2_execution_frozen_=false;
      std::atomic<bool> running{true};const auto begin=std::chrono::steady_clock::now();
      std::thread clock_body([&]{
        while(running.load()) {
          const auto elapsed=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-begin).count();
          set_clock(*node,ns+elapsed);auto message=*body;message.header.stamp=rclcpp::Time(ns+elapsed,RCL_ROS_TIME);
          body_pub->publish(message);if(fsm_pub!=body_pub)fsm_pub->publish(message);
          std::this_thread::sleep_for(std::chrono::milliseconds(5));
        }
      });
      const bool first=fsm.getLocalTarget();std::this_thread::sleep_for(std::chrono::milliseconds(34));
      const bool second=fsm.getLocalTarget();fsm.checkCollisionCallback();
      const bool stopped=fsm.exec_state_==scan_planner::SCANReplanFSM::EMERGENCY_STOP;
      if(stopped)fsm.execFSMCallback();
      running.store(false);clock_body.join();
      const double elapsed=(node->now().nanoseconds()-ns)*1e-9;
      const bool expected=std::string(std::getenv("TRIGGER_EXPECT_STOP"))=="1";
      std::ofstream result(output/"live_trigger.json");
      result<<std::setprecision(17)<<"{\"first_target\":"<<first<<",\"second_target\":"<<second<<",\"emergency_state\":"<<stopped<<",\"emergency_message\":"<<emergency_message<<",\"elapsed_s\":"<<elapsed<<",\"cloud_age_s\":"<<node->now().seconds()-cutoff*1e-9<<",\"expected_stop\":"<<expected<<",\"physics_steps\":0}\n";
      result.close();
      if(stopped!=expected || emergency_message!=expected)throw std::runtime_error("Live-clock trigger regression mismatch");
      rclcpp::shutdown();return 0;
    }
#ifdef V238_CONTRACTS
    if(frame==90) {
      const auto goal=fsm.end_pt_;const auto global_duration=fsm.planner_manager_->global_data_.global_duration_;
      const auto calls=[&]{return map->planning_profile_.values[reactive_stair::PlanningProfile::GoalSearch].calls;};
      auto count=calls();fsm.adjustGlobalTargetIfOccupied(fsm.start_pt_);
      if(calls()!=count+1)throw std::runtime_error("New-route admission lost original goal-neighbor search");
      count=calls();fsm.adjustGlobalTargetIfOccupied(goal,nullptr,nullptr,true);
      if(calls()!=count+1)throw std::runtime_error("No-forward-progress case lost terminal-neighbor recovery");
      set_clock(*node,cutoff+360000000LL);count=calls();const char* reason="none";
      if(fsm.adjustGlobalTargetIfOccupied(fsm.start_pt_,&reason,nullptr,true) || calls()!=count || std::string(reason)!="planning_inputs_not_ready")
        throw std::runtime_error("Stale evidence bypassed readiness or entered expensive geometric search");
      set_clock(*node,ns);
      if(!(goal.array()==fsm.end_pt_.array()).all() || global_duration!=fsm.planner_manager_->global_data_.global_duration_)
        throw std::runtime_error("Requested goal or admitted route was changed");
      std::cout<<"BOUNDARY_CONTRACTS passed=4 frame=90"<<std::endl;
    }
#endif
    const auto profile_before=map->planning_profile_.values;
    const auto begin=std::chrono::steady_clock::now();const bool target=fsm.getLocalTarget();
    const double target_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begin).count();
    const auto target_profile=map->planning_profile_.since(profile_before);
    const auto goal_search=map->planning_profile_.values[reactive_stair::PlanningProfile::GoalSearch];
    const auto old_goal_search=profile_before[reactive_stair::PlanningProfile::GoalSearch];
    bool plan=false;double plan_ms=0.;int post=-1;
    if(target && std::getenv("REPLAY_OPTIMIZE")) {
      auto start=std::chrono::steady_clock::now();
      plan=fsm.callReboundReplan(true,false,nullptr,warm_eligible?raw:-1.0);
      plan_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
      if(plan)post=int(check(fsm.planner_manager_->local_data_.position_traj_,0.).status);
    }
    // Controlled single-variable probe: same map/body/geometry, original 0.35s age gate.
    set_clock(*node,cutoff+360000000LL);
    const int aged=int(map->liveTraversability(fsm.odom_pos_,std::atan2(2.*(fsm.odom_orient_.w()*fsm.odom_orient_.z()+fsm.odom_orient_.x()*fsm.odom_orient_.y()),1.-2.*(std::pow(fsm.odom_orient_.y(),2)+std::pow(fsm.odom_orient_.z(),2)))));
    set_clock(*node,ns);
    csv<<frame<<','<<ns*1e-9<<','<<cutoff*1e-9<<','<<body_verdict<<','<<int(before.status)<<','<<before.first_time_s<<','<<target<<','<<target_ms<<','<<goal_search.wall_ms-old_goal_search.wall_ms<<','<<goal_search.calls-old_goal_search.calls<<','<<fsm.local_target_pt_.x()<<','<<fsm.local_target_pt_.y()<<','<<fsm.local_target_pt_.z()<<','<<plan<<','<<plan_ms<<','<<post<<','<<aged<<'\n';csv.flush();
    std::cout<<"FRAME "<<frame<<" t="<<ns*1e-9<<" prefix="<<applied<<" target="<<target<<" ms="<<target_ms<<" body="<<body_verdict<<" curve="<<int(before.status)<<" profile="<<target_profile<<std::endl;
  }
  rclcpp::shutdown();return 0;
}
