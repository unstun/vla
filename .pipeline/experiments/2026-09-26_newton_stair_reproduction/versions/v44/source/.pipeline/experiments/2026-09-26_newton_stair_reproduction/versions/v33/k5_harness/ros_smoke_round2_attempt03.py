"""K5 of versions/v33/PLAN.md: v33's pose freshness through real rclpy in the pinned image.

Run inside the pinned image (sha256:f7363cc3...) with /opt/ros/humble and the native build's overlay sourced and
PYTHONPATH as native_inside.sh sets it (see run_ros_smoke.sh). Usage: ros_smoke.py <variant> <attempt>.
Variants:
- multi (the round-1 harness): one process builds the backend's RosScanPort and CommandGate from a hand-built
  gate configuration (simulation base, 2.0 s backstop) and spins it with a publisher node on one
  MultiThreadedExecutor(num_threads=2).
- trial (added after review round 1, N2): the trial's path. The backend config is config_archived's
  p2b_backend_ros.two_goal.json with the gate update read from scripts/native_graph.py's own source and the run
  fields native_graph.py sets; it is loaded with load_runtime_config and built with build_runtime, as
  scripts/native_backend_entry.py does, and the backend node spins alone on a SingleThreadedExecutor (the trial's
  --backend-executor single). The publisher node spins on its own executor. A thread keeps the applied-evidence
  file fresh (wall time), as the Mac worker's applied channel does, so the node's applied-evidence check stays
  open and the pose rule is what the checks read.
In both, a second node publishes /clock with the bridge's own CLOCK_QOS and /quad_0/body_pose with sensor-data
QoS, as foxy_bridge_node.py does, and a SCAN-like thread sends the owner's raw commands at 50 Hz, as SCAN does,
so the node's own watchdog and raw-command paths evaluate the gate (heartbeat fresh) and the checks read their
decisions. Streams are bounded by simulation time (under emulation a 5 ms sleep takes longer than 5 ms).
Pass, all of:
1 streaming: /clock and poses arrive; snapshot() reports the simulation base and a simulation age <= 0.02 s;
  (trial) the loaded gate configuration is simulation/2.0/0.25;
2 host stall: with both streams frozen for 1.0 s of wall time, measurement_provider() returns the pose and the
  gate of an admitted owner stays open with block reason "ok" (the wall rule would call the pose stale);
3 lost poses: with /clock advancing 0.30 s of simulation time and no pose, measurement_provider() raises
  body_pose_stale and the gate closes with odom_stale;
4 stopped simulator: after fresh streaming, at 1.9 s of wall time with nothing arriving the pose is still fresh
  and the gate open, and at 2.1 s measurement_provider() raises body_pose_stale and the gate is closed with
  odom_stale;
5 a backward /clock sample is ignored and counted.
Diagnostics (added after multi attempt 02; no pass condition changed): the longest raw-command receipt gap in each
check's window, as the unchanged 0.20 s heartbeat sees it, and the gate's events.
Writes ros_smoke_<variant>_attempt<attempt>.json next to this script and exits non-zero on failure.
"""
import ast
import json
import os
from pathlib import Path
import platform
import sys
import tempfile
import threading
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor, SingleThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock

from backend_adapter.contracts import CommandIdentity, GateConfig
from backend_adapter.control_gate import CommandGate
from lite3_sim_bridge.foxy_bridge_node import CLOCK_QOS
from scan_planner_msgs.msg import P2BStampedTwist
from p2b_backend_ros.config import load_runtime_config
from p2b_backend_ros.node import RosScanPort, build_runtime

H = Path(__file__).resolve().parent
E = H.parents[1]
EPOCH = 1_700_000_000_000_000_000


def stamp(message_time, ns):
    message_time.sec, message_time.nanosec = ns // 1000000000, ns % 1000000000


