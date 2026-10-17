"""Observe the first rejected full curve after the production decision only."""
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
P2B = HERE.parents[6] / ".pipeline/experiments/2026-09-16_pi_cortex_harnessvln/p2b_execution"
sys.path.insert(0, str(P2B / "reactive_stair"))
from materialize_scan_20 import once, sha


def main():
    base = P2B / "builds/scan_29"
    out = P2B / "builds/scan29_curve_rejection_probe"
    if out.exists():
        raise FileExistsError(out)
    expected = json.loads((base / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(base / "src").as_posix(): sha(p)
              for p in (base / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((base / "build_result.json").read_text())["passed"]:
        raise ValueError("scan29 identity gate failed")
    shutil.copytree(base / "src", out / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manager = out / "src/plan_manage/src/planner_manager.cpp"
    helper = out / "src/plan_manage/include/plan_manage/curve_rejection_probe.inc"
    shutil.copy2(HERE / helper.name, helper)
    once(manager, "    ctrl_pts = std::move(timed.controls);", """    ctrl_pts = std::move(timed.controls);
    const Eigen::MatrixXd rejection_initial_controls = ctrl_pts;
    const double rejection_initial_interval = ts;""")
    once(manager, "    if (!collision.clear()) {", """    if (!collision.clear()) {
#include <plan_manage/curve_rejection_probe.inc>""")
    (out / "curve_rejection_probe_manifest.json").write_text(json.dumps({
        "base": base.name, "base_source_manifest_sha256": sha(base / "source_sha256.json"),
        "changed_sha256": {str(p.relative_to(out)): sha(p) for p in (manager, helper)},
        "generator_sha256": sha(Path(__file__)), "helper_sha256": sha(HERE / helper.name),
        "claim": "After first native final-curve rejection only: compare timed initial and optimized/final curves with original full checker; paired footprint queries at first blocked point and seed projection; dump seed/samples/controls/knots. Preserve failure, no publication or thresholds changed.",
        "boundary": "Extra diagnostics affect scheduling and are not a timing benchmark. Curve body pose/clock stamps must be matched before geometric attribution. Does not change production scan29."
    }, indent=2) + "\n")
    print(out)


if __name__ == "__main__":
    main()
