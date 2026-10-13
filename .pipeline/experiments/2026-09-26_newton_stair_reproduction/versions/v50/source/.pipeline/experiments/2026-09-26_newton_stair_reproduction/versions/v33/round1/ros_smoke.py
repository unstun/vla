"""K5 of versions/v33/PLAN.md: v33's pose freshness through real rclpy in the pinned image.

Run inside the pinned image (sha256:f7363cc3...) with /opt/ros/humble and the native build's overlay sourced and
PYTHONPATH as native_inside.sh sets it (see run_ros_smoke.sh). One process builds the backend's RosScanPort (a
real rclpy node, simulation base, 2.0 s backstop) and a second node that publishes /clock with the bridge's own
CLOCK_QOS and /quad_0/body_pose with sensor-data QoS, as foxy_bridge_node.py does.
Pass, all of:
1 streaming: /clock and poses arrive; snapshot() reports the simulation base and a simulation age <= 0.02 s;
2 host stall: with both streams frozen for 1.0 s of wall time, measurement_provider() returns the pose and the
  gate of an admitted owner stays open with block reason "ok" (the wall rule would call the pose stale);
3 lost poses: with /clock advancing 0.30 s of simulation time and no pose, measurement_provider() raises
  body_pose_stale and the gate closes with odom_stale;
4 stopped simulator: after fresh streaming, at 1.9 s of wall time with nothing arriving the pose is still fresh
  and the gate open, and at 2.1 s measurement_provider() raises body_pose_stale and the gate is closed with
  odom_stale;
5 a backward /clock sample is ignored and counted.
Throughout 2-4 a SCAN-like publisher sends the owner's raw commands at 50 Hz, as SCAN does, so the node's own
watchdog and raw-command paths evaluate the gate (heartbeat fresh) and the checks read their decisions.
Writes ros_smoke.json next to this script and exits non-zero on failure.
"""
import json
from pathlib import Path
import platform
import sys
import threading
import time

import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock

from backend_adapter.contracts import CommandIdentity, GateConfig
from backend_adapter.control_gate import CommandGate
from lite3_sim_bridge.foxy_bridge_node import CLOCK_QOS
from scan_planner_msgs.msg import P2BStampedTwist
from p2b_backend_ros.node import RosScanPort

H = Path(__file__).resolve().parent
IDENTITY = CommandIdentity(run_id="smoke", epoch=1, request_id="req", goal_id="goal", route_id="route",
                           command_id="cmd", generation=1, map_epoch="map", map_revision=0)


def stamp(message_time, ns):
    message_time.sec, message_time.nanosec = ns // 1000000000, ns % 1000000000


def main():
    rclpy.init()
    backend = rclpy.create_node("p2b_backend_ros_smoke")
    source = rclpy.create_node("bridge_like_publisher")
    config = {"gate": {"odom_stale_s": 0.25, "heartbeat_stale_s": 0.20, "still_speed_mps": 0.05, "still_window_s": 0.50,
                       "odom_time_base": "simulation", "odom_wall_backstop_s": 2.0},
              "map": {"frame_id": "world", "epoch": "map", "revision": 0}, "topics": {}}
    gate = CommandGate(GateConfig(**config["gate"]))
    port = RosScanPort(backend, config, gate)
    clock_pub = source.create_publisher(Clock, "/clock", CLOCK_QOS)
    pose_pub = source.create_publisher(Odometry, "/quad_0/body_pose", qos_profile_sensor_data)
    raw_pub = source.create_publisher(P2BStampedTwist, "/quad_0/raw_scan_cmd_vel", 50)
    commanding = threading.Event()

    def command_stream():
        while not stopping.is_set():
            if commanding.is_set():
                message = P2BStampedTwist()
                for field, value in IDENTITY.to_dict().items():
                    setattr(message, field, value)
                raw_pub.publish(message)
            time.sleep(0.02)
    stopping = threading.Event()
    threading.Thread(target=command_stream, daemon=True).start()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(backend)
    executor.add_node(source)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    sim = [50_000_000_000]

    def publish(pose=True, clock=True, clock_ns=None):
        if clock:
            message = Clock()
            stamp(message.clock, sim[0] if clock_ns is None else clock_ns)
            clock_pub.publish(message)
        if pose:
            message = Odometry()
            message.header.frame_id = "world"
            stamp(message.header.stamp, sim[0])
            pose_pub.publish(message)

    def stream(sim_seconds, pose=True, clock=True):
        # Bounded by simulation time: under emulation a 5 ms sleep takes longer than 5 ms.
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
                                       and abs(snap["last_body_pose_sim_age_s"]) <= 0.02 and checks["1_streaming"]["provider"] == "fresh")

    gate.admit(IDENTITY)
    commanding.set()
    stream(0.1)  # streaming with the owner commanding
    time.sleep(1.0)  # both streams frozen, commands continue
    wall_age = time.monotonic() - port._last_measurement.monotonic_s
    checks["2_host_stall"] = {"wall_age_s": round(wall_age, 3), "wall_rule_would_be_stale": wall_age > 0.25,
                              "provider": provider(), "gate": decision()}
    checks["2_host_stall"]["passed"] = (checks["2_host_stall"]["wall_rule_would_be_stale"]
                                        and checks["2_host_stall"]["provider"] == "fresh"
                                        and checks["2_host_stall"]["gate"] == {"closed_reason": "open", "block_reason": "ok"})

    stream(0.30, pose=False)  # /clock only
    snap = port.snapshot()
    time.sleep(0.1)  # a few watchdog ticks
    checks["3_lost_poses"] = {"sim_age_s": snap["last_body_pose_sim_age_s"], "provider": provider(), "gate": decision()}
    checks["3_lost_poses"]["passed"] = (checks["3_lost_poses"]["sim_age_s"] > 0.25 and checks["3_lost_poses"]["provider"] == "body_pose_stale"
                                        and checks["3_lost_poses"]["gate"]["closed_reason"] == "odom_stale")

    gate.admit(IDENTITY)  # a new admission reopens the gate
    stream(0.2)
    stopped = time.monotonic()
    time.sleep(max(0.0, 1.9 - (time.monotonic() - stopped)))
    early = {"provider": provider(), "gate": decision()}
    time.sleep(max(0.0, 2.1 - (time.monotonic() - stopped)))
    late = {"provider": provider(), "gate": decision()}
    checks["4_stopped_simulator"] = {"at_1p9_s": early, "at_2p1_s": late,
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
    executor.shutdown()
    backend.destroy_node()
    source.destroy_node()
    rclpy.shutdown()
    report = {"python": platform.python_version(), "checks": checks, "all_passed": all(c["passed"] for c in checks.values())}
    (H / "ros_smoke.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v["passed"] for k, v in checks.items()}))
    sys.exit(0 if report["all_passed"] else 1)


if __name__ == "__main__":
    main()
