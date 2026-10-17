"""Compose immutable measured sweeps for detour and ray-clearing regressions."""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil

from materialize import BASE


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    source = BASE / "runs/generic_sensor_cases_v1"
    cases = {
        "empty_control": (["empty"], .5),
        "static_human_detour": (["static_human"], .5),
        "post_detour": (["post"], .35),
        "low_box_detour": (["low_box"], .5),
        "box_detour": (["box"], 1.),
        "thin_wall_detour": (["thin_wall"], 1.5),
        "human_partial": (["static_human", "occluded_human"], .5),
        "box_removed": (["box", "empty"], 0.),
        "low_box_removed": (["low_box", "empty"], 0.),
        "blocked_corridor": (["blocked_corridor"], 1.5),
    }
    manifest = []
    for name, (phases, goal_y) in cases.items():
        target = out / name
        target.mkdir()
        for file in ("body_pose.txt", "sensor_pose.txt", "ground.f32"):
            shutil.copyfile(source / phases[0] / file, target / file)
        names, provenance = [], []
        for phase in phases:
            for file in (source / phase / "clouds.txt").read_text().splitlines():
                new_name = f"cloud_{len(names):03d}.f32"
                shutil.copyfile(source / phase / file, target / new_name)
                names.append(new_name)
                provenance.append({"file": new_name, "source": str((source / phase / file).relative_to(BASE))})
        (target / "clouds.txt").write_text("\n".join(names) + "\n")
        (target / "start_goal.txt").write_text(f"0 0 0.3 3 {goal_y} 0.3\n")
        queries = ["0 0 0.3 0 start", "1.6 0 0.3 0 obstacle_center", f"3 {goal_y} 0.3 0 goal", "4.8 4.8 0.3 0 unknown_corner"]
        for i in range(81):
            u = i / 80
            queries.append(f"{3*u:.12f} {goal_y*u:.12f} 0.3 {math.atan2(goal_y,3):.12f} direct_{i:03d}")
        (target / "queries.txt").write_text("\n".join(queries) + "\n")
        manifest.append({"case": name, "phases": phases, "goal": [3., goal_y, .3],
                         "provenance": provenance,
                         "sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir()}})
    shutil.copyfile(__file__, out / "executed_make_temporal_cases.py")
    (out / "result.json").write_text(json.dumps({"cases": manifest,
        "claim": "Recorded-cloud regression sequences, not new physical runs. Goals are explicitly chosen test requests; they do not supply obstacle coordinates to SCAN. Query locations only score the map after sensing."}, indent=2) + "\n")
    print(json.dumps({"cases": len(manifest)}))


if __name__ == "__main__":
    main()
