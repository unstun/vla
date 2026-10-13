  if (std::getenv("V48_WARM_CONTRACT")) {
    auto &manager=*fsm.planner_manager_;
    const auto source=manager.local_data_;
    const auto context=manager.warm_context_;
    const auto goal=manager.warm_goal_;
    int checks=0;
    auto require=[&](bool ok,const char *name) {
      if (!ok) throw std::runtime_error(std::string("V48_WARM_FAIL ")+name);
      std::cout << "V48_WARM_CHECK " << name << " PASS" << std::endl; ++checks;
    };
    require(live_ok && attempt_ok && !context.empty(),"source_from_complete_native_acceptance");
    auto curve=source.position_traj_;
    auto velocity=curve.getDerivative(); auto acceleration=velocity.getDerivative();
    const auto p=curve.evaluateDeBoorT(0.0), v=velocity.evaluateDeBoorT(0.0), a=acceleration.evaluateDeBoorT(0.0);
    const auto target=curve.evaluateDeBoorT(source.duration_);
    const auto end_v=velocity.evaluateDeBoorT(source.duration_);
    auto restore=[&]() {
      manager.local_data_=source;
      manager.warm_context_=manager.accepted_warm_context_=context;
      manager.warm_goal_=manager.accepted_warm_goal_=goal;
      manager.accepted_warm_traj_id_=source.traj_id_;
      manager.accepted_warm_map_=map.get();
      manager.warm_curve_time_=0.0;
    };
    vector<Eigen::Vector3d> seed; double interval=0.0; std::string reason;
    auto seed_ok=[&](const Eigen::Vector3d &start,const Eigen::Vector3d &target_point) {
      return manager.makeWarmStartSeed(start,v,a,target_point,seed,interval,reason);
    };
    restore();
    require(seed_ok(p,target),"valid_remaining_curve_selected_against_current_native_map");
    require(seed.size()>=2 && (seed.front()-p).norm()<1e-9 && (seed.back()-target).norm()<1e-9,
        "seed_preserves_exact_endpoint_positions");
    require((fsm.end_pt_.array()==goal.array()).all(),"final_goal_unchanged");
    restore(); manager.setWarmStartContext(context+"changed",goal,0.0);
    require(!seed_ok(p,target),"identity_change_rejects");
    restore(); manager.setWarmStartContext(context,goal+Eigen::Vector3d(0,0,.1),0.0);
    require(!seed_ok(p,target),"goal_change_rejects");
    restore(); manager.accepted_warm_map_=nullptr;
    require(!seed_ok(p,target),"map_instance_change_rejects");
    restore(); manager.local_data_.traj_id_++;
    require(!seed_ok(p,target),"unowned_curve_rejects");
    restore(); manager.warm_curve_time_=-.1;
    require(!seed_ok(p,target),"negative_curve_time_rejects");
    restore(); manager.warm_curve_time_=source.duration_;
    require(!seed_ok(p,target),"expired_curve_time_rejects");
    restore(); manager.local_data_.start_time_=node->now()+rclcpp::Duration::from_seconds(.1);
    require(!seed_ok(p,target),"future_curve_clock_rejects");
    restore(); manager.local_data_.start_time_=node->now()-rclcpp::Duration::from_seconds(source.duration_+.1);
    require(!seed_ok(p,target),"expired_live_curve_rejects");
    restore();
    require(!seed_ok(p+Eigen::Vector3d(.01,0,0),target),"start_position_drift_rejects");
    restore();
    require(!manager.makeWarmStartSeed(p,v+Eigen::Vector3d(.01,0,0),a,target,seed,interval,reason),"start_velocity_drift_rejects");
    restore();
    require(!manager.makeWarmStartSeed(p,v,a+Eigen::Vector3d(.01,0,0),target,seed,interval,reason),"start_acceleration_drift_rejects");
    restore(); const double scan_stamp=map->reactive_cloud_stamp_s_;map->reactive_cloud_stamp_s_=0.0;
    require(!seed_ok(p,target),"stale_scan_rejects"); map->reactive_cloud_stamp_s_=scan_stamp;
    restore(); const auto bounds=map->mp_.map_max_boundary_;map->mp_.map_max_boundary_=p-Eigen::Vector3d::Ones();
    require(!seed_ok(p,target),"new_blocked_or_out_of_map_curve_rejects");map->mp_.map_max_boundary_=bounds;
    restore();
    require(!seed_ok(p,target+Eigen::Vector3d(200,0,0)),"unsafe_target_connector_rejects");
    restore(); manager.EmergencyStop(p);
    require(manager.accepted_warm_traj_id_<0,"emergency_invalidates_source");
    restore(); manager.planGlobalTrajWaypoints(p,v,a,{},end_v,Eigen::Vector3d::Zero());
    require(manager.accepted_warm_traj_id_<0,"route_regeneration_invalidates_source");
    restore(); manager.setWarmStartContext(context+"new_command",goal,0.0);
    require(manager.reboundReplan(p,v,a,target,end_v,false,false),"invalid_reuse_falls_back_to_complete_graph_success");
    restore();
    const int id_before=manager.local_data_.traj_id_;
    require(!manager.reboundReplan(p,v,a,target,Eigen::Vector3d::Constant(std::numeric_limits<double>::quiet_NaN()),false,false),
        "failed_warm_boundary_fit_runs_graph_fallback_then_rejects");
    require(manager.local_data_.traj_id_==id_before,"failed_warm_and_graph_do_not_publish");

    // Identical accepted source, input PVA, target, map and fixed ROS clock.
    // Cold uses the complete original graph/recovery path; warm may safely fall back.
    auto pair=[&](bool warm,int iteration) {
      restore(); if (!warm) manager.setWarmStartContext("",goal,0.0);
      const auto begun=std::chrono::steady_clock::now();
      const bool ok=manager.reboundReplan(p,v,a,target,end_v,false,false);
      const double elapsed=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-begun).count();
      std::cout << "V48_PAIR warm=" << warm << " iteration=" << iteration << " success=" << ok << " wall_ms=" << std::setprecision(12) << elapsed << std::endl;
      require(ok,warm ? "warm_complete_planning_success" : "cold_complete_planning_success");
      auto accepted=manager.local_data_.position_traj_;
      const vector<Eigen::Vector3d> boundary={v,end_v,a,Eigen::Vector3d::Zero()};
      require(reactive_stair::matchesBoundaryPva(accepted,p,target,boundary),"published_start_end_pva_preserved");
      const auto final_check=reactive_stair::checkFullCubicTrajectory(accepted,0.0,map->getResolution(),
          GridMap::collision_heading_lookahead_s,heading_fn,occupied_fn);
      require(final_check.clear() && manager.checkDynamicFeasibility(accepted),"published_whole_curve_and_dynamics_pass");
      require(manager.local_data_.traj_id_>source.traj_id_,"new_native_trajectory_identity");
    };
    for (int i=0;i<3;++i) { pair(false,i); pair(true,i); }
    std::cout << "V48_WARM_PASSED checks=" << checks << std::endl;
  }
