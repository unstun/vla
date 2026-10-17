"""Compare failed guidance endpoints after original optimizer rejection only."""
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
P2B = HERE.parents[6] / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
sys.path.insert(0, str(P2B / "reactive_stair"))
from materialize_scan_20 import once, sha


def main():
    base = P2B / "builds/scan_30"
    out = P2B / "builds/scan30_guidance_endpoint_probe"
    if out.exists():
        raise FileExistsError(out)
    expected = json.loads((base / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(base / "src").as_posix(): sha(p)
              for p in (base / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((base / "build_result.json").read_text())["passed"]:
        raise ValueError("scan30 identity gate failed")
    shutil.copytree(base / "src", out / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    helper = out / "src/bspline_opt/include/bspline_opt/guidance_failure_probe.h"
    shutil.copy2(HERE / helper.name, helper)
    optimizer = out / "src/bspline_opt/src/bspline_optimizer.cpp"
    manager = out / "src/plan_manage/src/planner_manager.cpp"
    for p in (optimizer, manager):
        p.write_bytes(b"#include <bspline_opt/guidance_failure_probe.h>\n" + p.read_bytes())
    once(optimizer, '        RCLCPP_ERROR(rclcpp::get_logger("bspline_opt"), "A-star failed; aborting optimization");', '''        guidance_failure_probe::capture(flag_first_init, segment_ids[i].first, segment_ids[i].second,
                                        in, out, ret, init_points);
        RCLCPP_ERROR(rclcpp::get_logger("bspline_opt"), "A-star failed; aborting optimization");''')
    once(manager, "    if (!flag_step_1_success)\n    {", '''    if (!flag_step_1_success)
    {
      guidance_failure_probe::observe(grid_map_, ctrl_pts, ts);''')
    once(manager, "    a_star_paths = bspline_optimizer_rebound_->initControlPoints(ctrl_pts, true);", '''    guidance_failure_probe::beginAttempt();
    a_star_paths = bspline_optimizer_rebound_->initControlPoints(ctrl_pts, true);''')
    (out / "guidance_probe_manifest.json").write_text(json.dumps({
        "base": base.name, "base_manifest_sha256": sha(base / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(out)): sha(p) for p in (helper, optimizer, manager)},
        "generator_sha256": sha(Path(__file__)), "helper_sha256": sha(HERE / helper.name),
        "claim": "Capture first failed initial and restart guidance endpoints without extra queries. Only after original optimizer false: compare same endpoints under strict native AStar in an independent same-size pool, complete edge recheck and footprint logs; preserve original failure/publication behavior.",
        "boundary": "Copy/query/search overhead changes diagnostic timing. Match source controls and body/clock before geometric attribution. Strict diagnostic success does not establish valid rebound constraints or a passing optimized curve."
    }, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()
