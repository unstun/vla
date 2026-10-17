"""Recover missing rebound planes with individually checked route projections."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_31"
OUT = HERE.parent / "builds/scan_32"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((BASE / "build_result.json").read_text())["passed"]:
        raise ValueError("scan31 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    source = OUT / "src/bspline_opt/src/bspline_optimizer.cpp"
    helper = OUT / "src/bspline_opt/include/bspline_opt/rebound_constraint_utils.h"
    shutil.copy2(HERE / helper.name, helper)
    text = source.read_text()
    start = text.index("  bool BsplineOptimizer::check_collision_and_rebound(void)")
    end = text.index("  bool BsplineOptimizer::BsplineOptimizeTrajRebound", start)
    before = text[start:end]
    after = before.replace("        int got_intersection_id = -1;", "        int got_intersection_id = -1;\n        bool segment_has_geometric_intersection = false;")
    assert after != before
    old = "          if (found_intersection)\n          {"
    assert after.count(old) == 1
    after = after.replace(old, old + "\n            segment_has_geometric_intersection = true;")
    old = "        //step 3\n        if (got_intersection_id >= 0)"
    assert after.count(old) == 1
    fallback = '''        if (!segment_has_geometric_intersection && cps_.points.allFinite()) {
          size_t projection_clear = 0, projection_added = 0;
          for (int j = segment_ids[i].first + 1; j < segment_ids[i].second; ++j) {
            Eigen::Vector3d target;
            if (!reactive_stair::nearestPointOnMatchingRoute(a_star_paths[i],
                cps_.points.col(segment_ids[i].first), cps_.points.col(segment_ids[i].second),
                cps_.points.col(j), target)) continue;
            const double yaw = estimateControlPointYaw(cps_.points, j);
            if (!std::isfinite(yaw) || grid_map_->getInflateOccupancy(target, yaw) != 0) continue;
            ++projection_clear;
            const double length = (target - cps_.points.col(j)).norm();
            // Same base-point ray, clearance cost and paired normalized write
            // as the ordinary intersection branch. No direct control rewrite.
            for (double a = length; a >= 0.0; a -= grid_map_->getResolution()) {
              const Eigen::Vector3d sample = (a / length) * target + (1 - a / length) * cps_.points.col(j);
              const bool occupied = grid_map_->getInflateOccupancy(sample, yaw) != 0;
              if (occupied || a < grid_map_->getResolution()) {
                if (occupied) a += grid_map_->getResolution();
                if (reactive_stair::appendReboundConstraint(cps_, j,
                    (a / length) * target + (1 - a / length) * cps_.points.col(j),
                    (target - cps_.points.col(j)).normalized())) {
                  got_intersection_id = j;
                  ++committed_pairs;
                  ++projection_added;
                }
                break;
              }
            }
          }
          RCLCPP_INFO(rclcpp::get_logger("bspline_opt"),
                      "rebound_route_projection begin=%d end=%d clear_targets=%zu committed_pairs=%zu",
                      segment_ids[i].first, segment_ids[i].second, projection_clear, projection_added);
        }

        // Only ordinary plane constraints keep the original propagation.
        // Projection candidates are checked per control; do not copy one to
        // another control whose own target/heading was rejected.
        //step 3
        if (got_intersection_id >= 0 && segment_has_geometric_intersection)'''
    after = after.replace(old, fallback)
    old = '        else\n          RCLCPP_WARN(rclcpp::get_logger("bspline_opt"), "Failed to generate rebound direction");'
    assert after.count(old) == 1
    after = after.replace(old, '        else if (got_intersection_id < 0)\n          RCLCPP_WARN(rclcpp::get_logger("bspline_opt"), "Failed to generate rebound direction");')
    once(source, before, after)
    (OUT / "route_projection_manifest.json").write_text(json.dumps({
        "base": BASE.name, "base_manifest_sha256": sha(BASE / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (source, helper)},
        "generator_sha256": sha(Path(__file__)), "helper_sha256": sha(HERE / helper.name),
        "change": "Only when the original plane search finds no finite intersection anywhere in a rebound repair segment may that segment use per-control nearest points on its exact-endpoint strict route. Candidate must be clear under that control heading; reuse original base-point ray and guarded write, without propagation to unchecked controls. The original plane finder is not an exhaustive intersection enumerator.",
        "preserved": "Initial guidance, existing plane cases/propagation, original clearance/objective/gradients/weights, zero/finite/direction validity, strict search and retry limits, map/Unknown/height predicates and complete curve/PVA/dynamic gates.",
        "boundary": "Constraint-generation hypothesis for a folded control polygon. Clearance cost can push beyond the projection; neither a clear anchor nor committed pairs establishes a clear final curve or live feasibility."
    }, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
