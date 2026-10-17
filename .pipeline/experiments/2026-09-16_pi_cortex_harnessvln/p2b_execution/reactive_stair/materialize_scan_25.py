"""Make the manager seed terminate at a collision-checked exact endpoint."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_24"
OUT = HERE.parent / "builds/scan_25"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((BASE / "build_result.json").read_text())["passed"]:
        raise ValueError("scan_24 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    header = OUT / "src/path_searching/include/path_searching/dyn_a_star.h"
    source = OUT / "src/path_searching/src/dyn_a_star.cpp"
    manager = OUT / "src/plan_manage/src/planner_manager.cpp"
    once(header, "\tstd::vector<GridNodePtr> gridPath_;", '''\tstd::vector<GridNodePtr> gridPath_;
    bool has_exact_goal_{false};
    Eigen::Vector3d exact_goal_{Eigen::Vector3d::Zero()};''')
    once(header, "\tASTAR_RET AstarSearch(const double step_size, Eigen::Vector3d start_pt, Eigen::Vector3d end_pt);", '''    // Exact mode preserves the requested endpoints and checks a terminal edge
    // from a popped lattice node within two cells (3D Euclidean distance).
    // The default keeps the optimizer's existing adjusted-endpoint behavior.
    ASTAR_RET AstarSearch(const double step_size, Eigen::Vector3d start_pt,
                         Eigen::Vector3d end_pt, bool exact_endpoint = false);''')
    once(source, "ASTAR_RET AStar::AstarSearch(const double step_size, Vector3d start_pt, Vector3d end_pt)",
         "ASTAR_RET AStar::AstarSearch(const double step_size, Vector3d start_pt, Vector3d end_pt, bool exact_endpoint)")
    once(source, "    ++rounds_;", '''    // Clear result state even when initialization fails or modes are switched.
    gridPath_.clear();
    has_exact_goal_ = false;
    if (!std::isfinite(step_size) || step_size <= 0.0 ||
        !std::isfinite(1.0 / step_size) || !start_pt.allFinite() || !end_pt.allFinite())
      return ASTAR_RET::INIT_ERR;
    const Eigen::Vector3d search_span = (end_pt - start_pt) / step_size;
    if (!search_span.allFinite() || search_span.cwiseAbs().maxCoeff() > std::numeric_limits<int>::max() / 4.0)
      return ASTAR_RET::INIT_ERR;
    ++rounds_;''')
    once(source, "    if (!ConvertToIndexAndAdjustStartEndPoints(start_pt, end_pt, start_idx, end_idx))", '''    const bool endpoints_valid = exact_endpoint
        ? (Coord2Index(start_pt, start_idx) && Coord2Index(end_pt, end_idx) &&
           (Index2Coord(start_idx) - start_pt).norm() <= 1e-6)
        : ConvertToIndexAndAdjustStartEndPoints(start_pt, end_pt, start_idx, end_idx);
    if (!endpoints_valid)''')
    once(source, "        if (current->index(0) == endPtr->index(0) && current->index(1) == endPtr->index(1) && current->index(2) == endPtr->index(2))", '''        if (exact_endpoint && (Index2Coord(current->index) - end_pt).norm() <= 2.0 * step_size_)
        {
            // This is an explicit additional terminal edge, checked with the
            // same heading, endpoint and half-voxel rules as every grid edge.
            const bool terminal_clear = grid_map_->collisionFreeSegment(Index2Coord(current->index), end_pt);
            if (std::chrono::duration<double>(std::chrono::steady_clock::now() - time_1).count() > 0.2)
            {
                RCLCPP_WARN(rclcpp::get_logger("path_searching"),
                            "Failed in A-star path search: 0.2 second time limit exceeded during exact endpoint check");
                return ASTAR_RET::SEARCH_ERR;
            }
            if (terminal_clear)
            {
                gridPath_ = retrievePath(current);
                exact_goal_ = end_pt;
                has_exact_goal_ = true;
                return ASTAR_RET::SUCCESS;
            }
            // A rejected connector, including one at the snapped goal node,
            // does not finish the search. Other approach directions can work.
        }
        if (!exact_endpoint && current->index(0) == endPtr->index(0) && current->index(1) == endPtr->index(1) && current->index(2) == endPtr->index(2))''')
    once(source, "    reverse(path.begin(), path.end());", '''    reverse(path.begin(), path.end());
    if (has_exact_goal_ && !path.empty() && (path.back() - exact_goal_).squaredNorm() > 0.0)
      path.push_back(exact_goal_);''')
    once(manager, "seed_search->AstarSearch(grid_map_->getResolution(), start_pt, local_target_pt)",
         "seed_search->AstarSearch(grid_map_->getResolution(), start_pt, local_target_pt, true)")
    once(manager, "(seed_path.back() - local_target_pt).norm() > grid_map_->getResolution()", "(seed_path.back() - local_target_pt).norm() > 1e-6")
    once(manager, "    seed_path.front() = start_pt;\n    seed_path.back() = local_target_pt;", '''    // Search already checked the exact terminal connection. Do not overwrite
    // endpoints here: changing the last edge can change its footprint heading.''')
    (OUT / "exact_endpoint_manifest.json").write_text(json.dumps({
        "base": "scan_24", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (header, source, manager)},
        "generator_sha256": sha(Path(__file__)),
        "change": "Manager opts into strict exact-endpoint search with a fully checked terminal edge from a popped node within two grid steps; rejected connectors continue search. No post-search endpoint overwrite.",
        "preserved": "Default optimizer AStar endpoint adjustment, ordinary grid edges, occupancy/support/person/Unknown thresholds, .2s search budget, complete seed edge recheck and final spline gate.",
        "boundary": "Additional finite terminal edges are explicit, not threshold relaxation. Heuristic still targets snapped grid index; no shortest-path or continuous rotating-footprint guarantee. Runtime cause attribution awaits diagnostic replay."}, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