def multi_backend():
    backend = rclpy.create_node("p2b_backend_ros_smoke")
    config = {"gate": {"odom_stale_s": 0.25, "heartbeat_stale_s": 0.20, "still_speed_mps": 0.05, "still_window_s": 0.50,
                       "odom_time_base": "simulation", "odom_wall_backstop_s": 2.0},
              "map": {"frame_id": "world", "epoch": "map", "revision": 0}, "topics": {}}
    gate = CommandGate(GateConfig(**config["gate"]))
    port = RosScanPort(backend, config, gate)
    return backend, port, gate, config, {}


def trial_backend(tmp):
    graph = (E / "scripts/native_graph.py").read_text()
    update = next(node for node in ast.walk(ast.parse(graph))
                  if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "update"
                  and isinstance(node.func.value, ast.Subscript) and getattr(node.func.value.slice, "value", None) == "gate")
    backend_config = json.loads((E / "config_archived/p2b_backend_ros.two_goal.json").read_text())
    backend_config.update(run_id="smoke", run_epoch_ns=EPOCH)  # native_graph.py sets the run's own values
    backend_config["gate"].update({k.arg: ast.literal_eval(k.value) for k in update.keywords})
    backend_config["applied_evidence"].update(current_command_path=str(tmp / "current_command.json"),
                                              finish_request_path=str(tmp / "finish_request.json"))
    (tmp / "backend_config.json").write_text(json.dumps(backend_config, indent=2) + "\n")
    config = load_runtime_config(tmp / "backend_config.json")
    node = rclpy.create_node("p2b_backend_ros")
    runtime = build_runtime(node, config)
    port = runtime.scan_port
    loaded = {k: config["gate"].get(k) for k in ("odom_time_base", "odom_wall_backstop_s", "odom_stale_s")}
    return node, port, port.gate, config, {"loaded_gate": loaded, "gate_update_from_native_graph":
                                           {k.arg: ast.literal_eval(k.value) for k in update.keywords}}


def applied_snapshot(sequence):
    zero = {"vx": 0.0, "vy": 0.0, "wz": 0.0}
    return {"schema_version": 1, "run_id": "smoke", "run_epoch_ns": EPOCH, "sim_step": sequence,
            "sim_time_s": 50.0, "wall_monotonic_ns": time.monotonic_ns(), "command_source_timestamp_ns": 0,
            "freshness": {"max_reader_age_s": 2.0, "atomic_replace": True},
            "applied_command": zero, "admitted_command": zero, "raw_command": zero, "command_sequence": sequence,
            "command_stale": False, "command_reason": "ok",
            "measured": {"horizontal_speed_mps": 0.0, "yaw_rate_radps": 0.0, "base_xyz": [0.0, 0.0, 0.3],
                         "base_quat_wxyz": [1.0, 0.0, 0.0, 0.0], "command_obs_error": 0.0},
            "state_epoch": {"state_sequence": sequence, "telemetry_sequence": sequence}}


RAW_RECEIPTS = []  # the backend port's raw-command receipt times (observation only)
_ORIGINAL_RAW = RosScanPort._on_raw_command


def _observed_raw(self, msg):
    RAW_RECEIPTS.append(time.monotonic())
    _ORIGINAL_RAW(self, msg)


RosScanPort._on_raw_command = _observed_raw  # before any port subscribes, as native_backend_entry.py wraps poses


def heartbeat_gap(t0, t1):
    """Longest interval between consecutive raw-command receipts overlapping (t0, t1): the heartbeat's age."""
    times = [t for t in RAW_RECEIPTS]
    gaps = [b - a for a, b in zip(times, times[1:]) if b > t0 and a < t1]
    return round(max(gaps), 3) if gaps else None


