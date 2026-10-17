"""Pair actual recorded clouds/poses for a native-map diagnostic; no scene truth."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import pickle
import sys

import numpy as np
from materialize import BASE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pose(path, position, quaternion):
    # Recorded quaternions are WXYZ; native pose fixture uses XYZW.
    values = [*position, *quaternion[1:], quaternion[0]]
    path.write_text(" ".join(format(x, ".17g") for x in values) + "\n")


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    spec = importlib.util.spec_from_file_location("recorded_pct_core", BASE / "references/pct_sim_clock_core.py")
    core = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = core
    spec.loader.exec_module(core)
    records = []
    # Cutoffs are diagnostics at recorded poses, not alternative navigation goals.
    for run_id, seconds in (("flat_static_human_live_v4", 10.),
                            ("flat_static_human_live_v5", 10.),
                            ("flat_static_human_live_v5", 12.),
                            ("flat_box_live_v1", 5.5)):
        run = BASE / "runs" / run_id
        name = f"{run_id}_{seconds:g}s"
        case = out / name
        case.mkdir()
        manifest = json.loads((run / "sensor_manifest.json").read_text())
        selected = [r for r in manifest if r["sim_time_s"] <= seconds + .001]
        if not selected:
            raise ValueError("No measured scans")
        with (run / "inputs/flat_floor.pickle").open("rb") as stream:
            ground = core.selected_ground_points(pickle.load(stream))
        np.asarray(ground, dtype="<f4").tofile(case / "ground.f32")
        files, paired = [], []
        for index, row in enumerate(selected):
            source = run / row["file"]
            if sha(source) != row["sha256"]:
                raise ValueError("Recorded cloud changed")
            name_cloud = f"cloud_{index:04d}.f32"
            with np.load(source) as data:
                np.asarray(data["sensor_points"], dtype="<f4").tofile(case / name_cloud)
            b = row["body_sensor"]
            body_file, sensor_file = f"body_{index:04d}.txt", f"sensor_{index:04d}.txt"
            pose(case / body_file, b["position"], b["quaternion"])
            pose(case / sensor_file, b["sensor_position"], b["sensor_quaternion"])
            files.append(name_cloud)
            paired.append(f'{row["stamp_ns"] + 1_000_000_000} {body_file} {sensor_file}')
        first, last = selected[0]["body_sensor"], selected[-1]["body_sensor"]
        pose(case / "body_pose.txt", first["position"], first["quaternion"])
        pose(case / "sensor_pose.txt", first["sensor_position"], first["sensor_quaternion"])
        (case / "clouds.txt").write_text("\n".join(files) + "\n")
        (case / "poses.txt").write_text("\n".join(paired) + "\n")
        start = last["position"]
        w, x, y, z = last["quaternion"]
        yaw = math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))
        queries = []
        for dx in (0., -.15, -.3):
            for direction in (yaw, math.pi/2, -math.pi/2):
                label = f"body_dx{dx:g}_yaw{direction:.4f}"
                queries.append(" ".join(format(v, ".17g") for v in (start[0]+dx, *start[1:], direction)) + " " + label)
        (case / "queries.txt").write_text("\n".join(queries) + "\n")
        (case / "start_goal.txt").write_text(" ".join(format(v, ".17g") for v in (*start, 3., 0., .3)) + "\n")
        records.append({"case": name, "source_run": run_id, "cutoff_s": seconds,
                        "actual_last_stamp_ns": selected[-1]["stamp_ns"],
                        "body_position": start,
                        "source_manifest_sha256": sha(run / "sensor_manifest.json"),
                        "sha256": {p.name: sha(p) for p in case.iterdir() if p.is_file()}})
    (out / "result.json").write_text(json.dumps({"cases": records,
        "timestamp_translation_ns": 1_000_000_000,
        "claim": "Measured-cloud native-map diagnostic at actual poses. Query offsets are scoring controls only; not navigation input or physical reruns."}, indent=2) + "\n")
    print(json.dumps({"cases": [r["case"] for r in records]}))


if __name__ == "__main__":
    main()
