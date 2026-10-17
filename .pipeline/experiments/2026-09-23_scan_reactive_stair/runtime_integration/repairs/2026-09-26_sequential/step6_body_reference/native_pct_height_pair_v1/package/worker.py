"""Generate native PCT controls at both declared heights from one measured pose."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
IMAGE = "40f0fa16091e2b6e24fd82058ceb01dbe76c001276234af0b9a44ac0e3787555"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def worker():
    root = Path("/audit")
    expected = json.loads((root / "package_manifest.json").read_text())["files"]
    assert all(sha(root / p) == h for p, h in expected.items())
    sys.path.insert(0, str(root / "backend_adapter"))
    from backend_adapter.contracts import PlannerRequest
    from backend_adapter.pct_worker import NativePctPlanner, NativePctConfig
    specs = json.loads((root / "requests.json").read_text())
    result = {"completed": False, "package_sha256": expected, "routes": []}
    for spec in specs:
        planner = NativePctPlanner(NativePctConfig(root / "pct_runtime/python", str(root / "inputs"),
                                                   tomogram_path=str(root / "inputs/new_building.pickle")),
                                   reference_height_m=spec["reference_height_m"])
        assert hasattr(planner._planner.planner, "set_reference_height")
        request = PlannerRequest.from_mapping(spec["request"])
        route = planner.plan(request)
        result["routes"].append({"reference_height_m": spec["reference_height_m"], "request": request.to_wire(),
                                "native_reference_height_setter_available": True, "route": route.to_wire()})
        print("native PCT", spec["reference_height_m"], len(route.waypoints_m), "points", flush=True)
    result["completed"] = True
    write(root / "result.json", result)


def host():
    ri = HERE.parents[2]
    source = ri / "diagnostics/2026-09-26_root_cause/search_inputs"
    prepared = ri / "runs/walk_scan24_height030_right_v1"
    out = HERE / "native_pct_height_pair_v1"
    out.mkdir(exist_ok=False)
    package = out / "package"
    package.mkdir()
    for directory in ("pct_runtime", "backend_adapter"):
        # Copy only the actual Python package for the adapter; PCT includes its
        # captured native libraries and no online dependency resolution.
        origin = prepared / directory
        if directory == "backend_adapter":
            (package / directory).mkdir()
            shutil.copytree(origin / directory, package / directory / directory,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copytree(origin, package / directory)
    (package / "inputs").mkdir()
    shutil.copy2(prepared / "inputs/new_building.pickle", package / "inputs/new_building.pickle")
    shutil.copy2(__file__, package / "worker.py")
    events = json.loads((source / "events.json").read_text())
    route_event = next(v for v in events if v["kind"] == "pct_route")
    body = [v for v in events if v["kind"] == "body" and v["stamp"] <= route_event["stamp"]][-1]
    scenario = json.loads((prepared / "inputs/stair_scenario.json").read_text())
    specs = []
    for height in (.35, .30):
        position = list(body["data"]["position"])
        position[2] -= height
        specs.append({"reference_height_m": height, "measured_body_stamp_ns": body["stamp"],
                      "measured_body_position": body["data"]["position"], "request": {
            "schema": "p2b_pct_plan_request_v1", "request_id": route_event["data"]["request_id"],
            "goal_id": route_event["data"]["goal_id"], "start_xyz_m": position,
            "target_xyz_m": scenario["goal_ground_xyz_m"], "frame_id": "world",
            "map_epoch": "stair_reactive", "map_revision": 1, "start_layer": 1, "target_layer": 1, "optimize": True}})
    write(package / "requests.json", specs)
    hashes = {str(p.relative_to(package)): sha(p) for p in package.rglob("*") if p.is_file()}
    write(package / "package_manifest.json", {"files": hashes, "source_input_manifest_sha256": sha(source / "input_manifest.json"),
          "script_sha256": sha(Path(__file__)), "claim": "Native PCT regeneration at .35/.30 reference heights from identical recorded measured body pose and unchanged ground goal. No route Z post-shift."})
    remote = "/home/sun/vla_exec/2026-09-26_stair_repairs/native_pct_height_pair_v1"
    ssh = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "gpu5070ti"]
    commands = []
    def call(label, command):
        r = subprocess.run(command, text=True, capture_output=True, timeout=150)
        (out / (label + ".log")).write_text(r.stdout + r.stderr)
        commands.append({"label": label, "command": command, "returncode": r.returncode})
        write(out / "commands.json", commands)
        print(label, r.returncode, flush=True)
        r.check_returncode()
    call("mkdir", ssh + [shlex.join(["mkdir", remote])])
    call("sync", ["rsync", "-a", str(package) + "/", "gpu5070ti:" + remote + "/"])
    inner = "set -e\nsource /opt/ros/humble/setup.bash\nexport PYTHONPATH=/audit/backend_adapter:/audit/pct_runtime/python:${PYTHONPATH:-}\nexport LD_LIBRARY_PATH=/audit/pct_runtime/lib:${LD_LIBRARY_PATH:-}\npython3 /audit/worker.py --worker"
    command = ["timeout", "--kill-after=5", "90", "podman", "run", "--rm", "--pull=never", "--network=none",
               "--name", "vla-pct-height-pair-v1", "-e", "PYTHONDONTWRITEBYTECODE=1", "-v", remote + ":/audit", IMAGE, "bash", "-lc", inner]
    call("native_pct", ssh + [shlex.join(command)])
    call("collect", ["rsync", "-a", "--include=/result.json", "--exclude=*", "gpu5070ti:" + remote + "/", str(out) + "/"])
    value = json.loads((out / "result.json").read_text())
    assert value["completed"] and value["package_sha256"] == hashes
    for row in value["routes"]:
        suffix = "035_control" if row["reference_height_m"] == .35 else "030"
        inputs = HERE / ("body_reference_" + suffix + "_inputs")
        shutil.copytree(source, inputs)
        revised_events = copy.deepcopy(events)
        revised = next(v for v in revised_events if v["kind"] == "pct_route")["data"]
        revised["route_id"] = row["route"]["route_id"]
        revised["command_id"] = hashlib.sha256(revised["route_id"].encode()).hexdigest()[:16]
        template = revised["path"]["poses"][0]
        poses = []
        for xyz in row["route"]["waypoints_m"]:
            pose = copy.deepcopy(template)
            pose["pose"]["position"] = dict(zip(("x", "y", "z"), xyz))
            poses.append(pose)
        revised["path"]["poses"] = poses
        write(inputs / "events.json", revised_events)
        config = inputs / "planner.yaml"
        text = config.read_text()
        assert text.count("grid_map.reactive_body_clearance: 0.35") == 1
        config.write_text(text.replace("grid_map.reactive_body_clearance: 0.35", "grid_map.reactive_body_clearance: " + str(row["reference_height_m"])))
        manifest = json.loads((inputs / "input_manifest.json").read_text())
        manifest.update(parent_input_manifest_sha256=sha(source / "input_manifest.json"), native_pct_result_sha256=sha(out / "result.json"),
                        reference_height_m=row["reference_height_m"], measured_start=body,
                        claim="Captured actual sensors/poses/tracks unchanged. Native regenerated PCT route plus matching physical-reference configuration. Not a live navigation result.")
        manifest["files"].update({name: sha(inputs / name) for name in ("events.json", "planner.yaml")})
        write(inputs / "input_manifest.json", manifest)
        print(inputs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    worker() if args.worker else host()
