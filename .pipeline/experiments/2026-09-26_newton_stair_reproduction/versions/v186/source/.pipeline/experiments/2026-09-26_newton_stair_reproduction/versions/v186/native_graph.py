"""Launch pinned native ROS components and explicit selected variants."""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

VERSION = Path(__file__).resolve().parent
BASE = VERSION.parents[1]
sys.path.insert(0, str(BASE / "references"))
from archived_pilot_driver import get_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output
    request = json.loads((out / "episode_request.json").read_text())
    if request.get("integration_version") != "v186":
        raise ValueError("v186 graph requires the frozen v186 integration identity")
    contract = json.loads((VERSION / "navigation_contract.json").read_text())
    variant=request['native_variant']
    if variant not in ('baseline','candidate'):
        raise ValueError('Explicit native variant required')
    epoch = request["run_epoch_ns"]
    sources = BASE / "runtime_sources"
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

    try:
        launch("frequency_observer", [py, str(VERSION / "frequency_observer.py"), "--output", str(out)])
        launch("clock_responder", [py, str(BASE / "scripts/clock_sync.py"), "--port", "24602"])
        if request["applied_transport"] == "zmq":
            launch("applied_receiver", [py, str(VERSION / "applied_channel.py"), "--output", str(out)])
        flat = request.get("scene") in ("flat_static", "flat_box", "flat_empty_long")
        long_route = request.get("scene") == "flat_empty_long"
        map_path = (BASE / "repairs/2026-09-26_generic_occupancy/flat_inputs_v2/flat_floor.pickle"
                    if flat else BASE / "inputs/new_building.pickle")
        pct_script = str(BASE / "repairs/2026-09-26_generic_occupancy/flat_support_publisher.py"
                         if flat else sources / "bridge/lite3_sim_bridge/pct_sim_clock_publisher.py")
        if long_route:
            map_path = BASE / "repairs/2026-09-27_pd_long_route/inputs/flat_floor.pickle"
            pct_script = str(BASE / "scripts/long_support_publisher.py")
        route_map=map_path
        if variant in ('baseline','candidate'):
            if flat: raise ValueError('Static coverage correction is Building-only')
            record=json.loads((VERSION/'global_map_input.json').read_text())
            route_map=Path(record['file'])
            if hashlib.sha256(route_map.read_bytes()).hexdigest()!=record['map_sha256']:
                raise ValueError('Global coverage map identity mismatch')
        (out/'selected_route_map.json').write_text(json.dumps({'variant':variant,'path':str(route_map),
            'sha256':hashlib.sha256(route_map.read_bytes()).hexdigest()},indent=2)+'\n')
        ground_args = [py, pct_script, "--ros-args", "-p", "map_path:=" + str(map_path), "-p", "use_sim_time:=true"]
        if not flat:
            ground_args += ["-p", "elevation_path:=" + str(BASE / "inputs/new_building_original_precision.npz")]
        launch("pct_support", ground_args)
        if not flat:
            launch("pct_physical_floor", [py, str(VERSION / "physical_floor_publisher.py"), "--ros-args", "-p", "use_sim_time:=true"])
            launch("pct_surface_ground", ground_args + ["-r", "__node:=pct_surface_ground_publisher",
                "-p", "ground_mode:=surface_evidence", "-p", "dense_surface_path:=" +
                str(BASE / "inputs/new_building_dense_surface.npy")])
        if not request.get("geometry_obstacles", False):
            launch("tracking_ground", [py, pct_script, "--ros-args", "-r", "__node:=pct_tracking_ground_publisher",
                  "-p", "map_path:=" + str(BASE / "inputs/new_building.pickle"), "-p", "ground_mode:=tracking_physical", "-p", "use_sim_time:=true"])
        if not request.get("geometry_obstacles", False):
            launch("tracker", ["ros2", "run", "scan_reactive_tracker", "moving_cluster_tracker", "--ros-args", "-p", "use_sim_time:=true",
                  "-p", "static_background_pcd:=" + str(BASE / "inputs/static_background/building2_9.pcd")])
        launch("health", [py, str(VERSION / "native_observer.py"), "--output", str(out / "artifacts/runtime_health.json"),
              "--run-id", out.name, "--epoch", str(epoch), "--ros-args", "-p", "use_sim_time:=true"])
        launch("body_tf", [py, str(VERSION / "body_tf_bridge.py"), "--ros-args", "-p", "use_sim_time:=true"])
        launch("bridge", [py, "-c", "from lite3_sim_bridge.foxy_bridge_node import main; main()", "--ros-args", "--params-file", str(cfg / "bridge.yaml"),
              "-p", "telemetry_host:=host.docker.internal", "-p", "telemetry_port:=24600",
              "-p", "command_host:=host.docker.internal", "-p", "command_port:=24601",
              "-p", "scan_audit_path:=" + str(out / "bridge_scan_audit.jsonl")])
        backend = json.loads((cfg / "p2b_backend_ros.two_goal.json").read_text())
        backend.update(run_id=out.name, run_epoch_ns=epoch)
        backend["pct_worker"]["port"] = 24651
        if variant in ('baseline','candidate'):
            backend['map'].update(epoch='stair_reactive_coverage_v135',revision=1)
        backend["navigation"] = contract
        backend.setdefault("arrival", {}).update(xy_tolerance_m=contract["xy_goal_tolerance_m"],
            z_tolerance_m=contract["z_goal_tolerance_m"], yaw_tolerance_rad=contract["yaw_goal_tolerance_rad"],
            monitor_period_s=1/contract["controller_frequency"])
        if request.get("building_route_profile") in ("historical_full", "corner_start"):
            if request.get("scene") != "building_full":
                raise ValueError("Historical profile requires the full Building geometry")
            backend["map"]["pct_layer"] = None  # Existing native multi-floor selection.
        backend["service"]["command_timeout_s"] = request.get("goal_wall_budget_s", 35.0)
        # v33: in this simulator the backend judges body-pose freshness by simulation time, with a 2.0 s wall-time
        # backstop for a stopped simulator or a stalled pose path (Dr Sun, 2026-09-29). Every other gate keeps
        # wall time.
        backend["gate"].update(odom_time_base="simulation", odom_wall_backstop_s=2.0)
        backend["applied_evidence"].update(current_command_path=str(out / "artifacts/external_episode/current_command.json"),
                                           finish_request_path=str(out / "artifacts/external_episode/finish_request.json"))
        (out / "backend_config.json").write_text(json.dumps(backend, indent=2) + "\n")
        launch("nav2", ["ros2", "launch", "lite3_nav2_bridge", "navigation.launch.py",
              "native_planner_config:="+str(out/"planner.yaml"),
              "backend_config:="+str(out/"backend_config.json"),
              "generated_params:="+str(out/"nav2_params.yaml"), "pct_map:="+str(route_map),
              "use_sim_time:=true", "legacy_http:=true", "base_frame:=base",
              "odom_topic:=/quad_0/body_pose"])
        if not request["probe"]:
            driver = (BASE / "repairs/2026-09-26_generic_occupancy/geometry_driver.py"
                      if request.get("geometry_obstacles", False) else BASE / "references/archived_pilot_driver.py")
            if request.get("startup_mode", "policy") == "pd_stand":
                driver = out / "executed_pd_geometry_driver.py"
            if long_route or request.get("scene") == "building_full":
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
