"""Inspect the actual returned trial after native empty-rebound failure."""
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
P2B = HERE.parents[6] / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
sys.path.insert(0, str(P2B / "reactive_stair"))
from materialize_scan_20 import once, sha


def main():
    base = P2B / "builds/scan_31"
    out = P2B / "builds/scan31_returned_curve_probe"
    if out.exists():
        raise FileExistsError(out)
    expected = json.loads((base / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(base / "src").as_posix(): sha(p)
              for p in (base / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((base / "build_result.json").read_text())["passed"]:
        raise ValueError("scan31 identity gate failed")
    shutil.copytree(base / "src", out / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manager = out / "src/plan_manage/src/planner_manager.cpp"
    optimizer = out / "src/bspline_opt/src/bspline_optimizer.cpp"
    helper = out / "src/plan_manage/include/plan_manage/curve_rejection_probe.inc"
    shutil.copy2(HERE / helper.name, helper)
    once(manager, "    ctrl_pts = std::move(timed.controls);", '''    ctrl_pts = std::move(timed.controls);
    const Eigen::MatrixXd rejection_initial_controls = ctrl_pts;
    const double rejection_initial_interval = ts;''')
    once(manager, "    if (!flag_step_1_success)\n    {", '''    if (!flag_step_1_success)
    {
      { // Actual returned cps_, which can be the last canceled solver trial.
        UniformBspline pos(ctrl_pts, 3, ts);
#include <plan_manage/curve_rejection_probe.inc>
      }''')
    once(optimizer, '''        force_stop_type_ = STOP_FOR_ERROR;
        RCLCPP_WARN(rclcpp::get_logger("bspline_opt"), "rebound_no_valid_new_constraints; aborting this optimization");''', '''        force_stop_type_ = STOP_FOR_ERROR;
        static bool zero_rebound_captured = false;
        if (!zero_rebound_captured) {
          zero_rebound_captured = true;
          // Snapshot output only, after the original stop decision. No new
          // occupancy query, search, constraint or change to the stop state.
          for (int j = 0; j < cps_.points.cols(); ++j)
            RCLCPP_WARN(rclcpp::get_logger("bspline_opt"), "ZERO_CONTROL,%d,%.17g,%.17g,%.17g,%d,%zu,%zu",
                j, cps_.points(0,j), cps_.points(1,j), cps_.points(2,j), static_cast<int>(cps_.flag_temp[j]),
                cps_.base_point[j].size(), cps_.direction[j].size());
          for (size_t j = 0; j < segment_ids.size(); ++j)
            RCLCPP_WARN(rclcpp::get_logger("bspline_opt"), "ZERO_SEGMENT,%zu,%d,%d", j, segment_ids[j].first, segment_ids[j].second);
          for (size_t j = 0; j < a_star_paths.size(); ++j)
            for (size_t k = 0; k < a_star_paths[j].size(); ++k)
              RCLCPP_WARN(rclcpp::get_logger("bspline_opt"), "ZERO_PATH,%zu,%zu,%.17g,%.17g,%.17g",
                  j, k, a_star_paths[j][k].x(), a_star_paths[j][k].y(), a_star_paths[j][k].z());
        }
        RCLCPP_WARN(rclcpp::get_logger("bspline_opt"), "rebound_no_valid_new_constraints; aborting this optimization");''')
    (out / "returned_curve_probe_manifest.json").write_text(json.dumps({
        "base": base.name, "base_manifest_sha256": sha(base / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(out)): sha(p) for p in (manager, optimizer, helper)},
        "generator_sha256": sha(Path(__file__)), "helper_sha256": sha(HERE / helper.name),
        "claim": "After first zero-new-constraint stop decision, dump current controls/flags/pair counts and failed segments/paths without new queries. After original optimizer false, inspect actual returned trial and timed initialization using original full checker and same-time paired footprint queries. Preserve stop/failure and publication behavior.",
        "boundary": "Returned cps may differ from LBFGS internally rolled-back q and is not called a solver-accepted solution. Verify dumped stop-state vs returned controls component equality. Extra diagnostics are not timing evidence."
    }, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()
