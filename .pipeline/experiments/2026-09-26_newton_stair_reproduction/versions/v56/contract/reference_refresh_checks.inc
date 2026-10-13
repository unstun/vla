if (std::getenv("V53_REFRESH_CONTRACT")) {
  auto &manager=*fsm.planner_manager_;
  auto curve=manager.local_data_;
  auto old_global=manager.global_data_; const auto old_goal=fsm.end_pt_;
  const auto saved_window=fsm.feasible_window_;
  const auto old_window=accepted_hint;
  const auto old_binding=manager.warmStartBinding();
  const auto old_identity=fsm.active_p2b_identity_;
  const bool old_qualified=fsm.have_requested_goal_pose_;
  const auto old_requested=fsm.requested_goal_pose_;
  const auto old_state=fsm.exec_state_;
  const bool old_trigger=fsm.trigger_, old_target=fsm.have_target_, old_new=fsm.have_new_target_;
  const double old_frontier=fsm.reference_frontier_time_;
  const bool old_neighbor=fsm.reference_neighbor_target_;
  const auto old_neighbor_point=fsm.reference_neighbor_point_;
  const auto old_high=fsm.p2b_route_generation_high_water_;
  auto qualified=std::make_shared<scan_planner_msgs::msg::P2BRoute>(*route);
  qualified->has_goal_pose=true;
  qualified->goal_pose.position.x=old_goal.x(); qualified->goal_pose.position.y=old_goal.y(); qualified->goal_pose.position.z=old_goal.z();
  qualified->goal_pose.orientation.w=1.0;
  auto restore=[&]() {
    manager.local_data_=curve; manager.global_data_=old_global;
    fsm.end_pt_=old_goal; fsm.feasible_window_=old_window;
    fsm.active_p2b_identity_=old_identity;fsm.have_p2b_identity_=true;
    fsm.have_requested_goal_pose_=true;fsm.requested_goal_pose_=qualified->goal_pose;
    fsm.exec_state_=old_state;fsm.trigger_=old_trigger;fsm.have_target_=old_target;fsm.have_new_target_=old_new;
    fsm.reference_frontier_time_=old_frontier;fsm.reference_neighbor_target_=old_neighbor;fsm.reference_neighbor_point_=old_neighbor_point;
    fsm.p2b_route_generation_high_water_=old_high;
    manager.restoreWarmStartBinding({fsm.warmStartIdentity(),fsm.warmGoalContext(),curve.traj_id_,map.get()});
    fsm.feasible_window_.goal=fsm.warmGoalContext();
  };
  int checks=0;
  auto require=[&](bool ok,const char *name) {
    if(!ok)throw std::runtime_error(std::string("V53_REFRESH_FAIL ")+name);
    std::cout<<"V53_REFRESH_CHECK "<<name<<" PASS"<<std::endl; ++checks;
  };
  restore(); require(fsm.canPreserveReferenceBinding(),"qualified_live_binding_eligible");
  const double original_stamp=fsm.feasible_window_.stamp;
  const auto points_before=manager.local_data_.position_traj_.getControlPoint();
  const auto knots_before=manager.local_data_.position_traj_.getKnot();
  fsm.p2bRouteCallback(qualified);
  require(manager.warmStartBinding().trajectory_id==curve.traj_id_,"same_owner_requested_pose_refresh_preserves_binding");
  require(fsm.feasible_window_.valid && fsm.feasible_window_.world_geometry_valid,"window_reprojected_from_world_geometry");
  require(fsm.feasible_window_.stamp==original_stamp,"refresh_does_not_renew_hint_ttl");
  require(manager.local_data_.start_time_==curve.start_time_ && manager.local_data_.traj_id_==curve.traj_id_ &&
      manager.local_data_.position_traj_.getControlPoint()==points_before && manager.local_data_.position_traj_.getKnot()==knots_before,
      "refresh_does_not_restamp_or_replace_accepted_curve");
  require(fsm.requested_goal_pose_==qualified->goal_pose && (fsm.end_pt_.array()==old_goal.array()).all(),"requested_goal_and_reference_endpoint_unchanged");
  const std::vector<std::string> owner_fields={"run","epoch","request","goal","route","command","generation","map_epoch","map_revision"};
  for(const auto &field:owner_fields) {
    restore(); auto changed=std::make_shared<scan_planner_msgs::msg::P2BRoute>(*qualified);
    if(field=="run")changed->run_id+="x";if(field=="epoch")++changed->epoch;if(field=="request")changed->request_id+="x";
    if(field=="goal")changed->goal_id+="x";if(field=="route")changed->route_id+="x";if(field=="command")changed->command_id+="x";
    if(field=="generation")++changed->generation;if(field=="map_epoch")changed->map_epoch+="x";if(field=="map_revision")++changed->map_revision;
    fsm.p2bRouteCallback(changed);require(manager.warmStartBinding().trajectory_id<0,(field+"_change_invalidates").c_str());
  }
  for(int kind=0;kind<5;++kind) {
    restore();auto changed=std::make_shared<scan_planner_msgs::msg::P2BRoute>(*qualified);
    if(kind==0)changed->goal_pose.position.x=std::nextafter(changed->goal_pose.position.x,INFINITY);
    if(kind==1){changed->goal_pose.orientation.w=0.0;changed->goal_pose.orientation.z=1.0;}
    if(kind==2)changed->has_goal_pose=false;
    if(kind==3)changed->goal_pose.orientation.w=2.0;
    if(kind==4)changed->goal_pose.position.z=NAN;
    fsm.p2bRouteCallback(changed);require(manager.warmStartBinding().trajectory_id<0,"changed_or_unqualified_requested_pose_invalidates");
  }
  restore(); const auto bounds=map->mp_.map_max_boundary_;
  map->mp_.map_max_boundary_=Eigen::Vector3d::Constant(-1000.0);
  fsm.p2bRouteCallback(qualified);
  map->mp_.map_max_boundary_=bounds;
  require(manager.warmStartBinding().trajectory_id==curve.traj_id_ && manager.warmStartBinding().context==fsm.warmStartIdentity(),"failed_native_refresh_rolls_back_binding");
  require(manager.global_data_.global_duration_==old_global.global_duration_ &&
      (manager.global_data_.getPosition(0.5).array()==old_global.getPosition(0.5).array()).all() &&
      fsm.feasible_window_.stamp==old_window.stamp && fsm.have_new_target_==old_new && fsm.trigger_==old_trigger,
      "failed_native_refresh_restores_reference_window_and_flags");
  restore();manager.accepted_warm_map_=nullptr;require(!fsm.canPreserveReferenceBinding(),"changed_map_pointer_not_eligible");
  restore();manager.local_data_.start_time_=node->now()-rclcpp::Duration::from_seconds(curve.duration_+.1);
  require(!fsm.canPreserveReferenceBinding(),"expired_curve_not_eligible");
  restore();manager.local_data_.start_time_=node->now()+rclcpp::Duration::from_seconds(.1);
  require(!fsm.canPreserveReferenceBinding(),"future_curve_not_eligible");
  restore();manager.local_data_.traj_id_++;require(!fsm.canPreserveReferenceBinding(),"unowned_curve_not_eligible");
  restore();manager.local_data_.traj_id_=0;manager.local_data_.start_time_=rclcpp::Time(int64_t(0),RCL_SYSTEM_TIME);
  require(!fsm.canPreserveReferenceBinding(),"no_accepted_curve_rejects_before_clock_arithmetic");
  restore();manager.local_data_.start_time_=rclcpp::Time(node->now().nanoseconds(),RCL_SYSTEM_TIME);
  require(!fsm.canPreserveReferenceBinding(),"incompatible_clock_type_rejects_before_subtraction");
  restore();fsm.feasible_window_.endpoint_world=Eigen::Vector3d::Constant(1000.0);fsm.reprojectFeasibleWindow();
  require(!fsm.feasible_window_.valid,"unmappable_window_not_eligible");
  // Return all inherited fixtures to their exact original legacy context.
  restore();fsm.have_requested_goal_pose_=old_qualified;fsm.requested_goal_pose_=old_requested;
  fsm.feasible_window_=saved_window;manager.restoreWarmStartBinding(old_binding);
  std::cout<<"V53_REFRESH_PASSED checks="<<checks<<std::endl;
}
