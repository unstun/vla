"""Feed measured fixture clouds to the built native map and search probe."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

from materialize import BASE


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--probe-source", type=Path,
                        help="Build only the diagnostic probe against the unchanged qualified native libraries")
    parser.add_argument("--planner-config", type=Path, default=BASE / "config_archived/planner.yaml")
    parser.add_argument("--cases", nargs="+", default=["empty", "static_human", "box", "thin_wall", "post", "low_box", "occluded_human", "blocked_corridor"])
    args = parser.parse_args()
    out = Path(os.environ["NEWTON_RUN_DIR"])
    build, source = args.build.resolve(), args.source.resolve()
    evidence = json.loads((build / "build_result.json").read_text())
    if not evidence["passed"]:
        raise ValueError("Build not qualified")
    for name in ("source_sha256.json", "install_sha256.json"):
        for path, expected in json.loads((build / name).read_text()).items():
            if hashlib.sha256((build / path).read_bytes()).hexdigest() != expected:
                raise ValueError("Build bytes changed: " + path)
    records = json.loads((source / "result.json").read_text())["cases"]
    by_name = {row["case"]: row for row in records}
    lines = ["set -e", "source /opt/ros/humble/setup.bash", "source /workspace/install/setup.bash"]
    executable = ["ros2", "run", "geometry_probe", "measured_cloud_probe"]
    if args.probe_source:
        shutil.copytree(args.probe_source, out / "probe_source")
        lines += [shlex.join(["cmake", "-S", str(out / "probe_source"), "-B", str(out / "probe_build"),
                             "-DCMAKE_BUILD_TYPE=Release"]),
                  shlex.join(["cmake", "--build", str(out / "probe_build"), "-j2"])]
        executable = [str(out / "probe_build/measured_cloud_probe")]
    for name in args.cases:
        row = by_name[name]
        for file, expected in row["sha256"].items():
            if hashlib.sha256((source / name / file).read_bytes()).hexdigest() != expected:
                raise ValueError("Sensor input changed")
        command = ["env", "VLA_GEOMETRY_INPUT=" + str(source / name), "VLA_GEOMETRY_OUTPUT=" + str(out / (name + ".json")),
                   "VLA_QUERY_DIAGNOSTICS=1", *executable, "--ros-args", "--params-file", str(args.planner_config.resolve())]
        lines.append(" ".join(shlex.quote(word) for word in command) + " > " + shlex.quote(str(out / (name + ".log"))) + " 2>&1")
    (out / "inside.sh").write_text("\n".join(lines) + "\n")
    name = "vla-" + out.name.replace("_", "-")
    command = ["docker", "run", "--rm", "--pull=never", "--platform=linux/amd64", "--network=none",
        "--cpus=2", "--memory=4g", "--name", name, "-e", "ROS_DOMAIN_ID=217", "-e", "ROS_LOCALHOST_ONLY=1",
        "-v", str(BASE) + ":" + str(BASE) + ":ro", "-v", str(out) + ":" + str(out) + ":rw",
        "-v", str(build) + ":/workspace:ro", "--entrypoint", "/bin/bash", evidence["image"], str(out / "inside.sh")]
    (out / "native_request.json").write_text(json.dumps({"command": command, "cases": args.cases,
        "build": str(build), "sensor_source": str(source), "semantic_input_messages": 0,
        "planner_config": str(args.planner_config.resolve()),
        "planner_config_sha256": hashlib.sha256(args.planner_config.read_bytes()).hexdigest()}, indent=2) + "\n")
    if args.probe_source:
        records = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (out / "probe_source").rglob("*") if p.is_file()}
        (out / "probe_source_sha256.json").write_text(json.dumps(records, indent=2) + "\n")
    try:
        with (out / "native.log").open("w") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=240)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15)
    results = {name: json.loads((out / (name + ".json")).read_text()) for name in args.cases}
    (out / "result.json").write_text(json.dumps({"cases": results,
        "claim": "Actual native map and AStar with first-hit sensor data and no semantic messages. Requires separate case review; process completion alone is not acceptance."}, indent=2) + "\n")
    print(json.dumps({name: {"queries": row["queries"], "search_status": row["search_status"], "path_points": len(row["path"])} for name, row in results.items()}, indent=2))


if __name__ == "__main__":
    main()
