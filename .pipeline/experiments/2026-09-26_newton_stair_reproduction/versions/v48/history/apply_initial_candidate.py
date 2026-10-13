"""Apply the single Candidate 2 policy to the verified v47 native fork."""
from pathlib import Path
import shutil
import hashlib
import json

BASE=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
assert not (HERE/'manifest.json').exists(), 'Never regenerate a frozen version'
parent=BASE/'runtime/scan70_feasible_window_v47'
expected=json.loads((BASE/'versions/v47/manifest.json').read_text())['native_source_sha256']
assert all(hashlib.sha256((parent/name).read_bytes()).hexdigest()==digest for name,digest in expected.items())
shutil.copytree(parent/'src',BASE/'runtime/scan71_remaining_curve_v48/src',dirs_exist_ok=True)
NATIVE=BASE/'runtime/scan71_remaining_curve_v48/src/plan_manage'
p=NATIVE/'include/plan_manage/planner_manager.h'
s=p.read_text().replace('    bool EmergencyStop(Eigen::Vector3d stop_pos);','''    bool EmergencyStop(Eigen::Vector3d stop_pos);
    void setWarmStartContext(const std::string &identity, const Eigen::Vector3d &goal,
                             double curve_time = -1.0);
    void invalidateWarmStart();''')
s=s.replace('        bool &optimization_attempted);','''        bool &optimization_attempted, bool allow_warm_start = false,
        bool *used_warm_start = nullptr);
    bool makeWarmStartSeed(const Eigen::Vector3d &start, const Eigen::Vector3d &velocity,
        const Eigen::Vector3d &acceleration, const Eigen::Vector3d &target,
        vector<Eigen::Vector3d> &path, std::string &reason);
    std::string warm_context_, accepted_warm_context_;
    Eigen::Vector3d warm_goal_{Eigen::Vector3d::Zero()}, accepted_warm_goal_{Eigen::Vector3d::Zero()};
    double warm_curve_time_{-1.0};
    int accepted_warm_traj_id_{-1};
    const GridMap *accepted_warm_map_{nullptr};''')
