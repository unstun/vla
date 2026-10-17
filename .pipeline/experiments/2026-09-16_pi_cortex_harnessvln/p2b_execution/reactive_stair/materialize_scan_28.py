"""Initialize a dynamically bounded cubic with hard boundary PVA before rebound."""
import json
from pathlib import Path
import shutil
from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_27"
OUT = HERE.parent / "builds/scan_28"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((BASE / "build_result.json").read_text())["passed"]:
        raise ValueError("scan_27 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    helper = OUT / "src/bspline_opt/include/bspline_opt/timed_cubic_initialization.h"
    shutil.copy2(HERE / helper.name, helper)
    manager = OUT / "src/plan_manage/src/planner_manager.cpp"
    manager.write_bytes(b'#include <bspline_opt/timed_cubic_initialization.h>\n' + manager.read_bytes())
    once(manager, "    UniformBspline::parameterizeToBspline(ts, point_set, start_end_derivatives, ctrl_pts);", '''    const double seed_interval = ts;
    auto timed = reactive_stair::initializeTimedCubic(point_set, start_end_derivatives, ts,
        pp_.max_vel_, pp_.max_acc_, pp_.feasibility_tolerance_);
    if (!timed.ready()) {
      RCLCPP_WARN(node_->get_logger(), "timed_cubic_initialization_failed status=%d iterations=%zu",
                  static_cast<int>(timed.status), timed.iterations);
      continuous_failures_count_++;
      return false;
    }
    ts = timed.interval_s;
    ctrl_pts = std::move(timed.controls);
    RCLCPP_INFO(node_->get_logger(), "timed_cubic_initialized samples=%zu iterations=%zu interval=%.12f duration=%.12f scale=%.12f",
                point_set.size(), timed.iterations, ts, ts * (point_set.size() - 1), ts / seed_interval);''')
    once(manager, "    if (!flag_step_2_success || !checkDynamicFeasibility(pos))", '''    // A later native soft refit may change PVA. Reject that drift rather than
    // claiming initialization constraints survived a subsequent retiming.
    if (flag_step_2_success && !reactive_stair::matchesBoundaryPva(
        pos, start_pt, local_target_pt, start_end_derivatives)) {
      RCLCPP_WARN(node_->get_logger(), "final_spline_boundary_pva_rejected");
      flag_step_2_success = false;
    }
    if (!flag_step_2_success || !checkDynamicFeasibility(pos))''')
    (OUT / "timed_initialization_manifest.json").write_text(json.dumps({
        "base": "scan_27", "base_manifest_sha256": sha(BASE / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(OUT)):sha(p) for p in (helper,manager)},
        "generator_sha256":sha(Path(__file__)), "helper_sha256":sha(HERE/helper.name),
        "change":"Hard first/last PVA controls and internal position fit. At most eight initial refits with original PVA and native-derived increased interval before rebound. Final boundary residual rejection covers any later native soft refit.",
        "preserved":"Original measured/target PVA values, optimizer/costs, controller .8s heading, AStar, geometry samples, native limits, full sampled collision gate and Unknown blocking.",
        "boundary":"No initial curve fallback. Final PVA guard can reject native refinement; the refinement algorithm itself is unchanged. CPU timing/geometry results do not validate pose tracking or live execution."},indent=2)+"\n")
    print(OUT)


if __name__ == "__main__":
    main()
