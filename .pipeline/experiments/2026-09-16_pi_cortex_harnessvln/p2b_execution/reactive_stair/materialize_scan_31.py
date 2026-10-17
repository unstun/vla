"""Preserve exact control-polygon endpoints in collision-repair searches."""
import json
from pathlib import Path
import shutil

from materialize_scan_20 import once, sha

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "builds/scan_30"
OUT = HERE.parent / "builds/scan_31"


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    expected = json.loads((BASE / "source_sha256.json").read_text())
    actual = {"src/" + p.relative_to(BASE / "src").as_posix(): sha(p)
              for p in (BASE / "src").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    if actual != expected or not json.loads((BASE / "build_result.json").read_text())["passed"]:
        raise ValueError("scan30 source/build identity gate failed")
    shutil.copytree(BASE / "src", OUT / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    source = OUT / "src/bspline_opt/src/bspline_optimizer.cpp"
    first = '''      Eigen::Vector3d in(init_points.col(segment_ids[i].first)), out(init_points.col(segment_ids[i].second));
      ASTAR_RET ret = a_star_->AstarSearch(grid_map_->getResolution(), in, out);'''
    once(source, first, '''      Eigen::Vector3d in(init_points.col(segment_ids[i].first)), out(init_points.col(segment_ids[i].second));
      // Actual collision retries keep the original control-polygon endpoints.
      // Initial proxy guidance retains its existing behavior in this repair.
      ASTAR_RET ret = a_star_->AstarSearch(grid_map_->getResolution(), in, out, !flag_first_init);''')
    second = '''        Eigen::Vector3d in(cps_.points.col(segment_ids[i].first)), out(cps_.points.col(segment_ids[i].second));
        ASTAR_RET ret = a_star_->AstarSearch(grid_map_->getResolution(), in, out);'''
    once(source, second, '''        Eigen::Vector3d in(cps_.points.col(segment_ids[i].first)), out(cps_.points.col(segment_ids[i].second));
        // Rebound and merged-segment repairs use checked exact terminal edges.
        ASTAR_RET ret = a_star_->AstarSearch(grid_map_->getResolution(), in, out, true);''')
    (OUT / "exact_repair_endpoints_manifest.json").write_text(json.dumps({
        "base": BASE.name, "base_manifest_sha256": sha(BASE / "source_sha256.json"),
        "changed_sha256": {str(source.relative_to(OUT)): sha(source)}, "generator_sha256": sha(Path(__file__)),
        "change": "Only actual collision-repair searches opt into existing strict endpoint AStar: initControlPoints(false), and check_collision_and_rebound including merged-segment retry. Initial proxy initControlPoints(true) stays in default mode.",
        "preserved": "No control endpoint overwrite, constraint assignment/validity/objectives/gradients/weights/retry limits, all occupancy/support/Unknown/height rules, original AStar budget and complete curve gates.",
        "boundary": "Repair endpoints still come from control-polygon segmentation, not sampled curve-pose windows. A checked strict route does not itself prove useful constraints, accepted curve or live motion."
    }, indent=2) + "\n")
    print(OUT)


if __name__ == "__main__":
    main()
