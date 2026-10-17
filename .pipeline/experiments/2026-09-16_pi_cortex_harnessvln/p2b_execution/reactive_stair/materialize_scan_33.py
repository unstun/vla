"""Preserve reference goals and try bounded, fully checked stopping prefixes."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_32"
OUT = HERE.parent / "builds/scan_33"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((BASE / "build_result.json").read_text())["passed"]:
        raise ValueError("scan32 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    source = OUT / "src/plan_manage/src/scan_replan_fsm.cpp"
    header = OUT / "src/plan_manage/include/plan_manage/scan_replan_fsm.h"
    once(header, "    void getLocalTarget();", "    bool getLocalTarget();")
    once(header,
         "    bool callReboundReplan(bool flag_use_poly_init, bool flag_randomPolyTraj);",
         "    bool callReboundReplan(bool flag_use_poly_init, bool flag_randomPolyTraj, int *reference_prefix_budget = nullptr);")
    once(header,
         "    Eigen::Vector3d local_target_pt_, local_target_vel_;                     // local target state",
         """    Eigen::Vector3d local_target_pt_, local_target_vel_;                     // local target state
    // Reference proposals do not change the admitted route or its goal.
    double reference_frontier_time_{-1.0};
    double local_target_time_{-1.0}, local_projection_time_{-1.0};""")

    before = source.read_text()
    start = before.index("  bool SCANReplanFSM::adjustGlobalTargetIfOccupied()")
    end = before.index("  void SCANReplanFSM::p2bRouteCallback", start)
    method = before[start:end]
    updated = method.replace("    const double duration = global_data.global_duration_;", """    const double duration = global_data.global_duration_;
    const bool reference = navi_mode_ == NAVI_MODE::REFERENCE_PATH;
    reference_frontier_time_ = -1.0;
    if (reference && (!map || !std::isfinite(duration) || duration < 1e-3 ||
                      duration / 0.05 >= std::numeric_limits<int>::max()))
      return false;""")
    updated = updated.replace("    const int final_occ = map->getInflateOccupancy(final_pt, estimateYawFromSegment(final_prev, final_pt));", """    if (reference && (!final_pt.allFinite() || !final_prev.allFinite())) return false;
    const double final_yaw = estimateYawFromSegment(final_prev, final_pt);
    if (reference && !std::isfinite(final_yaw)) return false;
    const int final_occ = map->getInflateOccupancy(final_pt, final_yaw);""")
    updated = updated.replace("    if (final_occ <= 0)\n      return true;", """    if (reference ? final_occ == 0 : final_occ <= 0) {
      if (reference) reference_frontier_time_ = duration;
      return true;
    }""")
    updated = updated.replace("      if (map->getInflateOccupancy(pt, estimateYawFromSegment(prev_pt, pt)) == 0)", """      if (reference && (!pt.allFinite() || !prev_pt.allFinite())) return false;
      const double yaw = estimateYawFromSegment(prev_pt, pt);
      if (reference && !std::isfinite(yaw)) return false;
      if (map->getInflateOccupancy(pt, yaw) == 0)""")
    updated = updated.replace("        const Eigen::Vector3d raw_end = end_pt_;", """        if (reference) {
          reference_frontier_time_ = t;
          RCLCPP_INFO(node_->get_logger(),
                      "reference_frontier time=%.12f full_duration=%.12f xyz=[%.12f,%.12f,%.12f]",
                      t, duration, pt.x(), pt.y(), pt.z());
          return true;
        }
        const Eigen::Vector3d raw_end = end_pt_;""")
    once(source, method, updated)

    before = source.read_text()
    start = before.index("  bool SCANReplanFSM::planFromCurrentTraj()")
    end = before.index("  void SCANReplanFSM::setStartStateFromOdomOrCurrentTraj()", start)
    method = before[start:end]
    ref_end = method.index("    start_pt_ = odom_pos_;")
    ref = method[:ref_end]
    ref = ref.replace("      bool success = callReboundReplan(false, false);", """      // One shared prefix budget across all original initialization modes.
      int reference_prefix_budget = 3;
      bool success = callReboundReplan(false, false, &reference_prefix_budget);""")
    ref = ref.replace("callReboundReplan(true, false)", "callReboundReplan(true, false, &reference_prefix_budget)")
    ref = ref.replace("callReboundReplan(true, true)", "callReboundReplan(true, true, &reference_prefix_budget)")
    once(source, method, ref + method[ref_end:])

    once(source,
         "  bool SCANReplanFSM::callReboundReplan(bool flag_use_poly_init, bool flag_randomPolyTraj)",
         "  bool SCANReplanFSM::callReboundReplan(bool flag_use_poly_init, bool flag_randomPolyTraj, int *reference_prefix_budget)")
    once(source, "    getLocalTarget();", "    if (!getLocalTarget()) return false;")
    once(source, """    have_new_target_ = false;

    cout << "final_plan_success=" << plan_success << endl;""", """    have_new_target_ = false;

    const bool reference = navi_mode_ == NAVI_MODE::REFERENCE_PATH;
    int per_round_budget = 3;
    int &remaining = reference_prefix_budget ? *reference_prefix_budget : per_round_budget;
    double candidate_t = local_target_time_;
    while (!plan_success && reference && remaining > 0) {
      --remaining;  // Count considered proposals, including rejected endpoints.
      candidate_t = local_projection_time_ + 0.5 * (candidate_t - local_projection_time_);
      if (!std::isfinite(candidate_t) || candidate_t <= local_projection_time_ ||
          candidate_t > reference_frontier_time_) continue;
      const Eigen::Vector3d candidate = planner_manager_->global_data_.getPosition(candidate_t);
      if (!candidate.allFinite() || (candidate - start_pt_).norm() < 0.2) continue;
      const double yaw = estimateYawFromSegment(odom_pos_, candidate);
      if (!std::isfinite(yaw) || planner_manager_->grid_map_->getInflateOccupancy(candidate, yaw) != 0) continue;

      local_target_pt_ = candidate;
      local_target_vel_.setZero();
      local_target_time_ = candidate_t;
      RCLCPP_INFO(node_->get_logger(),
                  "reference_prefix_proposal time=%.12f projected=%.12f remaining=%d xyz=[%.12f,%.12f,%.12f]",
                  candidate_t, local_projection_time_, remaining, candidate.x(), candidate.y(), candidate.z());
      // Every shorter target goes through the complete native planner, with
      // the same start PVA and zero terminal velocity. No seed-only fallback.
      plan_success = planner_manager_->reboundReplan(start_pt_, start_vel_, start_acc_,
          local_target_pt_, local_target_vel_, true, flag_randomPolyTraj);
    }
    if (plan_success && reference) {
      // This marks the accepted planning window end, not measured execution.
      planner_manager_->global_data_.last_progress_time_ = local_target_time_;
      RCLCPP_INFO(node_->get_logger(), "reference_window_committed time=%.12f full_duration=%.12f",
                  local_target_time_, planner_manager_->global_data_.global_duration_);
    }

    cout << "final_plan_success=" << plan_success << endl;""")

    once(source, "  void SCANReplanFSM::getLocalTarget()", "  bool SCANReplanFSM::getLocalTarget()")
    before = source.read_text()
    start = before.index("  bool SCANReplanFSM::getLocalTarget()")
    end = before.index("\n} // namespace scan_planner", start)
    method = before[start:end]
    updated = method.replace("    const double duration = planner_manager_->global_data_.global_duration_;", """    const bool reference = navi_mode_ == NAVI_MODE::REFERENCE_PATH;
    local_target_time_ = local_projection_time_ = -1.0;
    if (reference) {
      local_target_pt_.setZero();
      local_target_vel_.setZero();
      if (!start_pt_.allFinite() || !start_vel_.allFinite() || !start_acc_.allFinite() ||
          !odom_pos_.allFinite() || !end_pt_.allFinite() ||
          !std::isfinite(max_vel) || max_vel <= 0.0 || !std::isfinite(max_acc) ||
          !std::isfinite(planning_horizon_) || planning_horizon_ <= 0.0 ||
          !adjustGlobalTargetIfOccupied()) return false;
    }
    const double duration = reference ? reference_frontier_time_ : planner_manager_->global_data_.global_duration_;
    const Eigen::Vector3d selection_end = reference ? planner_manager_->global_data_.getPosition(duration) : end_pt_;""")
    updated = updated.replace("      Eigen::Vector3d pos_t = planner_manager_->global_data_.getPosition(t);", """      Eigen::Vector3d pos_t = planner_manager_->global_data_.getPosition(t);
      if (reference && !pos_t.allFinite()) return false;""")
    updated = updated.replace("    local_target_pt_ = end_pt_;", "    local_target_pt_ = selection_end;")
    updated = updated.replace("    t_step = std::max(t_step, 0.01);", """    t_step = std::max(t_step, 0.01);
    if (reference && !std::isfinite(t_step)) return false;""")
    updated = updated.replace("    planner_manager_->global_data_.last_progress_time_ = target_found ? target_t : duration;", """    if (!reference)
      planner_manager_->global_data_.last_progress_time_ = target_found ? target_t : duration;""")
    updated = updated.replace("      return planner_manager_->grid_map_->getInflateOccupancy(pt, estimateYawFromSegment(odom_pos_, pt));", """      if (reference && !pt.allFinite()) return 1;
      const double yaw = estimateYawFromSegment(odom_pos_, pt);
      if (reference && !std::isfinite(yaw)) return 1;
      return planner_manager_->grid_map_->getInflateOccupancy(pt, yaw);""")
    updated = updated.replace('                             "Local target is in collision and no nearby free target was found");', '''                             "Local target is in collision and no nearby free target was found");
        if (reference) return false;''')
    updated = updated.replace("    if ((end_pt_ - local_target_pt_).norm() < braking_distance)", "    if ((selection_end - local_target_pt_).norm() < braking_distance)")
    tail = """    }
  }
