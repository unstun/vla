"""Diagnostic-only trace copy of the point-semantics counterfactual tree.

Copies ../point_waiver_probe/workspace (the v28 tree with the known-footprint
waiver evaluated at the queried point, already built) and its probe source,
then adds stderr tracing gated by the VLA_TRACE environment variable:

- GridMap::reactiveOccupancy and reactiveFootprintSupportQuery: each blocked
  query inside a traced scope, with the reason (map boundary, footprint
  support or final verdict), the raw voxel state before the waiver, the
  waiver's inside flag, the body-local query coordinates and the log-odds.
- BsplineOptimizer::initControlPoints, check_collision_and_rebound and the
  rebound/refine post-checks: blocked points, segments and A* results.
- AStar::ConvertToIndexAndAdjustStartEndPoints (the optimizer's non-exact
  calls only): endpoint checks with the path yaw and the endpoint walk.
- SCANPlannerManager::reboundReplanAttempt: raw seed nodes and refine checks.
- gen_probe: a dump of the voxels within 1.5 m (xy) and 0.4 m (z) of the start.

Planner decisions are unchanged: tracing only reads the same map state, and a
traced scope never alters a query result. Not a version, not for production.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "point_waiver_probe"
WORKSPACE = HERE / "workspace"
PROBE = HERE / "probe_source"
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
EXPECTED = {
    "src/plan_env/include/plan_env/scan_reactive_grid_methods.inc":
        "acc02d436fe91b3beb300197bbf514b448bdd19ca033ba5e734e0ed9c7af5505",
}


def once(text, old, new):
    pattern = r"\r?\n".join(re.escape(line) for line in old.split("\n"))
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError("anchor count %d: %s" % (len(matches), old[:90]))
    match = matches[0]
    ending = "\r\n" if "\r\n" in match.group() else "\n"
    return text[:match.start()] + new.replace("\n", ending) + text[match.end():]


assert not WORKSPACE.exists() and not PROBE.exists()
for name, digest in EXPECTED.items():
    assert sha(PARENT / "workspace" / name) == digest, name
for part in ("src", "build", "install"):
    shutil.copytree(PARENT / "workspace" / part, WORKSPACE / part, symlinks=True)
shutil.copytree(PARENT / "probe_source", PROBE)
before = {str(p.relative_to(HERE)): sha(p) for p in sorted((WORKSPACE / "src").rglob("*")) if p.is_file()}
before.update({str(p.relative_to(HERE)): sha(p) for p in sorted(PROBE.rglob("*")) if p.is_file()})

(WORKSPACE / "src/plan_env/include/plan_env/trace_diag.h").write_text(r'''// Diagnostic-only tracing for audits/2026-09-28_v28_start_thrash/optimizer_trace.
#pragma once
#include <cstdarg>
#include <cstdio>
#include <cstdlib>

namespace trace_diag {
inline bool enabled() { static const bool value = std::getenv("VLA_TRACE") != nullptr; return value; }
inline int &depth() { static int value = 0; return value; }
inline long &count() { static long value = 0; return value; }
inline bool on() { return enabled() && count() < 400000; }
inline bool active() { return on() && depth() > 0; }
inline void emit(const char *format, ...) {
  ++count();
  va_list args;
  va_start(args, format);
  std::vfprintf(stderr, format, args);
  va_end(args);
}
struct Scope {
  int saved;
  explicit Scope(int value) : saved(depth()) { depth() = value; }
  ~Scope() { depth() = saved; }
};
}  // namespace trace_diag
''')


def edit(relative, *pairs):
    path = WORKSPACE / relative if relative.startswith("src/") else HERE / relative
    text = path.read_bytes().decode()
    for old, new in pairs:
        text = once(text, old, new)
    path.write_bytes(text.encode())


Q = "p=(%.4f,%.4f,%.4f) body=(%.4f,%.4f,%.4f) raw=%d occ=%d inside=%d local=(%.4f,%.4f,%.4f) log_odds=%.5f inflate=%d support_z=%.4f"
QARGS = ("point.x(), point.y(), point.z(), trace_body.x(), trace_body.y(), trace_body.z(), "
         "static_cast<int>(trace_raw), static_cast<int>(obstacle.occupancy), trace_inside, "
         "trace_local.x(), trace_local.y(), trace_local.z(), trace_log_odds, trace_inflate, query.z_m")
TRACE_FIELDS = (
    "    double trace_log_odds = std::numeric_limits<double>::quiet_NaN();\n"
    "    int trace_inflate = -1;\n"
    "    if (query.in_map) {\n"
    "      Eigen::Vector3i trace_id;\n"
    "      posToIndex(point, trace_id);\n"
    "      trace_log_odds = md_.occupancy_buffer_[toAddress(trace_id)];\n"
    "      trace_inflate = md_.occupancy_buffer_inflate_[toAddress(trace_id)];\n"
    "    }\n"
    "    const Eigen::Vector3d trace_body = body_reference ? *body_reference :\n"
    "        Eigen::Vector3d::Constant(std::numeric_limits<double>::quiet_NaN());\n")

edit("src/plan_env/include/plan_env/scan_reactive_grid_methods.inc",
     ("#include <plan_env/motion_heading.h>\n",
      "#include <plan_env/motion_heading.h>\n#include <plan_env/trace_diag.h>\n"),
     ("  if (reactive_decision_.decide(body_query, support_only) != reactive_stair::Verdict::Free)\n    return false;\n",
      "  const auto trace_body_verdict = reactive_decision_.decide(body_query, support_only);\n"
      "  if (trace_body_verdict != reactive_stair::Verdict::Free) {\n"
      "    if (trace_diag::active())\n"
      "      trace_diag::emit(\"TRACE_SUPPORT reason=body_verdict v=%d body=(%.4f,%.4f,%.4f) q=(%.4f,%.4f,%.4f)\\n\",\n"
      "          static_cast<int>(trace_body_verdict), body_query.x_m, body_query.y_m, body_query.z_m,\n"
      "          query.x_m, query.y_m, query.z_m);\n"
      "    return false;\n"
      "  }\n"),
     ("  if (!associated_height(body_query.x_m, body_query.y_m,\n"
      "          body_query.z_m - reactive_parameters_.body_clearance_m,\n"
      "          reactive_parameters_.body_height_tolerance_m, body_ground) ||\n"
      "      !associated_height(query.x_m, query.y_m, body_ground, step, footprint_ground) ||\n"
      "      std::abs(footprint_ground - body_ground) >= step) return false;\n",
      "  const bool trace_body_ok = associated_height(body_query.x_m, body_query.y_m,\n"
      "          body_query.z_m - reactive_parameters_.body_clearance_m,\n"
      "          reactive_parameters_.body_height_tolerance_m, body_ground);\n"
      "  const bool trace_foot_ok = trace_body_ok &&\n"
      "      associated_height(query.x_m, query.y_m, body_ground, step, footprint_ground);\n"
      "  if (!trace_body_ok || !trace_foot_ok || std::abs(footprint_ground - body_ground) >= step) {\n"
      "    if (trace_diag::active())\n"
      "      trace_diag::emit(\"TRACE_SUPPORT reason=%s body=(%.4f,%.4f,%.4f) q=(%.4f,%.4f,%.4f) body_ground=%.4f foot_ground=%.4f\\n\",\n"
      "          !trace_body_ok ? \"body_height\" : (!trace_foot_ok ? \"foot_height\" : \"step\"),\n"
      "          body_query.x_m, body_query.y_m, body_query.z_m, query.x_m, query.y_m, query.z_m,\n"
      "          trace_body_ok ? body_ground : std::numeric_limits<double>::quiet_NaN(),\n"
      "          trace_foot_ok ? footprint_ground : std::numeric_limits<double>::quiet_NaN());\n"
      "    return false;\n"
      "  }\n"),
     ("      point.z() + mp_.obstacles_inflation_z_up > mp_.map_max_boundary_.z()) return 1;\n",
      "      point.z() + mp_.obstacles_inflation_z_up > mp_.map_max_boundary_.z()) {\n"
      "    if (trace_diag::active())\n"
      "      trace_diag::emit(\"TRACE_Q reason=boundary p=(%.4f,%.4f,%.4f)\\n\", point.x(), point.y(), point.z());\n"
      "    return 1;\n"
      "  }\n"),
     ("  if (reactive_known_trunk_enabled_ && query.in_map && reactive_body_stamp_s_ > 0.0) {\n",
      "  const auto trace_raw = obstacle.occupancy;\n"
      "  Eigen::Vector3d trace_local = Eigen::Vector3d::Constant(std::numeric_limits<double>::quiet_NaN());\n"
      "  int trace_inside = -1;\n"
      "  if (reactive_known_trunk_enabled_ && query.in_map && reactive_body_stamp_s_ > 0.0) {\n"),
     ("    obstacle.occupancy = reactive_stair::measuredTrunkQuery(\n",
      "    trace_local = local;\n"
      "    trace_inside = inside ? 1 : 0;\n"
      "    obstacle.occupancy = reactive_stair::measuredTrunkQuery(\n"),
     ("  if (body_reference && !reactiveFootprintSupportQuery(*body_reference, obstacle, query)) return 1;\n",
      "  if (body_reference && !reactiveFootprintSupportQuery(*body_reference, obstacle, query)) {\n"
      "    if (trace_diag::active()) {\n" + TRACE_FIELDS +
      "      trace_diag::emit(\"TRACE_Q reason=support " + Q + "\\n\", " + QARGS + ");\n"
      "    }\n"
      "    return 1;\n"
      "  }\n"),
     ("  return verdict == reactive_stair::Verdict::Free ? 0 : 1;\n}\n",
      "  if (verdict != reactive_stair::Verdict::Free && trace_diag::active()) {\n" + TRACE_FIELDS +
      "    trace_diag::emit(\"TRACE_Q reason=verdict v=%d " + Q + "\\n\", static_cast<int>(verdict), " + QARGS + ");\n"
      "  }\n"
      "  return verdict == reactive_stair::Verdict::Free ? 0 : 1;\n}\n"))

P3 = "(%.4f,%.4f,%.4f)"
edit("src/path_searching/src/dyn_a_star.cpp",
     ('#include "path_searching/dyn_a_star.h"\n',
      '#include "path_searching/dyn_a_star.h"\n#include <plan_env/trace_diag.h>\n'),
     ("    int occ = checkOccupancy(Index2Coord(start_idx), path_yaw);\n",
      "    if (trace_diag::on())\n"
      "        trace_diag::emit(\"TRACE_ASTAR_ENDPOINTS start=" + P3 + " end=" + P3 + " yaw=%.4f step=%.3f\\n\",\n"
      "            start_pt.x(), start_pt.y(), start_pt.z(), end_pt.x(), end_pt.y(), end_pt.z(), path_yaw, step_size_);\n"
      "    int occ;\n"
      "    {\n"
      "        trace_diag::Scope trace_on(1);\n"
      "        occ = checkOccupancy(Index2Coord(start_idx), path_yaw);\n"
      "    }\n"
      "    if (trace_diag::on()) trace_diag::emit(\"TRACE_ASTAR_START occ=%d\\n\", occ);\n"),
     ("            occ = checkOccupancy(Index2Coord(start_idx), path_yaw);\n",
      "            occ = checkOccupancy(Index2Coord(start_idx), path_yaw);\n"
      "            if (trace_diag::on())\n"
      "                trace_diag::emit(\"TRACE_WALK side=start p=" + P3 + " occ=%d\\n\", start_pt.x(), start_pt.y(), start_pt.z(), occ);\n"),
     # The trailing "if (occ)" keeps this anchor distinct from the 12-space walk line.
     ("    occ = checkOccupancy(Index2Coord(end_idx), path_yaw);\n    if (occ)\n",
      "    {\n"
      "        trace_diag::Scope trace_on(1);\n"
      "        occ = checkOccupancy(Index2Coord(end_idx), path_yaw);\n"
      "    }\n"
      "    if (trace_diag::on()) trace_diag::emit(\"TRACE_ASTAR_END occ=%d\\n\", occ);\n"
      "    if (occ)\n"),
     ("            occ = checkOccupancy(Index2Coord(end_idx), path_yaw);\n",
      "            occ = checkOccupancy(Index2Coord(end_idx), path_yaw);\n"
      "            if (trace_diag::on())\n"
      "                trace_diag::emit(\"TRACE_WALK side=end p=" + P3 + " occ=%d\\n\", end_pt.x(), end_pt.y(), end_pt.z(), occ);\n"),
     ("    const auto time_1 = std::chrono::steady_clock::now();\n",
      "    const auto time_1 = std::chrono::steady_clock::now();\n"
      "    trace_diag::Scope trace_off(0);\n"))

edit("src/bspline_opt/src/bspline_optimizer.cpp",
     ('#include "bspline_opt/bspline_optimizer.h"\n',
      '#include "bspline_opt/bspline_optimizer.h"\n#include <plan_env/trace_diag.h>\n'),
     ("    /*** Segment the initial trajectory according to obstacles ***/\n    constexpr int ENOUGH_INTERVAL = 2;\n",
      "    trace_diag::Scope trace_init(1);\n"
      "    if (trace_diag::on())\n"
      "    {\n"
      "      trace_diag::emit(\"TRACE_INIT first=%d n=%d cps=\", int(flag_first_init), int(init_points.cols()));\n"
      "      for (int c = 0; c < init_points.cols(); ++c)\n"
      "        trace_diag::emit(\"[%.4f,%.4f,%.4f]\", init_points(0, c), init_points(1, c), init_points(2, c));\n"
      "      trace_diag::emit(\"\\n\");\n"
      "    }\n"
      "    /*** Segment the initial trajectory according to obstacles ***/\n    constexpr int ENOUGH_INTERVAL = 2;\n"),
     ("        occ = grid_map_->getInflateOccupancy(sample_pt, sample_yaw);\n        // cout << setprecision(5);\n",
      "        occ = grid_map_->getInflateOccupancy(sample_pt, sample_yaw);\n"
      "        if (trace_diag::on() && occ != last_occ)\n"
      "          trace_diag::emit(\"TRACE_INIT_SAMPLE i=%d a=%.3f p=" + P3 + " yaw=%.4f occ=%d\\n\",\n"
      "                           i, a, sample_pt.x(), sample_pt.y(), sample_pt.z(), sample_yaw, int(occ));\n"
      "        // cout << setprecision(5);\n"),
     ("    /*** a star search ***/\n    vector<vector<Eigen::Vector3d>> a_star_paths;\n    for (size_t i = 0; i < segment_ids.size(); ++i)\n    {\n",
      "    if (trace_diag::on())\n"
      "    {\n"
      "      trace_diag::emit(\"TRACE_INIT_SEGMENTS n=%zu\", segment_ids.size());\n"
      "      for (const auto &segment : segment_ids)\n"
      "        trace_diag::emit(\" [%d,%d]\", segment.first, segment.second);\n"
      "      trace_diag::emit(\"\\n\");\n"
      "    }\n"
      "    /*** a star search ***/\n    vector<vector<Eigen::Vector3d>> a_star_paths;\n    for (size_t i = 0; i < segment_ids.size(); ++i)\n    {\n"),
     ("      Eigen::Vector3d in(init_points.col(segment_ids[i].first)), out(init_points.col(segment_ids[i].second));\n"
      "      ASTAR_RET ret = a_star_->AstarSearch(grid_map_->getResolution(), in, out);\n",
      "      Eigen::Vector3d in(init_points.col(segment_ids[i].first)), out(init_points.col(segment_ids[i].second));\n"
      "      ASTAR_RET ret = a_star_->AstarSearch(grid_map_->getResolution(), in, out);\n"
      "      if (trace_diag::on())\n"
      "        trace_diag::emit(\"TRACE_INIT_ASTAR seg=%zu in=%d out=%d ret=%d path=%zu\\n\", i, segment_ids[i].first,\n"
      "                         segment_ids[i].second, int(ret), ret == ASTAR_RET::SUCCESS ? a_star_->getPath().size() : size_t(0));\n"),
     ("  bool BsplineOptimizer::check_collision_and_rebound(void)\n  {\n",
      "  bool BsplineOptimizer::check_collision_and_rebound(void)\n  {\n    trace_diag::Scope trace_rebound(1);\n"),
     ("        flag_new_obs_valid = true;\n",
      "        flag_new_obs_valid = true;\n"
      "        if (trace_diag::on())\n"
      "          trace_diag::emit(\"TRACE_REB_HIT i=%d p=" + P3 + " yaw=%.4f\\n\", i, cps_.points(0, i), cps_.points(1, i),\n"
      "                           cps_.points(2, i), estimateControlPointYaw(cps_.points, i));\n"),
     ("        segment_ids.push_back(std::pair<int, int>(in_id, out_id));\n      }\n    }\n",
      "        if (trace_diag::on()) trace_diag::emit(\"TRACE_REB_SEG in=%d out=%d\\n\", in_id, out_id);\n"
      "        segment_ids.push_back(std::pair<int, int>(in_id, out_id));\n      }\n    }\n"),
     ("        Eigen::Vector3d in(cps_.points.col(segment_ids[i].first)), out(cps_.points.col(segment_ids[i].second));\n"
      "        ASTAR_RET ret = a_star_->AstarSearch(grid_map_->getResolution(), in, out);\n",
      "        Eigen::Vector3d in(cps_.points.col(segment_ids[i].first)), out(cps_.points.col(segment_ids[i].second));\n"
      "        ASTAR_RET ret = a_star_->AstarSearch(grid_map_->getResolution(), in, out);\n"
      "        if (trace_diag::on())\n"
      "          trace_diag::emit(\"TRACE_REB_ASTAR seg=%zu in=%d out=%d ret=%d path=%zu\\n\", i, segment_ids[i].first,\n"
      "                           segment_ids[i].second, int(ret), ret == ASTAR_RET::SUCCESS ? a_star_->getPath().size() : size_t(0));\n"),
     ("          flag_occ = grid_map_->getInflateOccupancy(pos, estimateSegmentYaw(pos, pos_next));\n",
      "          {\n"
      "            trace_diag::Scope trace_post(1);\n"
      "            flag_occ = grid_map_->getInflateOccupancy(pos, estimateSegmentYaw(pos, pos_next));\n"
      "          }\n"
      "          if (trace_diag::on() && flag_occ)\n"
      "            trace_diag::emit(\"TRACE_POST t=%.4f interval=%.4f p=" + P3 + " yaw=%.4f\\n\", t, bspline_interval_,\n"
      "                             pos.x(), pos.y(), pos.z(), estimateSegmentYaw(pos, pos_next));\n"),
     ("        if (grid_map_->getInflateOccupancy(pos, estimateSegmentYaw(pos, pos_next)))\n        {\n",
      "        int trace_refine_occ;\n"
      "        {\n"
      "          trace_diag::Scope trace_refine(1);\n"
      "          trace_refine_occ = grid_map_->getInflateOccupancy(pos, estimateSegmentYaw(pos, pos_next));\n"
      "        }\n"
      "        if (trace_refine_occ)\n        {\n"
      "          if (trace_diag::on())\n"
      "            trace_diag::emit(\"TRACE_REFINE_POST t=%.4f p=" + P3 + " yaw=%.4f\\n\", t, pos.x(), pos.y(), pos.z(),\n"
      "                             estimateSegmentYaw(pos, pos_next));\n"))

edit("src/plan_manage/src/planner_manager.cpp",
     ("#include <plan_manage/planner_manager.h>\n",
      "#include <plan_manage/planner_manager.h>\n#include <plan_env/trace_diag.h>\n"),
     ("    std::vector<Eigen::Vector3d> seed_path = seed_search->getPath();\n",
      "    std::vector<Eigen::Vector3d> seed_path = seed_search->getPath();\n"
      "    if (trace_diag::on()) {\n"
      "      trace_diag::emit(\"TRACE_SEED n=%zu nodes=\", seed_path.size());\n"
      "      for (const auto &node : seed_path) trace_diag::emit(\"[%.4f,%.4f,%.4f]\", node.x(), node.y(), node.z());\n"
      "      trace_diag::emit(\"\\n\");\n"
      "    }\n"),
     ("      native_feasible = pos.checkFeasibility(ratio, false);\n",
      "      native_feasible = pos.checkFeasibility(ratio, false);\n"
      "      if (trace_diag::on())\n"
      "        trace_diag::emit(\"TRACE_REFINE adjustment=%d feasible=%d ratio=%.6f\\n\", adjustment, int(native_feasible), ratio);\n"),
     ("      flag_step_2_success = refineTrajAlgo(pos, start_end_derivatives, ratio, ts, optimal_control_points);\n",
      "      flag_step_2_success = refineTrajAlgo(pos, start_end_derivatives, ratio, ts, optimal_control_points);\n"
      "      if (trace_diag::on())\n"
      "        trace_diag::emit(\"TRACE_REFINE_ALGO adjustment=%d success=%d\\n\", adjustment, int(flag_step_2_success));\n"),
     ("    if (!flag_step_2_success || !checkDynamicFeasibility(pos))\n",
      "    if (trace_diag::on())\n"
      "      trace_diag::emit(\"TRACE_REFINE_RESULT step2=%d native=%d\\n\", int(flag_step_2_success), int(native_feasible));\n"
      "    if (!flag_step_2_success || !checkDynamicFeasibility(pos))\n"))

edit("probe_source/src/gen_probe.cpp",
     ("  map->logInitialSplineCollision(original_start,start_yaw);\n",
      "  map->logInitialSplineCollision(original_start,start_yaw);\n"
      "  {\n"
      "    // Diagnostic voxel dump around the start; read-only.\n"
      "    std::ofstream dump(fs::path(output).parent_path()/(fs::path(output).stem().string()+\"_voxels.csv\"));\n"
      "    dump<<std::setprecision(9)<<\"ix,iy,iz,cx,cy,cz,log_odds,inflate\\n\";\n"
      "    Eigen::Vector3i low,high;\n"
      "    map->posToIndex(original_start-Eigen::Vector3d(1.5,1.5,0.4),low);\n"
      "    map->posToIndex(original_start+Eigen::Vector3d(1.5,1.5,0.4),high);\n"
      "    for(int x=low.x();x<=high.x();++x)for(int y=low.y();y<=high.y();++y)for(int z=low.z();z<=high.z();++z){\n"
      "      const Eigen::Vector3i id(x,y,z);if(!map->isInMap(id))continue;Eigen::Vector3d center;map->indexToPos(id,center);\n"
      "      const int address=map->toAddress(id);\n"
      "      dump<<x<<\",\"<<y<<\",\"<<z<<\",\"<<center.x()<<\",\"<<center.y()<<\",\"<<center.z()<<\",\"\n"
      "          <<map->md_.occupancy_buffer_[address]<<\",\"<<int(map->md_.occupancy_buffer_inflate_[address])<<\"\\n\";}\n"
      "    std::cout<<std::setprecision(9)<<\"[VOXEL-DUMP] clamp_min_log=\"<<map->mp_.clamp_min_log_<<\" min_occupancy_log=\"<<map->mp_.min_occupancy_log_\n"
      "             <<\" resolution=\"<<map->mp_.resolution_<<\" body_q=\"<<map->reactive_body_quaternion_.coeffs().transpose()\n"
      "             <<\" body=\"<<map->md_.sliding_map_frame_pos_.transpose()<<\" sensor=\"<<map->md_.ray_pos_.transpose()<<std::endl;\n"
      "  }\n"))

after = {str(p.relative_to(HERE)): sha(p) for p in sorted((WORKSPACE / "src").rglob("*")) if p.is_file()}
after.update({str(p.relative_to(HERE)): sha(p) for p in sorted(PROBE.rglob("*")) if p.is_file()})
changed = sorted(name for name in after if before.get(name) != after[name])
(HERE / "diagnostic_source.json").write_text(json.dumps({
    "parent_tree": "audits/2026-09-28_v28_start_thrash/point_waiver_probe/workspace "
                   "(v28 with the known-footprint waiver evaluated at the queried point)",
    "parent_waiver_file_sha256": EXPECTED,
    "changed_or_added": {name: {"before": before.get(name), "after": after[name]} for name in changed},
    "scope": "Adds VLA_TRACE-gated stderr tracing and a read-only voxel dump; planner decisions unchanged. "
             "Diagnostic only, not a version and not for production."}, indent=2) + "\n")
print(json.dumps({"changed_or_added": changed}, indent=2))