p.write_text(s)
p=NATIVE/'src/planner_manager.cpp';s=p.read_text()
start=s.index('  bool SCANPlannerManager::reboundReplan(')
helper='''  void SCANPlannerManager::invalidateWarmStart()
  {
    accepted_warm_traj_id_ = -1;
    accepted_warm_context_.clear();
    accepted_warm_map_ = nullptr;
  }

  void SCANPlannerManager::setWarmStartContext(const std::string &identity,
      const Eigen::Vector3d &goal, double curve_time)
  {
    if (identity.empty() || !goal.allFinite() ||
        identity != accepted_warm_context_ || !(goal.array() == accepted_warm_goal_.array()).all())
      invalidateWarmStart();
    warm_context_ = identity;
    warm_goal_ = goal;
    warm_curve_time_ = curve_time;
  }

  bool SCANPlannerManager::makeWarmStartSeed(const Eigen::Vector3d &start,
      const Eigen::Vector3d &velocity, const Eigen::Vector3d &acceleration,
      const Eigen::Vector3d &target, vector<Eigen::Vector3d> &path, std::string &reason)
  {
    path.clear();
    auto reject = [&](const char *why) { reason = why; invalidateWarmStart(); return false; };
    if (warm_context_.empty() || accepted_warm_context_ != warm_context_ ||
        accepted_warm_traj_id_ < 1 || accepted_warm_traj_id_ != local_data_.traj_id_ ||
        accepted_warm_map_ != grid_map_.get() ||
        !(accepted_warm_goal_.array() == warm_goal_.array()).all()) return reject("identity_or_owner");
    auto curve = local_data_.position_traj_;
    const auto points = curve.getControlPoint();
    if (points.rows() != 3 || points.cols() < 4 ||
        !reactive_stair::validSplineLayout(points, curve.getKnot(), 3)) return reject("curve_layout");
    const double duration = curve.getTimeSum();
    const double age = (node_->now() - local_data_.start_time_).seconds();
    if (!std::isfinite(duration) || duration <= 0.0 || !std::isfinite(age) || age < 0.0 || age >= duration ||
        !std::isfinite(warm_curve_time_) || warm_curve_time_ < 0.0 || warm_curve_time_ >= duration ||
        warm_curve_time_ > age + 1e-6 || std::abs(local_data_.duration_ - duration) > 1e-6)
      return reject("curve_time");
    auto derivative = curve.getDerivative();
    auto second = derivative.getDerivative();
    if (!reactive_stair::validSplineLayout(derivative.getControlPoint(), derivative.getKnot(), 2) ||
        !reactive_stair::validSplineLayout(second.getControlPoint(), second.getKnot(), 1) ||
        !start.allFinite() || !velocity.allFinite() || !acceleration.allFinite() || !target.allFinite() ||
        (curve.evaluateDeBoorT(warm_curve_time_) - start).norm() > 1e-6 ||
        (derivative.evaluateDeBoorT(warm_curve_time_) - velocity).norm() > 1e-6 ||
        (second.evaluateDeBoorT(warm_curve_time_) - acceleration).norm() > 1e-6)
      return reject("start_pva");

    grid_map_->refreshSensorInputs("warm_seed_check");
    const auto check = reactive_stair::checkFullCubicTrajectory(curve, warm_curve_time_,
        grid_map_->getResolution(), GridMap::collision_heading_lookahead_s,
        [this](const Eigen::Vector3d &p, const Eigen::Vector3d &ahead, const Eigen::Vector3d &v) {
          return grid_map_->collisionTrajectoryYaw(p, ahead, v);
        }, [this](const Eigen::Vector3d &p, double yaw) { return grid_map_->getInflateOccupancy(p, yaw) != 0; });
    if (!check.clear()) return reject("remaining_curve_not_clear");

    // Upstream 348e8a5 remaining-curve sampling/resampling, without its unchecked
    // polynomial extension or linear-Z rewrite. The original endpoint/PVA stay exact.
    const size_t divisions = std::max<size_t>(1, check.samples - 1);
    vector<Eigen::Vector3d> samples;
    samples.reserve(divisions + 1);
    size_t closest = 0;
    double distance = std::numeric_limits<double>::infinity();
    for (size_t i = 0; i <= divisions; ++i) {
      const double t = i == divisions ? duration : warm_curve_time_ +
          (duration - warm_curve_time_) * static_cast<double>(i) / divisions;
      const Eigen::Vector3d sample = curve.evaluateDeBoorT(t);
      const double d = (sample - target).squaredNorm();
      if (d < distance) { distance = d; closest = i; }
      samples.push_back(sample);
    }
    if (closest == 0) return reject("no_remaining_progress");
    path.push_back(start);
    for (size_t i = 1; i <= closest; ++i)
      if ((samples[i] - path.back()).norm() > 1e-9) path.push_back(samples[i]);
    if ((target - path.back()).norm() > 1e-6) {
      if (!grid_map_->collisionFreeSegment(path.back(), target)) return reject("target_connector");
      path.push_back(target);
    } else path.back() = target;
    if (path.size() < 2 || !hasLocalTranslation(start, target)) return reject("seed_progress");
    for (size_t i = 1; i < path.size(); ++i)
      if (!grid_map_->collisionFreeSegment(path[i-1], path[i])) return reject("seed_edge");
    reason = "accepted";
    return true;
  }

'''
s=s[:start]+helper+s[start:]
s=s.replace('#include <thread>','#include <thread>\n#include <limits>')
s=s.replace('''    if (reboundReplanAttempt(start_pt, start_vel, start_acc, local_target_pt,
                            local_target_vel, flag_polyInit, flag_randomPolyTraj, attempted)) return true;''','''    bool used_warm = false;
    if (reboundReplanAttempt(start_pt, start_vel, start_acc, local_target_pt,
        local_target_vel, flag_polyInit, flag_randomPolyTraj, attempted, true, &used_warm)) {
      if (used_warm) RCLCPP_INFO(node_->get_logger(), "V48_WARM_RESULT accepted=1 graph_fallback=0");
      return true;
    }
    if (used_warm) {
      // A warm optimizer/refit rejection is not a failed original graph solve.
      // Retry the complete parent search/recovery chain from the same input PVA.
      invalidateWarmStart();
      continuous_failures_count_ = failures_before;
      RCLCPP_INFO(node_->get_logger(), "V48_WARM_RESULT accepted=0 graph_fallback=1");
      if (reboundReplanAttempt(start_pt, start_vel, start_acc, local_target_pt,
          local_target_vel, flag_polyInit, flag_randomPolyTraj, attempted)) return true;
    }''')