"""
    assert updated.endswith(tail)
    updated = updated[:-len(tail)] + """    }
    if (reference && (!local_target_pt_.allFinite() || !local_target_vel_.allFinite() ||
                      !std::isfinite(target_t) || target_t <= t_proj || target_t > duration ||
                      (local_target_pt_ - start_pt_).norm() < 0.2)) return false;
    local_target_time_ = target_t;
    local_projection_time_ = t_proj;
    return true;
  }
"""
    once(source, method, updated)
    (OUT / "reference_prefix_manifest.json").write_text(json.dumps({
        "base": BASE.name, "base_manifest_sha256": sha(BASE / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (source, header)},
        "generator_sha256": sha(Path(__file__)),
        "change": "REFERENCE_PATH keeps the admitted goal and full duration, refreshes a point-free frontier, commits actual adjusted local time only after complete manager success, and considers at most three halved-time stopping prefixes per outer round after primary failure.",
        "preserved": "Original primary initialization modes and order, non-reference behavior, route identity, manager 0.2 m separation, complete search/optimizer/PVA/dynamics/collision acceptance, map/Unknown/height rules and original solver limits.",
        "boundary": "Policy experiment. The frontier is not a reachability proof. Zero terminal velocity is a planning condition, not evidence of physical stopping. Count bounds are not hard realtime bounds. Predicted rolling start state and measured arrival require separate validation."
    }, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
