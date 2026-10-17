"""First-replan geometry/solver observer; extra map queries only after failure."""
import argparse
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
P2B = ROOT / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
sys.path.insert(0, str(P2B / "reactive_stair"))
from materialize_scan_20 import once, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, default=1)
    parser.add_argument("--base", default="scan_25")
    args = parser.parse_args()
    if not args.base.replace("_", "").isalnum():
        raise ValueError("invalid source build name")
    base = P2B / "builds" / args.base
    name = args.base.replace("_", "") + "_optimizer_trace" + (f"_v{args.attempt}" if args.attempt > 1 else "")
    out = P2B / "builds" / name
    if out.exists():
        raise FileExistsError(out)
    expected = json.loads((base / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(base / "src").as_posix(): sha(p)
              for p in (base / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((base / "build_result.json").read_text())["passed"]:
        raise ValueError("parent source/build identity gate failed")
    shutil.copytree(base / "src", out / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    helper = out / "src/plan_env/include/plan_env/optimizer_trace.h"
    shutil.copy2(HERE / helper.name, helper)
    manager = out / "src/plan_manage/src/planner_manager.cpp"
    optimizer = out / "src/bspline_opt/src/bspline_optimizer.cpp"
    search = out / "src/path_searching/src/dyn_a_star.cpp"
    for p in (manager, optimizer, search):
        p.write_bytes(b'#include <plan_env/optimizer_trace.h>\n' + p.read_bytes())
    once(manager, "    static int count = 0;", "    reactive_stair::OptimizerTraceScope optimizer_trace_scope;\n    static int count = 0;")
    once(manager, "    Eigen::MatrixXd ctrl_pts;\n", '''    reactive_stair::optimizerTrace("OPT_TRACE boundary ts=", ts,
        " start=", reactive_stair::tracePoint(start_pt), " velocity=", reactive_stair::tracePoint(start_vel),
        " acceleration=", reactive_stair::tracePoint(start_acc), " goal=", reactive_stair::tracePoint(local_target_pt),
        " goal_velocity=", reactive_stair::tracePoint(local_target_vel));
    reactive_stair::tracePoints("seed", seed_path);
    reactive_stair::tracePoints("sampled", point_set);
    Eigen::MatrixXd ctrl_pts;
''')
    once(manager, "    UniformBspline::parameterizeToBspline(ts, point_set, start_end_derivatives, ctrl_pts);", '''    UniformBspline::parameterizeToBspline(ts, point_set, start_end_derivatives, ctrl_pts);
    const Eigen::MatrixXd trace_initial_control = reactive_stair::optimizerTraceState().active ? ctrl_pts : Eigen::MatrixXd();
    reactive_stair::traceMatrix("initial_control", ctrl_pts);''')
    once(manager, "    if (!flag_step_1_success)\n    {", '''    if (!flag_step_1_success)
    {
      if (reactive_stair::optimizerTraceState().active) {
        // Original optimization has already failed. These read-only queries
        // compare the fitted and optimized curves under this same map/time;
        // their results never alter acceptance or trigger a fallback.
        reactive_stair::traceMatrix("optimized_control", ctrl_pts);
        for (size_t i = 1; i < point_set.size(); ++i) {
          int sample = -1;
          if (!grid_map_->collisionFreeSegment(point_set[i - 1], point_set[i], &sample)) {
            reactive_stair::optimizerTrace("OPT_TRACE sampled_edge_blocked edge=", i, " sample=", sample,
                " from=", reactive_stair::tracePoint(point_set[i - 1]), " to=", reactive_stair::tracePoint(point_set[i]));
            break;
          }
          if (i + 1 == point_set.size()) reactive_stair::optimizerTrace("OPT_TRACE sampled_edges_clear");
        }
        const auto observe_curve = [&](const char* label, const Eigen::MatrixXd& controls) {
          UniformBspline curve(controls, 3, ts);
          const auto check = reactive_stair::checkFullCubicTrajectory(
              curve, 0.0, grid_map_->getResolution(), GridMap::collision_heading_lookahead_s,
              [this](const Eigen::Vector3d& p, const Eigen::Vector3d& ahead, const Eigen::Vector3d& v) {
                return grid_map_->collisionTrajectoryYaw(p, ahead, v);
              }, [this](const Eigen::Vector3d& p, double yaw) { return grid_map_->getInflateOccupancy(p, yaw) != 0; });
          reactive_stair::optimizerTrace("OPT_TRACE curve=", label, " status=", static_cast<int>(check.status),
              " first_t=", check.first_time_s, " duration=", check.duration_s, " samples=", check.samples);
          if (check.status != reactive_stair::TrajectoryCheckStatus::Clear &&
              check.status != reactive_stair::TrajectoryCheckStatus::Collision) return;
          UniformBspline velocity = curve.getDerivative(), acceleration = velocity.getDerivative();
          curve.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);
          double diagnostic_ratio = 0.0;
          const bool diagnostic_feasible = curve.checkFeasibility(diagnostic_ratio, false);
          reactive_stair::optimizerTrace("OPT_TRACE derivative_bounds label=", label,
              " max_velocity_component=", velocity.getControlPoint().cwiseAbs().maxCoeff(),
              " max_acceleration_component=", acceleration.getControlPoint().cwiseAbs().maxCoeff(),
              " native_convex_feasible=", diagnostic_feasible, " native_time_ratio=", diagnostic_ratio);
          const auto p0 = curve.evaluateDeBoorT(0.0), v0 = velocity.evaluateDeBoorT(0.0), a0 = acceleration.evaluateDeBoorT(0.0);
          const auto end = curve.evaluateDeBoorT(check.duration_s), end_v = velocity.evaluateDeBoorT(check.duration_s), end_a = acceleration.evaluateDeBoorT(check.duration_s);
          const auto ahead = curve.evaluateDeBoorT(std::min(GridMap::collision_heading_lookahead_s, check.duration_s));
          reactive_stair::optimizerTrace("OPT_TRACE curve_boundary label=", label,
              " p0=", reactive_stair::tracePoint(p0), " v0=", reactive_stair::tracePoint(v0), " a0=", reactive_stair::tracePoint(a0),
              " end=", reactive_stair::tracePoint(end), " end_v=", reactive_stair::tracePoint(end_v), " end_a=", reactive_stair::tracePoint(end_a),
              " ahead=", reactive_stair::tracePoint(ahead), " yaw0=", grid_map_->collisionTrajectoryYaw(p0, ahead, v0),
              " p0_error=", (p0 - start_pt).norm(), " v0_error=", (v0 - start_vel).norm(), " a0_error=", (a0 - start_acc).norm(),
              " end_error=", (end - local_target_pt).norm(), " end_v_error=", (end_v - local_target_vel).norm(), " end_a_error=", end_a.norm());
          if (check.status == reactive_stair::TrajectoryCheckStatus::Collision) {
            const auto p = curve.evaluateDeBoorT(check.first_time_s);
            const auto next = curve.evaluateDeBoorT(std::min(check.first_time_s + GridMap::collision_heading_lookahead_s, check.duration_s));
            const double yaw = grid_map_->collisionTrajectoryYaw(p, next, velocity.evaluateDeBoorT(check.first_time_s));
            RCLCPP_WARN(node_->get_logger(), "OPT_TRACE_DIAGNOSTIC curve=%s t=%.12f", label, check.first_time_s);
            grid_map_->logInitialSplineCollision(p, yaw);
          }
        };
        observe_curve("initial_fitted", trace_initial_control);
        observe_curve("post_optimized", ctrl_pts);
      }''')
    first_call = "\n      ASTAR_RET ret = a_star_->AstarSearch(grid_map_->getResolution(), in, out);"
    once(optimizer, first_call, '''
      reactive_stair::optimizerTrace("OPT_TRACE astar_call stage=init first_init=", flag_first_init,
          " segment=", i, " in_id=", segment_ids[i].first, " out_id=", segment_ids[i].second,
          " in=", reactive_stair::tracePoint(in), " out=", reactive_stair::tracePoint(out));
''' + first_call + '''
      reactive_stair::optimizerTrace("OPT_TRACE astar_return stage=init search=", reactive_stair::optimizerTraceState().search_calls,
          " status=", static_cast<int>(ret), " path_size=", ret == ASTAR_RET::SUCCESS ? a_star_->getPath().size() : 0);''')
    second_call = "\n        ASTAR_RET ret = a_star_->AstarSearch(grid_map_->getResolution(), in, out);"
    # Match the remaining differently indented call, not the already modified one.
    once(optimizer, second_call, '''
        reactive_stair::optimizerTrace("OPT_TRACE astar_call stage=rebound segment=", i,
            " in_id=", segment_ids[i].first, " out_id=", segment_ids[i].second,
            " in=", reactive_stair::tracePoint(in), " out=", reactive_stair::tracePoint(out));
''' + second_call + '''
        reactive_stair::optimizerTrace("OPT_TRACE astar_return stage=rebound search=", reactive_stair::optimizerTraceState().search_calls,
            " status=", static_cast<int>(ret), " path_size=", ret == ASTAR_RET::SUCCESS ? a_star_->getPath().size() : 0);''')
    once(optimizer, "      double total_time_ms = std::chrono::duration<double, std::milli>(t2 - t0).count();", '''      double total_time_ms = std::chrono::duration<double, std::milli>(t2 - t0).count();
      reactive_stair::optimizerTrace("OPT_TRACE solver result=", result, " iterations=", iter_num_,
          " force_stop=", static_cast<int>(force_stop_type_), " restarts=", restart_nums, " rebounds=", rebound_times,
          " cost=", final_cost, " ts=", bspline_interval_);''')
    once(optimizer, '            //cout << "hit_obs, t=" << t << " P=" << traj.evaluateDeBoorT(t).transpose() << endl;', '''            reactive_stair::optimizerTrace("OPT_TRACE optimized_collision t=", t,
                " p=", reactive_stair::tracePoint(pos), " ahead=", reactive_stair::tracePoint(pos_next), " yaw=", spline_yaw);
            reactive_stair::traceMatrix("collision_control", cps_.points);''')
    once(optimizer, '                          "First three control points are in obstacles; t=%f", t);', '''                          "First three control points are in obstacles; t=%f", t);
              reactive_stair::optimizerTrace("OPT_TRACE optimizer_exit reason=initial_curve_collision t=", t);''')
    once(optimizer, "    return success;\n  }\n\n  bool BsplineOptimizer::refine_optimize()", '''    reactive_stair::optimizerTrace("OPT_TRACE optimizer_exit success=", success,
        " collision=", flag_occ, " forced=", flag_force_return, " force_stop=", static_cast<int>(force_stop_type_),
        " restarts=", restart_nums, " rebounds=", rebound_times);
    return success;
  }

  bool BsplineOptimizer::refine_optimize()''')
    once(search, "    const auto time_1 = std::chrono::steady_clock::now();", '''    const auto time_1 = std::chrono::steady_clock::now();
    if (reactive_stair::optimizerTraceState().active) ++reactive_stair::optimizerTraceState().search_calls;
    reactive_stair::optimizerTrace("OPT_TRACE search_begin id=", reactive_stair::optimizerTraceState().search_calls,
        " exact=", exact_endpoint, " step=", step_size,
        " start=", reactive_stair::tracePoint(start_pt), " end=", reactive_stair::tracePoint(end_pt));''')
    once(search, "    if (!Coord2Index(start_pt, start_idx) || !Coord2Index(end_pt, end_idx))\n        return false;", '''    if (!Coord2Index(start_pt, start_idx) || !Coord2Index(end_pt, end_idx)) {
        reactive_stair::optimizerTrace("OPT_TRACE endpoint phase=initial_index_failed search=", reactive_stair::optimizerTraceState().search_calls);
        return false;
    }
    int trace_start_steps = 0, trace_end_steps = 0;''')
    once(search, "    int occ = checkOccupancy(Index2Coord(start_idx), path_yaw);", '''    int occ = checkOccupancy(Index2Coord(start_idx), path_yaw);
    reactive_stair::optimizerTrace("OPT_TRACE endpoint phase=start_initial search=", reactive_stair::optimizerTraceState().search_calls,
        " p=", reactive_stair::tracePoint(Index2Coord(start_idx)), " yaw=", path_yaw, " occ=", occ);''')
    once(search, "            start_pt -= start_to_end * step_size_;\n            if (!Coord2Index(start_pt, start_idx))\n                return false;", '''            start_pt -= start_to_end * step_size_;
            ++trace_start_steps;
            if (!Coord2Index(start_pt, start_idx)) {
                reactive_stair::optimizerTrace("OPT_TRACE endpoint phase=start_adjust_index_failed search=", reactive_stair::optimizerTraceState().search_calls,
                    " steps=", trace_start_steps, " p=", reactive_stair::tracePoint(start_pt), " index=", start_idx.transpose());
                return false;
            }''')
    once(search, "            occ = checkOccupancy(Index2Coord(start_idx), path_yaw);", '''            occ = checkOccupancy(Index2Coord(start_idx), path_yaw);
            reactive_stair::optimizerTrace("OPT_TRACE endpoint phase=start_adjust search=", reactive_stair::optimizerTraceState().search_calls,
                " steps=", trace_start_steps, " p=", reactive_stair::tracePoint(Index2Coord(start_idx)), " yaw=", path_yaw, " occ=", occ);''')
    once(search, "\n    occ = checkOccupancy(Index2Coord(end_idx), path_yaw);", '''
    occ = checkOccupancy(Index2Coord(end_idx), path_yaw);
    reactive_stair::optimizerTrace("OPT_TRACE endpoint phase=end_initial search=", reactive_stair::optimizerTraceState().search_calls,
        " p=", reactive_stair::tracePoint(Index2Coord(end_idx)), " yaw=", path_yaw, " occ=", occ);''')
    once(search, "            end_pt += start_to_end * step_size_;\n            if (!Coord2Index(end_pt, end_idx))\n                return false;", '''            end_pt += start_to_end * step_size_;
            ++trace_end_steps;
            if (!Coord2Index(end_pt, end_idx)) {
                reactive_stair::optimizerTrace("OPT_TRACE endpoint phase=end_adjust_index_failed search=", reactive_stair::optimizerTraceState().search_calls,
                    " steps=", trace_end_steps, " p=", reactive_stair::tracePoint(end_pt), " index=", end_idx.transpose());
                return false;
            }''')
    once(search, "            occ = checkOccupancy(Index2Coord(end_idx), path_yaw);", '''            occ = checkOccupancy(Index2Coord(end_idx), path_yaw);
            reactive_stair::optimizerTrace("OPT_TRACE endpoint phase=end_adjust search=", reactive_stair::optimizerTraceState().search_calls,
                " steps=", trace_end_steps, " p=", reactive_stair::tracePoint(Index2Coord(end_idx)), " yaw=", path_yaw, " occ=", occ);''')
    (out / "optimizer_trace_manifest.json").write_text(json.dumps({
        "base": args.base, "base_source_manifest_sha256": sha(base / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(out)): sha(p) for p in (helper, manager, optimizer, search)},
        "generator_sha256": sha(Path(__file__)), "helper_sha256": sha(HERE / helper.name),
        "claim": "First-replan buffered observation of seed/resampling/fit/optimization and existing AStar endpoint queries. Extra sampled-line and full-curve map checks occur only after original optimization has failed; they never affect acceptance. No thresholds, objective, search, spline or timing budget changed. Diagnostic overhead is not performance evidence."}, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()