s=s.replace('''                                        bool &optimization_attempted)
  {
    optimization_attempted = false;''','''                                        bool &optimization_attempted, bool allow_warm_start,
                                        bool *used_warm_start)
  {
    optimization_attempted = false;
    if (used_warm_start) *used_warm_start = false;''')
a=s.index('    // A stair seed must come');b=s.index('    // SCAN-Planner 348e8a5',a)
original=s[a:b];original=original.replace('    std::vector<Eigen::Vector3d> seed_path = seed_search->getPath();','    seed_path = seed_search->getPath();')
s=s[:a]+'''    std::vector<Eigen::Vector3d> seed_path;
    std::string warm_reason;
    const auto warm_started = std::chrono::steady_clock::now();
    const bool warm = allow_warm_start && makeWarmStartSeed(start_pt, start_vel, start_acc,
        local_target_pt, seed_path, warm_reason);
    if (allow_warm_start)
      RCLCPP_INFO(node_->get_logger(), "V48_WARM_SEED selected=%d reason=%s nodes=%zu wall_ms=%.3f",
          warm, warm_reason.c_str(), seed_path.size(), std::chrono::duration<double, std::milli>(
          std::chrono::steady_clock::now() - warm_started).count());
    if (used_warm_start) *used_warm_start = warm;
    if (!warm) {
'''+original+'''    }
'''+s[b:]
s=s.replace('''    start_end_derivatives = {start_vel, local_target_vel, start_acc, Eigen::Vector3d::Zero()};''','''    if (warm && point_set.size() > pp_.planning_horizon_ / pp_.ctrl_pt_dist * 3) {
      continuous_failures_count_++;
      return false;
    }
    start_end_derivatives = {start_vel, local_target_vel, start_acc, Eigen::Vector3d::Zero()};''')
s=s.replace('''    updateTrajInfo(pos, node_->now());''','''    updateTrajInfo(pos, node_->now());
    if (!warm_context_.empty() && warm_goal_.allFinite()) {
      accepted_warm_context_ = warm_context_;
      accepted_warm_goal_ = warm_goal_;
      accepted_warm_traj_id_ = local_data_.traj_id_;
      accepted_warm_map_ = grid_map_.get();
    }''',1)
s=s.replace('''  bool SCANPlannerManager::EmergencyStop(Eigen::Vector3d stop_pos)
  {''','''  bool SCANPlannerManager::EmergencyStop(Eigen::Vector3d stop_pos)
  {
    invalidateWarmStart();''')
s=s.replace('''    if (waypoints.empty())
      return false;''','''    invalidateWarmStart();
    if (waypoints.empty())
      return false;''',1)
p.write_text(s)
p=NATIVE/'include/plan_manage/scan_replan_fsm.h';s=p.read_text().replace('int *reference_prefix_budget = nullptr); // front-end','int *reference_prefix_budget = nullptr, double warm_curve_time = -1.0); // front-end');p.write_text(s)
p=NATIVE/'src/scan_replan_fsm.cpp';s=p.read_text().replace('#include <stdexcept>','#include <stdexcept>\n#include <iomanip>\n#include <sstream>')
s=s.replace('feasible_window_.valid = false; // Regenerated geometry', 'planner_manager_->invalidateWarmStart();\n    feasible_window_.valid = false; // Regenerated geometry',1)
s=s.replace('''    if (collision.clear()) return;
    feasible_window_.valid = false;''','''    if (collision.clear()) return;
    planner_manager_->invalidateWarmStart();
    feasible_window_.valid = false;''',1)
