from pathlib import Path
BASE=Path(__file__).resolve().parents[2]
V=BASE/'versions/v122'

def replace(s,old,new,count=1):
 assert s.count(old)==count,(old[:90],s.count(old),count)
 return s.replace(old,new)

p=V/'src/plan_env/include/plan_env/grid_map.h';s=p.read_text()
s=replace(s,'  double observationStamp() const { return mapState().reactive_cloud_stamp_s_; }','''  double observationStamp() const { return mapState().reactive_cloud_stamp_s_; }
  // V122_DIAGNOSTIC_BEGIN
  bool observationReady() const { return mapState().reactive_cloud_ready_; }
  double observationMaxAge() const { return supportState().reactive_parameters_.obstacle_max_age_s; }
  // V122_DIAGNOSTIC_END''');p.write_text(s)
p=V/'src/plan_manage/include/plan_manage/planner_manager.h';s=p.read_text()
s=replace(s,'#include <stdlib.h>','#include <stdlib.h>\n// V122_DIAGNOSTIC_BEGIN\n#include <plan_manage/planning_outcome.h>\n// V122_DIAGNOSTIC_END')
s=replace(s,'    /* main planning interface */','''    // V122_DIAGNOSTIC_BEGIN
    PlanningOutcome planning_outcome_;
    bool planningRejected(FailureStage stage, const char *detail);
    void finishPlanningOutcome(bool success);
    // V122_DIAGNOSTIC_END
    /* main planning interface */''');p.write_text(s)
p=V/'src/plan_manage/src/planner_manager.cpp';s=p.read_text()
anchor='  bool SCANPlannerManager::reboundReplan(Eigen::Vector3d start_pt'
pos=s.index(anchor)
s=s[:pos]+'''  // V122_DIAGNOSTIC_BEGIN
  bool SCANPlannerManager::planningRejected(FailureStage stage, const char *detail) {
    if (planning_outcome_.active()) {
      const auto observation = grid_map_ && node_
        ? observationState(grid_map_->observationReady(), node_->now().seconds(),
            grid_map_->observationStamp(), grid_map_->observationMaxAge())
        : ObservationState::Missing;
      planning_outcome_.rejected(stage, detail, observation, grid_map_ ? grid_map_->mapRevision() : 0);
    }
    return false;
  }
  void SCANPlannerManager::finishPlanningOutcome(bool success) {
    planning_outcome_.finish(success);
    RCLCPP_INFO(node_->get_logger(), "V122_PLANNING_OUTCOME %s", planning_outcome_.json().c_str());
  }
  // V122_DIAGNOSTIC_END

'''+s[pos:]
# Wrap only already-rejecting returns. No predicate or success path changes.
for log,stage,detail in [
 ('V62_RETRY_EPOCH invalid_clock_or_future','Epoch','retry_origin'),
 ('Close to goal','SeedGeometry','no_local_translation'),
 ('reactive_stair_seed_search_failed','SeedSearch','astar_rejected'),
 ('reactive_stair_seed_endpoint_mismatch','SeedGeometry','endpoint_mismatch'),
 ('reactive_stair_seed_edge_blocked','SeedGeometry','edge_rejected'),
 ('final_spline_rejected status=','FinalCollision','curve_collision'),
 ('final_spline_time_invalid','Epoch','published_curve_expired')]:
 start=s.index(log);end=s.index('return false;',start)
 s=s[:end]+f'return planningRejected(FailureStage::{stage}, "{detail}"); // V122_REJECT'+s[end+len('return false;'):]
old='''      // visualization_->displayOptimalList( ctrl_pts, vis_id );
      continuous_failures_count_++;
      return false;'''
s=replace(s,old,old.replace('return false;','return planningRejected(FailureStage::Optimizer, "optimizer_rejected"); // V122_REJECT'))
old='''      continuous_failures_count_++;
      return false;
    }

    t_refine ='''
s=replace(s,old,old.replace('return false;','return planningRejected(FailureStage::Dynamics, "refine_boundary_or_limits"); // V122_REJECT'))
old='''        !std::isfinite(pp_.max_vel_) || pp_.max_vel_ <= 0.0) return false;'''
s=replace(s,old,old.replace('return false;','return planningRejected(FailureStage::InvalidInput, "seed_parameters"); // V122_REJECT'))
old='''    if (search->AstarSearch(grid_map_->getResolution(), start, goal, true, tolerance) != ASTAR_RET::SUCCESS) return {};'''
s=replace(s,old,'''    if (search->AstarSearch(grid_map_->getResolution(), start, goal, true, tolerance) != ASTAR_RET::SUCCESS) {
      // V122_DIAGNOSTIC_BEGIN
      planningRejected(FailureStage::Target, "goal_neighborhood_search");
      // V122_DIAGNOSTIC_END
      return {};
    }''')
p.write_text(s)
p=V/'src/plan_manage/src/scan_replan_fsm.cpp';s=p.read_text()
for call in ['const bool success = planFromCurrentTraj();','bool success = callReboundReplan(true, flag_random_poly_init);']:
 assert s.count(call)==1,(call,s.count(call))
 s=s.replace(call,'''// V122_DIAGNOSTIC_BEGIN
    planner_manager_->planning_outcome_.begin();
    // V122_DIAGNOSTIC_END
    '''+call+'''
    // V122_DIAGNOSTIC_BEGIN
    planner_manager_->finishPlanningOutcome(success);
    // V122_DIAGNOSTIC_END''')
old='''    if (!getLocalTarget()) {
      planner_manager_->invalidateWarmStart();
      feasible_window_.valid = false;
      return false;
    }'''
s=replace(s,old,old.replace('return false;','return planner_manager_->planningRejected(FailureStage::Target, "local_target_selection"); // V122_REJECT'))
p.write_text(s)
print('Instrumented step 1; decision predicates and successful trajectories unchanged')
