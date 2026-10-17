"""Run the archived native ROS components unchanged inside the local image."""
import argparse
import json
from pathlib import Path
import signal
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / "references"))
from archived_pilot_driver import get_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output
    request = json.loads((out / "episode_request.json").read_text())
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
        launch("clock_responder", [py, str(BASE / "scripts/clock_sync.py")])
        if request["applied_transport"] == "zmq":
            launch("applied_receiver", [py, str(BASE / "scripts/applied_channel.py"), "--output", str(out)])
        pct_script = str(sources / "bridge/lite3_sim_bridge/pct_sim_clock_publisher.py")
        launch("pct_support", [py, pct_script, "--ros-args", "-p", "map_path:=" + str(BASE / "inputs/new_building.pickle"), "-p", "use_sim_time:=true"])
        launch("tracking_ground", [py, pct_script, "--ros-args", "-r", "__node:=pct_tracking_ground_publisher",
              "-p", "map_path:=" + str(BASE / "inputs/new_building.pickle"), "-p", "ground_mode:=tracking_physical", "-p", "use_sim_time:=true"])
        launch("pct_worker", [py, "-m", "backend_adapter.pct_worker", "--host", "127.0.0.1", "--port", "47651",
              "--pct-source-root", str(sources / "pct_runtime/python"), "--rsg-root", str(BASE / "inputs"),
              "--tomogram-path", str(BASE / "inputs/new_building.pickle"), "--reference-height-m", "0.30"])
        launch("scan", ["ros2", "run", "scan_planner", "scan_planner_node", "--ros-args", "--params-file", str(cfg / "planner.yaml"),
              "-r", "body_pose:=/quad_0/body_pose", "-r", "sensor_pose:=/quad_0/lidar_pose", "-r", "cloud:=/quad_0/cloud"])
        launch("controller", ["ros2", "run", "scan_planner", "closed_loop_controller", "--ros-args", "--params-file", str(cfg / "controller.yaml"), "-r", "body_pose:=/quad_0/body_pose"])
        launch("tracker", ["ros2", "run", "scan_reactive_tracker", "moving_cluster_tracker", "--ros-args", "-p", "use_sim_time:=true",
              "-p", "static_background_pcd:=" + str(BASE / "inputs/static_background/building2_9.pcd")])
        launch("health", [py, str(BASE / "scripts/native_observer.py"), "--output", str(out / "artifacts/runtime_health.json"),
              "--run-id", out.name, "--epoch", str(epoch), "--ros-args", "-p", "use_sim_time:=true"])
        launch("bridge", [py, "-c", "from lite3_sim_bridge.foxy_bridge_node import main; main()", "--ros-args", "--params-file", str(cfg / "bridge.yaml"),
              "-p", "telemetry_host:=host.docker.internal", "-p", "telemetry_port:=46200",
              "-p", "command_host:=host.docker.internal", "-p", "command_port:=46201",
              "-p", "scan_audit_path:=" + str(out / "bridge_scan_audit.jsonl")])
        backend = json.loads((cfg / "p2b_backend_ros.two_goal.json").read_text())
        backend.update(run_id=out.name, run_epoch_ns=epoch)
        backend["applied_evidence"].update(current_command_path=str(out / "artifacts/external_episode/current_command.json"),
                                           finish_request_path=str(out / "artifacts/external_episode/finish_request.json"))
        (out / "backend_config.json").write_text(json.dumps(backend, indent=2) + "\n")
        launch("backend", [py, str(BASE / "scripts/native_backend_entry.py"), "--config", str(out / "backend_config.json"),
                            "--executor", request["backend_executor"]])
        if not request["probe"]:
            launch("driver", [py, str(BASE / "references/archived_pilot_driver.py"),
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
