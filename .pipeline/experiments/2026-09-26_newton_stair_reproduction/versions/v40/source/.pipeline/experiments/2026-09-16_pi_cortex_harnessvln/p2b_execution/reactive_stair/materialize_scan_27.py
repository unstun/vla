"""Fail closed on empty rebound and commit only this-point valid constraints."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_26"
OUT = HERE.parent / "builds/scan_27"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((BASE / "build_result.json").read_text())["passed"]:
        raise ValueError("scan_26 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    helper = OUT / "src/bspline_opt/include/bspline_opt/rebound_constraint_utils.h"
    shutil.copy2(HERE / helper.name, helper)
    source = OUT / "src/bspline_opt/src/bspline_optimizer.cpp"
    source.write_bytes(b'#include <bspline_opt/rebound_constraint_utils.h>\n' + source.read_bytes())
    for indent, rebound in (("        ", False), ("          ", True)):
        declaration = indent + "Eigen::Vector3d ctrl_pts_law(cps_.points.col(j + 1) - cps_.points.col(j - 1)), intersection_point;"
        once(source, "\n" + declaration, "\n" + declaration[:-1] + " = Eigen::Vector3d::Zero();\n" + indent + "bool found_intersection = false;")
        once(source, "\n" + indent + "    got_intersection_id = j;",
             "\n" + indent + "    found_intersection = intersection_point.allFinite();")
        before = (indent + "if (got_intersection_id >= 0)\n" + indent + "{\n" +
                  indent + "  cps_.flag_temp[j] = true;\n" +
                  indent + "  double length = (intersection_point - cps_.points.col(j)).norm();\n" +
                  indent + "  if (length > 1e-5)")
        after = (indent + "if (found_intersection)\n" + indent + "{\n" +
                 indent + "  double length = (intersection_point - cps_.points.col(j)).norm();\n" +
                 indent + "  if (std::isfinite(length) && length > 1e-5)")
        once(source, "\n" + before, "\n" + after)
        push_indent = indent + "        "
        before = (push_indent + "cps_.base_point[j].push_back((a / length) * intersection_point + (1 - a / length) * cps_.points.col(j));\n" +
                  push_indent + "cps_.direction[j].push_back((intersection_point - cps_.points.col(j)).normalized());")
        after = (push_indent + "if (reactive_stair::appendReboundConstraint(cps_, j,\n" +
                 push_indent + "    (a / length) * intersection_point + (1 - a / length) * cps_.points.col(j),\n" +
                 push_indent + "    (intersection_point - cps_.points.col(j)).normalized())) {\n" +
                 push_indent + "  got_intersection_id = j;\n" +
                 (push_indent + "  ++committed_pairs;\n" if rebound else "") + push_indent + "}")
        once(source, "\n" + before, "\n" + after)
    # A later missing/zero intersection must not erase an earlier valid seed.
    once(source, "\n            else\n            {\n              got_intersection_id = -1;\n            }", "")
    once(source, '''              cps_.flag_temp[segment_ids[i].first] = true;
              cps_.base_point[segment_ids[i].first].push_back(cps_.points.col(segment_ids[i].first));
              cps_.direction[segment_ids[i].first].push_back((intersection_point - middle_point).normalized());

              got_intersection_id = segment_ids[i].first;''', '''              if (reactive_stair::appendReboundConstraint(cps_, segment_ids[i].first,
                  cps_.points.col(segment_ids[i].first), (intersection_point - middle_point).normalized())) {
                got_intersection_id = segment_ids[i].first;
              }''')
    for indent, rebound in (("            ", False), ("              ", True)):
        for neighbor in ("j - 1", "j + 1"):
            before = (indent + f"cps_.base_point[j].push_back(cps_.base_point[{neighbor}].back());\n" +
                      indent + f"cps_.direction[j].push_back(cps_.direction[{neighbor}].back());")
            after = indent + (f"if (reactive_stair::copyReboundConstraint(cps_, j, {neighbor})) ++committed_pairs;"
                              if rebound else f"reactive_stair::copyReboundConstraint(cps_, j, {neighbor});")
            once(source, "\n" + before, "\n" + after)
    once(source, "    if (flag_new_obs_valid)\n    {\n      vector<vector<Eigen::Vector3d>> a_star_paths;", '''    if (flag_new_obs_valid)
    {
      size_t committed_pairs = 0;
      vector<vector<Eigen::Vector3d>> a_star_paths;''')
    once(source, "      force_stop_type_ = STOP_FOR_REBOUND;\n      return true;", '''      if (committed_pairs == 0) {
        // The caller ignores this bool and earlyExit reads force_stop_type_.
        // A failed repair must terminate this solve, never request an empty rebound.
        force_stop_type_ = STOP_FOR_ERROR;
        RCLCPP_WARN(rclcpp::get_logger("bspline_opt"), "rebound_no_valid_new_constraints; aborting this optimization");
        return false;
      }
      force_stop_type_ = STOP_FOR_REBOUND;
      return true;''')
    (OUT / "rebound_validity_manifest.json").write_text(json.dumps({
        "base": "scan_26", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(OUT)): sha(p) for p in (helper, source)},
        "generator_sha256": sha(Path(__file__)), "helper_sha256": sha(HERE / helper.name),
        "change": "Per-point intersection validity; finite normalized base/direction pair committed before temporary flag; propagation from a fresh valid pair; new collision without any committed pair sets STOP_FOR_ERROR in the actual rebound callback.",
        "preserved": "Existing intersection search, tiny-length thresholds, AStar modes and result selection, cost weights, collision/Unknown/terrain/height/dynamic rules and final spline gate.",
        "boundary": "Constraint validity and finite failure semantics only. Does not establish a usable repair route, safe cubic or navigation success."}, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
