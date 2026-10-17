"""Launch pinned native ROS components and explicit selected variants (Option B direct Nav2 + SCAN)."""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

VERSION = Path(__file__).resolve().parent
BASELINE = VERSION.parent / "v196"
BASE = VERSION.parents[1]
sys.path.insert(0, str(BASE / "references"))
from archived_pilot_driver import get_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--terrain-manifest", type=Path, required=True)
    parser.add_argument("--environmental-manifest", type=Path, required=True)
    args = parser.parse_args()
    out = args.output
    request = json.loads((out / "episode_request.json").read_text())
    if request.get("integration_version") != "v231":
        raise ValueError("v231 execution requires its v230 navigation binding")
    if request.get("applied_transport") != "shared":
        raise ValueError("v206 requires shared applied-state storage")
    contract = json.loads((BASELINE / "navigation_contract.json").read_text())
    variant = request["native_variant"]
    if variant != "candidate":
        raise ValueError("v206 requires the Option B candidate")
    epoch = request["run_epoch_ns"]
    cfg = BASE / "config_archived"
    py = sys.executable
    children, handles = [], []
    commands = {}
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    def launch(name, command):
        log = (out / (name + ".log")).open("w")
        handles.append(log)
        commands[name] = command
        children.append((name, subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)))

    if request.get("scene") != "building_full" or not request.get("geometry_obstacles", False):
        raise ValueError("v206 graph supports the current Building geometry-sensor profile")
    terrain_manifest = args.terrain_manifest.resolve(strict=True)

    try:
        launch("frequency_observer", [py, str(BASELINE / "frequency_observer.py"), "--output", str(out)])
        launch("clock_responder", [py, str(BASE / "scripts/clock_sync.py"), "--port", "24602"])
        # navigation.launch.py owns the one static publisher and all map bindings.
        (out / "selected_terrain.json").write_text(json.dumps({
            "manifest": str(terrain_manifest),
            "sha256": hashlib.sha256(terrain_manifest.read_bytes()).hexdigest()}, indent=2) + "\n")
        launch("health", [py, str(BASELINE / "native_observer.py"), "--output", str(out / "artifacts/runtime_health.json"),
              "--run-id", out.name, "--epoch", str(epoch), "--ros-args", "-p", "use_sim_time:=true"])
        launch("body_tf", [py, str(BASELINE / "body_tf_bridge.py"), "--ros-args", "-p", "use_sim_time:=true"])
        launch("bridge", [py, "-c", "import sys; sys.path.insert(0, sys.argv.pop(1)); from lite3_sim_bridge.foxy_bridge_node import main; main()",
              str(VERSION.parent / "v198/runtime/bridge"), "--ros-args", "--params-file", str(cfg / "bridge.yaml"),
              "-p", "telemetry_host:=host.docker.internal", "-p", "telemetry_port:=24600",
              "-p", "command_host:=host.docker.internal", "-p", "command_port:=24601",
              "-p", "scan_audit_path:=" + str(out / "bridge_scan_audit.jsonl")])
        backend = json.loads((BASELINE / "mission_bridge_input.json").read_text())
        backend.update(run_id=out.name, run_epoch_ns=epoch)
        if variant in ("baseline", "candidate"):
            backend["map"].update(epoch="stair_reactive_coverage_v135", revision=1)
        backend["navigation"] = contract
        backend.setdefault("arrival", {}).update(
            xy_tolerance_m=contract["xy_goal_tolerance_m"],
            z_tolerance_m=contract["z_goal_tolerance_m"],
            yaw_tolerance_rad=contract["yaw_goal_tolerance_rad"],
            monitor_period_s=1 / contract["controller_frequency"])
        if request.get("building_route_profile") in ("historical_full", "corner_start"):
            if request.get("scene") != "building_full":
                raise ValueError("Historical profile requires the full Building geometry")
            backend["map"]["pct_layer"] = None
        backend["service"]["command_timeout_s"] = request.get("goal_wall_budget_s", 35.0)
        (out / "backend_config.json").write_text(json.dumps(backend, indent=2) + "\n")
        launch("nav2", ["ros2", "launch", "lite3_nav2_bridge", "navigation.launch.py",
              "native_planner_config:=" + str(out / "planner.yaml"),
              "backend_config:=" + str(out / "backend_config.json"),
              "generated_params:=" + str(out / "nav2_params.yaml"),
              "terrain_manifest:=" + str(terrain_manifest),
              "environmental_manifest:=" + str(args.environmental_manifest.resolve(strict=True)),
              "use_sim_time:=true", "base_frame:=base",
              "odom_topic:=/quad_0/body_pose"])
        if not request["probe"]:
            driver = (BASE / "repairs/2026-09-26_generic_occupancy/geometry_driver.py"
                      if request.get("geometry_obstacles", False) else BASE / "references/archived_pilot_driver.py")
            if request.get("startup_mode", "policy") == "pd_stand":
                driver = out / "executed_pd_geometry_driver.py"
            if request.get("scene") == "building_full":
                driver = out / "executed_long_route_driver.py"
            launch("driver", [py, str(driver),
                               "--run-root", str(out), "--run-id", out.name, "--http-port", "8785"])
        (out / "native_commands.json").write_text(json.dumps(commands, indent=2) + "\n")
        while not stopping:
            for name, process in children:
                if name != "driver" and process.poll() is not None:
                    (out / "native_failure.json").write_text(json.dumps({"component": name, "exit_code": process.returncode}))
                    raise RuntimeError(f"Native component {name} exited {process.returncode}")
            try:
                state = get_json("http://127.0.0.1:8785", "/state")
                tmp = out / "backend_latest.tmp"
                tmp.write_text(json.dumps(state) + "\n")
                tmp.replace(out / "backend_latest.json")
            except (OSError, ValueError):
                pass
            time.sleep(.1)
    finally:
        for _, process in children:
            if process.poll() is None:
                process.terminate()
        for _, process in children:
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
        for handle in handles:
            handle.close()


if __name__ == "__main__":
    main()
