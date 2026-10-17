"""Create a hash-gated geometry-only candidate without editing SCAN33."""
import hashlib
import argparse
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ORIGINAL = BASE / "builds/scan33_humble_amd64_v1"
WORKSPACE = BASE / "runtime/scan34_geometry_v1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(path, old, new):
    data = path.read_bytes()
    if data.count(old.encode()) != 1:
        raise ValueError(f"Expected exactly one patch anchor in {path}: {old[:80]}")
    path.write_bytes(data.replace(old.encode(), new.encode()))


def remove_between(path, start, end):
    data = path.read_bytes()
    left, right = data.index(start.encode()), data.index(end.encode())
    if right <= left:
        raise ValueError("Invalid removal interval")
    path.write_bytes(data[:left] + data[right:])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=("geometry", "terrain_cache", "upstream_timing", "upstream_sampling", "ground_marking", "self_footprint", "bounded_retime", "goal_neighborhood", "reachable_goal"), default="geometry")
    parser.add_argument("--revision", type=int, default=1)
    args = parser.parse_args()
    global WORKSPACE
    if args.variant == "terrain_cache":
        WORKSPACE = BASE / "runtime/scan35_geometry_v1"
    elif args.variant == "upstream_timing":
        WORKSPACE = BASE / "runtime/scan36_geometry_v1"
    elif args.variant == "upstream_sampling":
        WORKSPACE = BASE / "runtime/scan37_geometry_v1"
    elif args.variant == "ground_marking":
        WORKSPACE = BASE / "runtime/scan38_geometry_v1"
    elif args.variant == "self_footprint":
        WORKSPACE = BASE / "runtime/scan39_geometry_v1"
    elif args.variant == "bounded_retime":
        WORKSPACE = BASE / "runtime/scan40_geometry_v1"
    elif args.variant == "goal_neighborhood":
        WORKSPACE = BASE / "runtime/scan41_geometry_v1"
    elif args.variant == "reachable_goal":
        WORKSPACE = BASE / "runtime/scan42_geometry_v1"
    if not 1 <= args.revision <= 20:
        parser.error("revision must be in [1,20]")
    WORKSPACE = WORKSPACE.with_name(WORKSPACE.name.rsplit("_v", 1)[0] + f"_v{args.revision}")
    original = json.loads((ORIGINAL / "source_sha256.json").read_text())
    actual = {name: sha(ORIGINAL / name) for name in original}
    if actual != original:
        raise ValueError("SCAN33 baseline source mismatch")
    if WORKSPACE.exists():
        raise FileExistsError(WORKSPACE)
    shutil.copytree(ORIGINAL / "src", WORKSPACE / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    header = WORKSPACE / "src/plan_env/include/plan_env/reactive_collision.h"
    remove_between(header, "struct Track {", "struct Query {")
    remove_between(header, "inline bool valid(const TrackSnapshot", "class CollisionDecision {")
    remove_between(header, "  bool acceptTracks(", "  Verdict decide(")
    replace_once(header, "  double track_max_age_s = 0.25;\n", "")
    replace_once(header, "!terrain_ready_ || !tracks_ready_ || obstacle.source_id.empty()", "!terrain_ready_ || obstacle.source_id.empty()")
    replace_once(header, "query.frame != terrain_.frame || query.frame != tracks_.frame || query.frame != obstacle.frame", "query.frame != terrain_.frame || query.frame != obstacle.frame")
    replace_once(header, "if (!fresh(query.stamp_s, tracks_.stamp_s, p_.track_max_age_s) ||\n        !fresh(query.stamp_s, terrain_.stamp_s", "if (!fresh(query.stamp_s, terrain_.stamp_s")
    remove_between(header, "    for (const Track &track : tracks_.tracks)", "    if (obstacle.occupancy == Occupancy::Unknown)")
    replace_once(header, "  TrackSnapshot tracks_;\n", "")
    replace_once(header, "  bool tracks_ready_ = false;\n", "")
    replace_once(header, "  Person,\n", "  Person,  // Reserved legacy log value; geometry-only queries never return it.\n")
    replace_once(header, "// Local experiment contract. This header has no ROS dependency and is not\n// connected to scan_05's GridMap until the three input producers are verified.",
                 "// Geometry-only navigation contract. All unclassified measured obstacles\n// block regardless of semantic class or motion. Required inputs are current\n// geometric occupancy and terrain support; person tracking is diagnostic only.")

    grid_header = WORKSPACE / "src/plan_env/include/plan_env/grid_map.h"
    data = grid_header.read_bytes().splitlines(keepends=True)
    grid_header.write_bytes(b"".join(line for line in data if not any(token in line for token in
        (b"tracked_person_snapshot.hpp", b"reactiveTracksCallback", b"reactive_tracks_sub_"))))
    grid = WORKSPACE / "src/plan_env/src/grid_map.cpp"
    lines = grid.read_bytes().splitlines(keepends=True)
    grid.write_bytes(b"".join(line for line in lines if b"reactive_track_max_age" not in line))
    remove_between(grid, "  reactive_tracks_sub_ =", "  occ_timer_ =")
    methods = WORKSPACE / "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc"
    remove_between(methods, "void GridMap::reactiveTracksCallback(", "bool GridMap::reactiveTerrainReturn(")
    if args.variant != "geometry":
        # Occupancy persists across scans. Its positive terrain classification
        # must have the same lifetime, with nonterrain observations taking
        # precedence. Cell reset, terrain-map replacement and ray clearing
        # invalidate the classification; semantic tracks never clear it.
        data = grid.read_bytes()
        start = data.index(b"void GridMap::cloudCallback(")
        end = data.index(b"void GridMap::publishMap()", start)
        part = data[start:end]
        if part.count(b"  reactive_terrain_hits_.clear();") != 1:
            raise ValueError("Unexpected terrain classification reset")
        part = part.replace(b"  reactive_terrain_hits_.clear();\r\n", b"")
        grid.write_bytes(data[:start] + part + data[end:])
        replace_once(grid,
            "  if (!now_occ) reactive_nonterrain_history_.erase(std::make_tuple(id.x(), id.y(), id.z()));",
            "  if (!now_occ) {\n    const auto key = std::make_tuple(id.x(), id.y(), id.z());\n    reactive_nonterrain_history_.erase(key);\n    reactive_terrain_hits_.erase(key);\n  }")
        raw = WORKSPACE / "src/plan_env/include/plan_env/raw_return_classification.h"
        data = raw.read_bytes().replace(b"current_terrain_return", b"confirmed_terrain_return")
        raw.write_bytes(data)
        replace_once(methods, "positively classified current LiDAR endpoints", "positively classified measured LiDAR endpoints")
        replace_once(methods, "have a positively classified current terrain return.", "have a retained, positively observed terrain classification.")
    if args.variant == "ground_marking":
        # Nav2's marking/clearing separation: a measured ground endpoint is
        # clearing evidence, not a newly marked obstacle. Keep the native
        # probabilistic ray update. Contradictory nonterrain in the same voxel
        # still marks occupancy, regardless of point order or semantic labels.
        replace_once(grid, "        vox_idx = setCacheOccupancy(pt_w, 1);", '''        Eigen::Vector3i endpoint;
        posToIndex(pt_w, endpoint);
        const auto endpoint_key = std::make_tuple(endpoint.x(), endpoint.y(), endpoint.z());
        const bool observed_ground = reactiveTerrainReturn(pt_w) &&
            reactive_nonterrain_hits_.count(endpoint_key) == 0;
        vox_idx = setCacheOccupancy(pt_w, observed_ground ? 0 : 1);''')
    if args.variant in ("self_footprint", "bounded_retime", "goal_neighborhood", "reachable_goal"):
        # Apply Nav2's current-footprint initialization convention using
        # SCAN's existing two-circle robot model. This narrower adaptation
        # resolves Unknown only; measured occupied/inflated cells are retained.
        trunk = WORKSPACE / "src/plan_env/include/plan_env/known_lite3_trunk.h"
        helper = '''
// Reference: Nav2 Humble 3c3db59 ObstacleLayer::updateFootprint/updateCosts.
// Geometry is the same two-circle footprint used by SCAN collision queries.
// Unlike Nav2's unconditional footprint clearing, an observed obstacle wins.
inline bool knownNavigationFootprintInterior(double x, double y, double z,
    double now, double pose_stamp, double radius, double offset) {
  if (!std::isfinite(x) || !std::isfinite(y) || !std::isfinite(z) ||
      !std::isfinite(radius) || radius < 0.0 || !std::isfinite(offset) || offset < 0.0 ||
      pose_stamp <= 0.0 || !fresh(now, pose_stamp, 0.1)) return false;
  const double dx = std::min(std::abs(x - offset), std::abs(x + offset));
  return dx * dx + y * y <= radius * radius && std::abs(z - 0.01) <= 0.06;
}

'''
        replace_once(trunk, "#include <cmath>", "#include <cmath>\n#include <algorithm>")
        replace_once(trunk, "inline Occupancy measuredTrunkQuery", helper + "inline Occupancy measuredTrunkQuery")
        replace_once(methods, "    const Eigen::Vector3d local = reactive_body_quaternion_.conjugate() *\n                                 (point - md_.sliding_map_frame_pos_);",
                     "    Eigen::Vector3d cell_center;\n    indexToPos(id, cell_center);\n    const Eigen::Vector3d local = reactive_body_quaternion_.conjugate() *\n                                 (cell_center - md_.sliding_map_frame_pos_);")
        replace_once(methods, "    const bool inside = reactive_stair::knownLite3TrunkInterior(\n        local.x(), local.y(), local.z(), query.stamp_s, reactive_body_stamp_s_);",
                     "    const bool inside = reactive_stair::knownNavigationFootprintInterior(\n        local.x(), local.y(), local.z(), query.stamp_s, reactive_body_stamp_s_,\n        mp_.double_cylinder_radius_, mp_.double_cylinder_offset_);")

    manager = WORKSPACE / "src/plan_manage/src/planner_manager.cpp"
    data = manager.read_bytes()
    manager.write_bytes(b"#include <iomanip>\n#include <sstream>\n" + data)
    capture = '''    // Diagnostic capture preserves the exact initializer input, before fitting.
    std::ostringstream seed_capture;
    seed_capture << std::setprecision(17) << "{\\\"interval\\\":" << ts
      << ",\\\"velocity_limit\\\":" << pp_.max_vel_ << ",\\\"acceleration_limit\\\":" << pp_.max_acc_
      << ",\\\"tolerance\\\":" << pp_.feasibility_tolerance_ << ",\\\"points\\\":[";
    for (size_t i = 0; i < point_set.size(); ++i) {
      if (i) seed_capture << ",";
      seed_capture << "[" << point_set[i].x() << "," << point_set[i].y() << "," << point_set[i].z() << "]";
    }
    seed_capture << "],\\\"derivatives\\\":[";
    for (size_t i = 0; i < start_end_derivatives.size(); ++i) {
      if (i) seed_capture << ",";
      const auto &d = start_end_derivatives[i];
      seed_capture << "[" << d.x() << "," << d.y() << "," << d.z() << "]";
    }
    seed_capture << "]}";
    RCLCPP_INFO(node_->get_logger(), "spline_seed_capture %s", seed_capture.str().c_str());
'''
    replace_once(manager, "    auto timed = reactive_stair::initializeTimedCubic", capture + "    auto timed = reactive_stair::initializeTimedCubic")
    if args.variant in ("upstream_timing", "upstream_sampling", "self_footprint", "bounded_retime", "goal_neighborhood", "reachable_goal"):
        # Restore SCAN's parameterize -> optimize -> time-refine order. Reuse
        # the existing hard-PVA fit as the endpoint adapter, not a new solver.
        data = manager.read_bytes()
        start = data.index(b"    auto timed = reactive_stair::initializeTimedCubic")
        end = data.index(b"    vector<vector<Eigen::Vector3d>> a_star_paths;", start)
        initial_fit = '''    if (!reactive_stair::fitCubicBoundaryPva(ts, point_set, start_end_derivatives, ctrl_pts)) {
      RCLCPP_WARN(node_->get_logger(), "spline_boundary_fit_failed");
      continuous_failures_count_++;
      return false;
    }
    RCLCPP_INFO(node_->get_logger(), "spline_geometry_initialized samples=%zu interval=%.12f duration=%.12f",
                point_set.size(), ts, ts * (point_set.size() - 1));

'''
        manager.write_bytes(data[:start] + initial_fit.encode() + data[end:])
        replace_once(manager, "    const double seed_interval = ts;\n", "")
        replace_once(manager, "    reparamBspline(traj, start_end_derivative, ratio, ctrl_pts, ts, t_inc);",
                     "    if (!reparamBspline(traj, start_end_derivative, ratio, ctrl_pts, ts, t_inc)) return false;")
        replace_once(manager, "  void SCANPlannerManager::reparamBspline(", "  bool SCANPlannerManager::reparamBspline(")
        replace_once(manager, "    UniformBspline::parameterizeToBspline(dt, point_set, start_end_derivative, ctrl_pts);",
                     "    return reactive_stair::fitCubicBoundaryPva(dt, point_set, start_end_derivative, ctrl_pts);")
        manager_header = WORKSPACE / "src/plan_manage/include/plan_manage/planner_manager.h"
        replace_once(manager_header, "    void reparamBspline(", "    bool reparamBspline(")
    if args.variant in ("upstream_sampling", "self_footprint", "bounded_retime", "goal_neighborhood", "reachable_goal"):
        data = manager.read_bytes()
        start = data.index(b"    const double seed_duration = ts *")
        end = data.index(b"    start_end_derivatives = {start_vel", start)
        # This is the existing SCAN arc-length sampling loop, applied to its
        # collision-checked AStar path. It uses the existing ctrl_pt_dist and
        # max_vel parameters; full output-curve validation remains mandatory.
        sampling = '''    // SCAN-Planner 348e8a5 planner_manager.cpp:210-231 (Apache-2.0):
    // use its control-point arc-length sampler, not the local quintic quota sampler.
    vector<double> pseudo_arc_length(1, 0.0);
    for (size_t i = 1; i < seed_path.size(); ++i)
      pseudo_arc_length.push_back(pseudo_arc_length.back() + (seed_path[i] - seed_path[i-1]).norm());
    double cps_dist = pp_.ctrl_pt_dist * 1.5;
    if (!std::isfinite(cps_dist) || cps_dist <= 0.0 ||
        !std::isfinite(pp_.max_vel_) || pp_.max_vel_ <= 0.0) return false;
    do {
      cps_dist /= 1.5;
      point_set.clear();
      double sample_length = 0.0;
      size_t id = 0;
      while (id <= pseudo_arc_length.size() - 2 && sample_length <= pseudo_arc_length.back()) {
        if (sample_length >= pseudo_arc_length[id] && sample_length < pseudo_arc_length[id + 1]) {
          point_set.push_back((sample_length - pseudo_arc_length[id]) / (pseudo_arc_length[id + 1] - pseudo_arc_length[id]) * seed_path[id + 1] +
              (pseudo_arc_length[id + 1] - sample_length) / (pseudo_arc_length[id + 1] - pseudo_arc_length[id]) * seed_path[id]);
          sample_length += cps_dist;
        } else ++id;
      }
      point_set.push_back(local_target_pt);
    } while (point_set.size() < 7);
    ts = cps_dist / pp_.max_vel_ * 1.2;
    RCLCPP_INFO(node_->get_logger(), "upstream_arclength_seed nodes=%zu samples=%zu spacing=%.12f interval=%.12f",
                seed_path.size(), point_set.size(), cps_dist, ts);
'''
        manager.write_bytes(data[:start] + sampling.encode() + data[end:])
    if args.variant in ("bounded_retime", "goal_neighborhood", "reachable_goal"):
        # Fast-Planner 41be219 uses at most three post-optimization time
        # adjustments. Reuse SCAN's own refinement and hard-PVA adapter here;
        # no new time allocator and no relaxation of any acceptance limit.
        data = manager.read_bytes()
        start = data.index(b"    double ratio;\r\n    bool flag_step_2_success = true;")
        end = data.index(b"    // A later native soft refit", start)
        retime = '''    bool flag_step_2_success = true;
    bool native_feasible = false;
    for (int adjustment = 0; adjustment <= 3; ++adjustment) {
      // Constructing a refined curve resets its physical-limit fields.
      pos.setPhysicalLimits(pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);
      double ratio = 0.0;
      native_feasible = pos.checkFeasibility(ratio, false);
      if (native_feasible || adjustment == 3) break;
      if (!std::isfinite(ratio) || ratio <= 1.0) {
        flag_step_2_success = false;
        break;
      }
      Eigen::MatrixXd optimal_control_points;
      flag_step_2_success = refineTrajAlgo(pos, start_end_derivatives, ratio, ts, optimal_control_points);
      if (!flag_step_2_success) break;
      pos = UniformBspline(optimal_control_points, 3, ts);
      RCLCPP_INFO(node_->get_logger(), "post_opt_time_adjustment iteration=%d ratio=%.12f duration=%.12f",
                  adjustment + 1, ratio, pos.getTimeSum());
    }
    flag_step_2_success = flag_step_2_success && native_feasible;

'''
        manager.write_bytes(data[:start] + retime.encode() + data[end:])
    if args.variant in ("goal_neighborhood", "reachable_goal"):
        fsm = WORKSPACE / "src/plan_manage/src/scan_replan_fsm.cpp"
        fsm_header = WORKSPACE / "src/plan_manage/include/plan_manage/scan_replan_fsm.h"
        replace_once(fsm_header, "    double reference_frontier_time_{-1.0};",
                     "    double reference_frontier_time_{-1.0};\n    bool reference_neighbor_target_{false};\n    Eigen::Vector3d reference_neighbor_point_{Eigen::Vector3d::Zero()};")
        replace_once(fsm, "    reference_frontier_time_ = -1.0;",
                     "    reference_frontier_time_ = -1.0;\n    reference_neighbor_target_ = false;")
        anchor = "    for (int i = sample_num; i >= 0; --i)"
        neighborhood = '''    if (reference) {
      // Nav2 NavfnPlanner::makePlan, Humble 3c3db59 (Apache-2.0):
      // search a resolution-spaced goal neighborhood, nearest candidate first.
      // Navfn tests finite potential; here native SCAN AStar and complete spline
      // validation establish reachability after this measured-free proposal.
      // The final user goal and global reference are never replaced.
      constexpr double tolerance = 0.5;  // Navfn's default neighborhood [m].
      const double resolution = map->getResolution();
      double best_distance = std::numeric_limits<double>::infinity();
      if (std::isfinite(resolution) && resolution > 0.0) {
        const int cells = static_cast<int>(std::floor(tolerance / resolution));
        for (int iy = -cells; iy <= cells; ++iy) {
          for (int ix = -cells; ix <= cells; ++ix) {
            const Eigen::Vector3d point = final_pt + Eigen::Vector3d(ix * resolution, iy * resolution, 0.0);
            const double distance = (point - final_pt).squaredNorm();
            if (distance >= best_distance || distance <= 0.0) continue;
            const double yaw = estimateYawFromSegment(start_pt_, point);
            if (!std::isfinite(yaw) || map->getInflateOccupancy(point, yaw) != 0) continue;
            reference_neighbor_point_ = point;
            best_distance = distance;
          }
        }
      }
      if (std::isfinite(best_distance)) {
        reference_frontier_time_ = duration;
        reference_neighbor_target_ = true;
        RCLCPP_INFO(node_->get_logger(), "reference_goal_neighbor xyz=[%.12f,%.12f,%.12f] displacement=%.12f final_goal_unchanged=1",
                    reference_neighbor_point_.x(), reference_neighbor_point_.y(), reference_neighbor_point_.z(), std::sqrt(best_distance));
        return true;
      }
    }

'''
        replace_once(fsm, anchor, neighborhood + anchor)
        replace_once(fsm, "    const Eigen::Vector3d selection_end = reference ? planner_manager_->global_data_.getPosition(duration) : end_pt_;",
                     "    const Eigen::Vector3d selection_end = reference\n        ? (reference_neighbor_target_ ? reference_neighbor_point_ : planner_manager_->global_data_.getPosition(duration))\n        : end_pt_;")
        replace_once(fsm, "            global_data.last_progress_time_ < global_data.global_duration_ - 1e-3;",
                     "            (global_data.last_progress_time_ < global_data.global_duration_ - 1e-3 ||\n             (info->position_traj_.evaluateDeBoorT(info->duration_) - end_pt_).norm() > 1e-3);")
        if args.variant == "reachable_goal":
            replace_once(fsm_header, "    bool reference_neighbor_target_{false};",
                         "    bool reference_neighbor_target_{false};\n    double goal_neighbor_tolerance_{0.5};")
            replace_once(fsm, "    emergency_time_ = load_parameter<double>(node_, \"fsm.emergency_time\", 1.0);",
                         '''    goal_neighbor_tolerance_ = load_parameter<double>(node_, "fsm.goal_neighbor_tolerance", 0.5);
    if (!std::isfinite(goal_neighbor_tolerance_) || goal_neighbor_tolerance_ <= 0.0 ||
        goal_neighbor_tolerance_ > planning_horizon_) throw std::runtime_error("Invalid local goal neighborhood");
    emergency_time_ = load_parameter<double>(node_, "fsm.emergency_time", 1.0);''')
            # Nav2 Smac AStar uses a reached search node within goal tolerance,
            # not just a locally empty cell. Reuse SCAN's graph/edge checker,
            # with one approach iteration and the original 0.2 s search limit.
            reachable = '''    if (reference) {
      const auto path = planner_manager_->findGoalNeighborhoodPath(start_pt_, final_pt, goal_neighbor_tolerance_);
      if (!path.empty()) {
        if (path.size() > 1 && (path.back() - final_pt).norm() <= goal_neighbor_tolerance_ &&
            (path.back() - start_pt_).norm() >= 0.2) {
          reference_neighbor_point_ = path.back();
          reference_frontier_time_ = duration;
          reference_neighbor_target_ = true;
          RCLCPP_INFO(node_->get_logger(), "reference_goal_neighbor xyz=[%.12f,%.12f,%.12f] displacement=%.12f reached_path_points=%zu final_goal_unchanged=1",
                      path.back().x(), path.back().y(), path.back().z(), (path.back()-final_pt).norm(), path.size());
          return true;
        }
      }
    }

'''
            replace_once(fsm, neighborhood, reachable)
            replace_once(manager_header, "    void initPlanModules(",
                         "    std::vector<Eigen::Vector3d> findGoalNeighborhoodPath(const Eigen::Vector3d &start, const Eigen::Vector3d &goal, double tolerance);\n    void initPlanModules(")
            replace_once(manager, "  bool SCANPlannerManager::EmergencyStop(",
                         '''  std::vector<Eigen::Vector3d> SCANPlannerManager::findGoalNeighborhoodPath(
      const Eigen::Vector3d &start, const Eigen::Vector3d &goal, double tolerance) {
    if (!grid_map_ || !bspline_optimizer_rebound_ || !bspline_optimizer_rebound_->a_star_) return {};
    const auto search = bspline_optimizer_rebound_->a_star_;
    if (search->AstarSearch(grid_map_->getResolution(), start, goal, true, tolerance) != ASTAR_RET::SUCCESS) return {};
    return search->getPath();
  }

  bool SCANPlannerManager::EmergencyStop(''')
            astar_header = WORKSPACE / "src/path_searching/include/path_searching/dyn_a_star.h"
            astar = WORKSPACE / "src/path_searching/src/dyn_a_star.cpp"
            replace_once(astar_header, "Eigen::Vector3d end_pt, bool exact_endpoint = false);",
                         "Eigen::Vector3d end_pt, bool exact_endpoint = false, double goal_tolerance = 0.0);")
            replace_once(astar, "Vector3d end_pt, bool exact_endpoint)",
                         "Vector3d end_pt, bool exact_endpoint, double goal_tolerance)")
            replace_once(astar, "    if (!std::isfinite(step_size) || step_size <= 0.0 ||",
                         "    if (!std::isfinite(goal_tolerance) || goal_tolerance < 0.0 ||\n        (!exact_endpoint && goal_tolerance != 0.0) ||\n        !std::isfinite(step_size) || step_size <= 0.0 ||")
            replace_once(astar, "        if (exact_endpoint && (Index2Coord(current->index) - end_pt).norm() <= 2.0 * step_size_)",
                         '''        // Nav2 Smac AStar, Humble 3c3db59 (Apache-2.0): a reached
        // node inside goal tolerance is a valid local proposal. Every edge
        // was checked by SCAN. Default tolerance zero keeps exact semantics.
        if (goal_tolerance > 0.0 && current->cameFrom != nullptr &&
            (Index2Coord(current->index) - end_pt).norm() <= goal_tolerance) {
            const Eigen::Vector3d proposal = Index2Coord(current->index);
            const Eigen::Vector3d direction = proposal - start_pt;
            const double selection_yaw = std::atan2(direction.y(), direction.x());
            const double stopped_yaw = grid_map_->collisionTrajectoryYaw(
                proposal, proposal, Eigen::Vector3d::Zero());
            // A reached edge alone is insufficient for an anisotropic robot.
            // Match the FSM target query and the stopped endpoint query too.
            if (grid_map_->getInflateOccupancy(proposal, selection_yaw) == 0 &&
                grid_map_->getInflateOccupancy(proposal, stopped_yaw) == 0) {
                gridPath_ = retrievePath(current);
                return ASTAR_RET::SUCCESS;
            }
        }
        if (exact_endpoint && (Index2Coord(current->index) - end_pt).norm() <= 2.0 * step_size_)''')
            # Keep the stair graph as the default. The explicit flat control
            # profile can select the original upstream SCAN search plane.
            replace_once(astar_header, "    ASTAR_RET AstarSearch(",
                         "    bool use_upstream_search_plane{false};\n    ASTAR_RET AstarSearch(")
            upstream_astar = BASE / "references/2026-09-26_generic_occupancy/wuyi2121__SCAN-Planner/src/planner/path_searching/src/dyn_a_star.cpp"
            upstream_record = json.loads((upstream_astar.parents[4] / "source.json").read_text())
            if sha(upstream_astar) != upstream_record["sha256"]:
                raise ValueError("Pinned upstream search plane changed")
            upstream_text = upstream_astar.read_text()
            plane_start = upstream_text.index("    const Eigen::Vector3d search_start =")
            plane_end = upstream_text.index("    // if ( start_pt", plane_start)
            replace_once(astar, "    GridNodePtr startPtr =", upstream_text[plane_start:plane_end] + "    GridNodePtr startPtr =")
            replace_once(astar, "for (int dz_step = -1; dz_step <= 1; dz_step++)",
                         "for (int dz_step = (use_upstream_search_plane ? 0 : -1); dz_step <= (use_upstream_search_plane ? 0 : 1); dz_step++)")
            replace_once(astar, "                neighborIdx(2) = current->index(2) + dz_step;",
                         "                neighborIdx(2) = use_upstream_search_plane\n                    ? interpolateZIndexOnSearchPlane(neighborIdx(0), neighborIdx(1))\n                    : current->index(2) + dz_step;")
            replace_once(manager, "    visualization_ = vis;",
                         '''    if (!node_->has_parameter("manager.use_upstream_search_plane"))
      node_->declare_parameter<bool>("manager.use_upstream_search_plane", false);
    bspline_optimizer_rebound_->a_star_->use_upstream_search_plane =
        node_->get_parameter("manager.use_upstream_search_plane").as_bool();
    visualization_ = vis;''')
    shutil.copytree(HERE / "geometry_probe", WORKSPACE / "src/geometry_probe")
    manifest = {"src/" + str(path.relative_to(WORKSPACE / "src")): sha(path)
                for path in sorted((WORKSPACE / "src").rglob("*")) if path.is_file()}
    (WORKSPACE / "source_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")
    changed = {name: value for name, value in manifest.items() if original.get(name) != value}
    identity_name = {"geometry": "candidate_identity.json", "terrain_cache": "candidate_terrain_cache_identity.json",
                     "upstream_timing": "candidate_upstream_timing_identity.json",
                     "upstream_sampling": "candidate_upstream_sampling_identity.json",
                     "ground_marking": "candidate_ground_marking_identity.json",
                     "self_footprint": "candidate_self_footprint_identity.json",
                     "bounded_retime": "candidate_bounded_retime_identity.json",
                     "goal_neighborhood": "candidate_goal_neighborhood_identity.json",
                     "reachable_goal": "candidate_reachable_goal_identity.json"}[args.variant]
    if args.revision != 1:
        identity_name = identity_name.replace(".json", f"_v{args.revision}.json")
    (HERE / identity_name).write_text(json.dumps({
        "original": str(ORIGINAL), "workspace": str(WORKSPACE),
        "original_manifest_sha256": sha(ORIGINAL / "source_sha256.json"),
        "generator_sha256": sha(Path(__file__)), "variant": args.variant, "changed_files": changed,
        "source_sha256": manifest,
        "contract": "Native geometric occupancy and support own navigation; no semantic tracker input or simulator truth. Upstream timing variant restores optimize-before-retime with existing hard endpoint fit; other variants preserve original timing."
    }, indent=2) + "\n")
    shutil.copyfile(Path(__file__), WORKSPACE / "executed_materialize.py")
    print(json.dumps({"workspace": str(WORKSPACE), "changed_files": list(changed)}))


if __name__ == "__main__":
    main()