s=s.replace('bool SCANReplanFSM::callReboundReplan(bool flag_use_poly_init, bool flag_randomPolyTraj, int *reference_prefix_budget)', 'bool SCANReplanFSM::callReboundReplan(bool flag_use_poly_init, bool flag_randomPolyTraj, int *reference_prefix_budget, double warm_curve_time)')
needle='''    bool plan_success =
        planner_manager_->reboundReplan'''
identity='''    std::ostringstream warm_identity;
    if (navi_mode_ == NAVI_MODE::REFERENCE_PATH && have_p2b_identity_) {
      const auto &id = active_p2b_identity_;
      warm_identity << std::quoted(id.run_id) << ' ' << id.epoch << ' '
          << std::quoted(id.request_id) << ' ' << std::quoted(id.goal_id) << ' '
          << std::quoted(id.route_id) << ' ' << std::quoted(id.command_id) << ' '
          << id.generation << ' ' << std::quoted(id.map_epoch) << ' ' << id.map_revision;
    }
    planner_manager_->setWarmStartContext(warm_identity.str(), end_pt_, warm_curve_time);

'''
assert needle in s;s=s.replace(needle,identity+needle,1)
for flags in ['false, false','true, false','true, true']:
 s=s.replace('callReboundReplan('+flags+', &reference_prefix_budget)', 'callReboundReplan('+flags+', &reference_prefix_budget, t_cur)',1)
s=s.replace('''  bool SCANReplanFSM::callEmergencyStop(Eigen::Vector3d stop_pos)
  {
    feasible_window_.valid = false;''','''  bool SCANReplanFSM::callEmergencyStop(Eigen::Vector3d stop_pos)
  {
    planner_manager_->invalidateWarmStart();
    feasible_window_.valid = false;''')
p.write_text(s)


p=NATIVE/'include/plan_manage/planner_manager.h';s=p.read_text().replace('#include <stdlib.h>','#include <stdlib.h>\n#include <string>');p.write_text(s)
p=NATIVE/'src/planner_manager.cpp';s=p.read_text().replace('    if (!attempted || !bspline_optimizer_rebound_->optimizesHeight()) return false;','    if (!attempted || !bspline_optimizer_rebound_->optimizesHeight()) {\n      invalidateWarmStart();\n      return false;\n    }',1).replace('    RCLCPP_INFO(node_->get_logger(), "fixed_height_recovery_result accepted=%d", accepted);\n    return accepted;','    RCLCPP_INFO(node_->get_logger(), "fixed_height_recovery_result accepted=%d", accepted);\n    if (!accepted) invalidateWarmStart();\n    return accepted;',1)
needle='                                         const Eigen::Vector3d &end_pos, const Eigen::Vector3d &end_vel, const Eigen::Vector3d &end_acc)\n  {\n\n    // generate global reference trajectory'
assert needle in s;s=s.replace(needle,needle.replace('\n\n    // generate','\n    invalidateWarmStart();\n\n    // generate'))
s=s.replace('    for (size_t i = 1; i < path.size(); ++i)\n      if (!grid_map_->collisionFreeSegment(path[i-1], path[i])) return reject("seed_edge");','    // The reused portion is the already checked cubic, not an executed polyline.\n    // Its resampled/refitted guess still undergoes every unchanged final gate.')
p.write_text(s)
p=NATIVE/'src/scan_replan_fsm.cpp';s=p.read_text().replace('    if (!getLocalTarget()) {\n      feasible_window_.valid = false;','    if (!getLocalTarget()) {\n      planner_manager_->invalidateWarmStart();\n      feasible_window_.valid = false;',1);p.write_text(s)
print('Candidate 2 applied to manager/FSM pairs')