def main():
    variant, attempt = sys.argv[1], int(sys.argv[2])
    assert variant in ("multi", "trial")
    output = H / f"ros_smoke_{variant}_attempt{attempt:02d}.json"
    assert not output.exists(), output
    rclpy.init()
    stopping = threading.Event()
    threads = []
    tmp = Path(tempfile.mkdtemp(prefix="v33_smoke_"))
    if variant == "multi":
        backend, port, gate, config, setup = multi_backend()
    else:
        backend, port, gate, config, setup = trial_backend(tmp)

        def applied_stream():
            sequence = 0
            while not stopping.is_set():
                sequence += 1
                part = tmp / "current_command.json.part"
                part.write_text(json.dumps(applied_snapshot(sequence)))
                os.replace(part, tmp / "current_command.json")
                time.sleep(0.02)
        threads.append(threading.Thread(target=applied_stream, daemon=True))
        threads[-1].start()
        time.sleep(0.1)
    map_cfg = config["map"]
    identity = CommandIdentity(run_id="smoke", epoch=1, request_id="req", goal_id="goal", route_id="route",
                               command_id="cmd", generation=1, map_epoch=str(map_cfg["epoch"]),
                               map_revision=int(map_cfg["revision"]))
    source = rclpy.create_node("bridge_like_publisher")
    clock_pub = source.create_publisher(Clock, "/clock", CLOCK_QOS)
    pose_pub = source.create_publisher(Odometry, "/quad_0/body_pose", qos_profile_sensor_data)
    raw_pub = source.create_publisher(P2BStampedTwist, "/quad_0/raw_scan_cmd_vel", 50)
    commanding = threading.Event()

    def command_stream():
        while not stopping.is_set():
            if commanding.is_set():
                message = P2BStampedTwist()
                for field, value in identity.to_dict().items():
                    setattr(message, field, value)
                raw_pub.publish(message)
            time.sleep(0.02)
    threads.append(threading.Thread(target=command_stream, daemon=True))
    threads[-1].start()
    if variant == "multi":
        executors = [MultiThreadedExecutor(num_threads=2)]
        executors[0].add_node(backend)
        executors[0].add_node(source)
    else:
        executors = [SingleThreadedExecutor(), SingleThreadedExecutor()]
        executors[0].add_node(backend)
        executors[1].add_node(source)
    for executor in executors:
        threading.Thread(target=executor.spin, daemon=True).start()
    sim = [50_000_000_000]

    def publish(pose=True, clock=True, clock_ns=None):
        if clock:
            message = Clock()
            stamp(message.clock, sim[0] if clock_ns is None else clock_ns)
            clock_pub.publish(message)
        if pose:
            message = Odometry()
            message.header.frame_id = str(map_cfg.get("frame_id", "world"))
            stamp(message.header.stamp, sim[0])
            pose_pub.publish(message)

    def stream(sim_seconds, pose=True, clock=True):
        start = sim[0]
        while sim[0] - start < round(sim_seconds * 1e9):
            sim[0] += 5_000_000
            publish(pose, clock)
            time.sleep(0.005)
        time.sleep(0.05)  # let the last messages be delivered

    def decision():
        return {"closed_reason": gate.closed_reason, "block_reason": port._last_block_reason}

    def provider():
        try:
            port.measurement_provider()
            return "fresh"
        except RuntimeError as exc:
            return str(exc)

    checks = {}
    time.sleep(1.0)  # discovery
    stream(1.0)
    snap = port.snapshot()
    checks["1_streaming"] = {"odom_time_base": snap["odom_time_base"], "sim_clock_s": snap["sim_clock_s"],
                             "sim_age_s": snap["last_body_pose_sim_age_s"], "provider": provider()}
    checks["1_streaming"]["passed"] = (snap["odom_time_base"] == "simulation" and snap["sim_clock_s"] is not None
                                       and snap["last_body_pose_sim_age_s"] is not None
                                       and abs(snap["last_body_pose_sim_age_s"]) <= 0.02
                                       and checks["1_streaming"]["provider"] == "fresh"
                                       and (variant == "multi" or setup["loaded_gate"] == {
                                           "odom_time_base": "simulation", "odom_wall_backstop_s": 2.0,
                                           "odom_stale_s": 0.25}))

    gate.admit(identity)
    commanding.set()
    window = time.monotonic()
    stream(0.1)  # streaming with the owner commanding
    time.sleep(1.0)  # both streams frozen, commands continue
    wall_age = time.monotonic() - port._last_measurement.monotonic_s
    checks["2_host_stall"] = {"wall_age_s": round(wall_age, 3), "wall_rule_would_be_stale": wall_age > 0.25,
                              "provider": provider(), "gate": decision(),
                              "max_raw_command_gap_s": heartbeat_gap(window, time.monotonic())}
    checks["2_host_stall"]["passed"] = (checks["2_host_stall"]["wall_rule_would_be_stale"]
                                        and checks["2_host_stall"]["provider"] == "fresh"
                                        and checks["2_host_stall"]["gate"] == {"closed_reason": "open", "block_reason": "ok"})

    window = time.monotonic()
    stream(0.30, pose=False)  # /clock only
    snap = port.snapshot()
    time.sleep(0.1)  # a few watchdog ticks
    checks["3_lost_poses"] = {"sim_age_s": snap["last_body_pose_sim_age_s"], "provider": provider(), "gate": decision(),
                              "max_raw_command_gap_s": heartbeat_gap(window, time.monotonic())}
    checks["3_lost_poses"]["passed"] = (checks["3_lost_poses"]["sim_age_s"] > 0.25 and checks["3_lost_poses"]["provider"] == "body_pose_stale"
                                        and checks["3_lost_poses"]["gate"]["closed_reason"] == "odom_stale")

    # Fresh poses first, then a new admission reopens the gate: re-admitting while check 3's pose is still 0.30 s
    # old closes the gate again at the first evaluation (trial attempt 01, a harness fault in COMPONENT_RESULTS.md).
    stream(0.2)
    gate.admit(identity)
    window = time.monotonic()
    stream(0.1)
    stopped = time.monotonic()
    time.sleep(max(0.0, 1.9 - (time.monotonic() - stopped)))
    early = {"provider": provider(), "gate": decision()}
    time.sleep(max(0.0, 2.1 - (time.monotonic() - stopped)))
    late = {"provider": provider(), "gate": decision()}
    checks["4_stopped_simulator"] = {"at_1p9_s": early, "at_2p1_s": late,
                                     "max_raw_command_gap_s": heartbeat_gap(window, time.monotonic()),
                                     "passed": early == {"provider": "fresh", "gate": {"closed_reason": "open", "block_reason": "ok"}}
                                     and late["provider"] == "body_pose_stale" and late["gate"]["closed_reason"] == "odom_stale"}
    commanding.clear()

    before = port.sim_now()
    publish(pose=False, clock=True, clock_ns=sim[0] - 1_000_000_000)
    time.sleep(0.2)
    checks["5_backward_clock"] = {"sim_now_before": before, "sim_now_after": port.sim_now(),
                                  "backward_events": port.snapshot()["sim_clock_backward_events"]}
    checks["5_backward_clock"]["passed"] = (checks["5_backward_clock"]["sim_now_after"] == before
                                            and checks["5_backward_clock"]["backward_events"] == 1)

    stopping.set()
    for executor in executors:
        executor.shutdown()
    backend.destroy_node()
    source.destroy_node()
    rclpy.shutdown()
    report = {"variant": variant, "attempt": attempt, "python": platform.python_version(), "setup": setup,
              "checks": checks, "all_passed": all(c["passed"] for c in checks.values()),
              "gate_events": [e for e in gate.events if e.get("kind") != "blocked_command"][-40:],
              "blocked_commands_by_reason": {r: sum(1 for e in gate.events if e.get("kind") == "blocked_command"
                                                    and e["data"].get("reason") == r)
                                             for r in sorted({e["data"].get("reason") for e in gate.events
                                                              if e.get("kind") == "blocked_command"})}}
    output.write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: v["passed"] for k, v in checks.items()}))
    sys.exit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
