"""Runnable Foxy/rclpy adapter node with localhost JSON HTTP control API."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Mapping, Optional, Tuple

from .adapter_core import P2BBackendAdapter
from .applied_evidence import AppliedEvidenceReader, StopEvidenceConfig, finish_request_payload
from .contracts import CommandIdentity, ContractError, GateConfig, MeasuredState, NativeRoute, ScanAdmission, require_finite, require_identifier, require_int
from .control_gate import CommandGate
from .p2a_bridge import load_p2a_core
from .pct_ipc import PctIpcClient, PctIpcClientConfig
from .scan_wire import ScanPort, ScanTopics


class RosUnavailable(RuntimeError):
    pass


class RosScanPort(ScanPort):
    def __init__(self, node: Any, topics: ScanTopics, gate: CommandGate, map_epoch: str, map_revision: int, submit_timeout_s: float = 2.0, stop_timeout_s: float = 2.0) -> None:
        self.node = node
        self.topics = topics
        self.gate = gate
        self.map_epoch = map_epoch
        self.map_revision = map_revision
        self.submit_timeout_s = submit_timeout_s
        self.stop_timeout_s = stop_timeout_s
        self._condition = threading.Condition()
        self._admissions = []
        self._last_measurement = None  # type: Optional[MeasuredState]
        self._load_ros_types()
        self.route_pub = node.create_publisher(self.P2BRoute, topics.route_topic, 10)
        self.cancel_pub = node.create_publisher(self.P2BCancel, topics.cancel_topic, 10)
        self.gated_pub = node.create_publisher(self.Twist, topics.gated_cmd_topic, 20)
        self.admission_sub = node.create_subscription(self.P2BAdmission, topics.admission_topic, self._on_admission, 10)
        self.raw_sub = node.create_subscription(self.P2BStampedTwist, topics.raw_cmd_topic, self._on_raw_command, 20)
        self.odom_sub = node.create_subscription(self.Odometry, "/quad_0/body_pose", self._on_body_pose, 20)
        self.watchdog_timer = node.create_timer(0.02, self._watchdog_tick)

    def _load_ros_types(self) -> None:
        try:
            from geometry_msgs.msg import Point, PoseStamped, Twist
            from nav_msgs.msg import Odometry, Path
            from scan_planner_msgs.msg import P2BAdmission, P2BCancel, P2BRoute, P2BStampedTwist
        except Exception as exc:
            raise RosUnavailable("p2b_overlay_messages_unavailable") from exc
        self.Point = Point
        self.PoseStamped = PoseStamped
        self.Twist = Twist
        self.Odometry = Odometry
        self.Path = Path
        self.P2BAdmission = P2BAdmission
        self.P2BCancel = P2BCancel
        self.P2BRoute = P2BRoute
        self.P2BStampedTwist = P2BStampedTwist

    def measurement_provider(self) -> MeasuredState:
        if self._last_measurement is None:
            raise RuntimeError("body_pose_not_ready")
        return self._last_measurement

    def wait_body_ready(self, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self._last_measurement is not None:
                return True
            time.sleep(0.02)
        return False

    def submit_route(self, identity: CommandIdentity, route: NativeRoute) -> ScanAdmission:
        msg = self.P2BRoute()
        self._fill_identity(msg, identity)
        msg.path = self._route_to_path(route)
        with self._condition:
            self.route_pub.publish(msg)
            return self._wait_admission(identity, {"accepted", "rejected"}, self.submit_timeout_s, required_consumer="controller")

    def request_stop(self, identity: CommandIdentity, reason: str) -> ScanAdmission:
        msg = self.P2BCancel()
        self._fill_identity(msg, identity)
        msg.reason = reason
        with self._condition:
            self.cancel_pub.publish(msg)
            return self._wait_admission(identity, {"stopped", "pending", "uncertain", "rejected"}, self.stop_timeout_s, required_consumer="controller")

    def _route_to_path(self, route: NativeRoute) -> Any:
        path = self.Path()
        path.header.frame_id = route.frame_id
        path.header.stamp = self.node.get_clock().now().to_msg()
        for x, y, z in route.waypoints_m:
            pose = self.PoseStamped()
            pose.header = path.header
            pose.pose.position.x = float(x)
            pose.pose.position.y = float(y)
            pose.pose.position.z = float(z)
            pose.pose.orientation.w = 1.0
            path.poses.append(pose)
        return path

    def _wait_admission(self, identity: CommandIdentity, statuses: set, timeout_s: float, required_consumer: Optional[str] = None) -> ScanAdmission:
        deadline = time.monotonic() + timeout_s
        while True:
            for idx, admission in enumerate(list(self._admissions)):
                if admission.identity.matches(identity) and admission.status in statuses and (required_consumer is None or admission.consumer == required_consumer or admission.status == "rejected"):
                    self._admissions.pop(idx)
                    return admission
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                return ScanAdmission("pending", identity, "scan_admission_timeout")
            self._condition.wait(remaining)

    def _on_admission(self, msg: Any) -> None:
        identity = self._identity_from_msg(msg)
        admission = ScanAdmission(
            status=str(msg.status),
            identity=identity,
            message=str(msg.message),
            hold_confirmed=bool(msg.hold_confirmed),
            measured_stillness_confirmed=bool(msg.measured_stillness_confirmed),
            consumer=str(msg.consumer),
        )
        with self._condition:
            self._admissions.append(admission)
            self._condition.notify_all()

    def _on_raw_command(self, msg: Any) -> None:
        identity = self._identity_from_msg(msg)
        self.gate.observe_heartbeat(time.monotonic())
        decision = self.gate.gate_raw_command(identity, (float(msg.twist.linear.x), float(msg.twist.linear.y), float(msg.twist.angular.z)))
        out = self.Twist()
        out.linear.x, out.linear.y, out.angular.z = decision.command_xyz_yaw
        self.gated_pub.publish(out)

    def _on_body_pose(self, msg: Any) -> None:
        now = time.monotonic()
        seq = int(getattr(msg.header, "stamp", None).sec * 1000000000 + getattr(msg.header, "stamp", None).nanosec) if getattr(msg, "header", None) else int(now * 1000)
        state = MeasuredState(
            state_sequence=max(1, seq),
            monotonic_s=now,
            position_world_m=(float(msg.pose.pose.position.x), float(msg.pose.pose.position.y), float(msg.pose.pose.position.z)),
            velocity_world_mps=(float(msg.twist.twist.linear.x), float(msg.twist.twist.linear.y), float(msg.twist.twist.linear.z)),
            map_epoch=self.map_epoch,
            map_revision=self.map_revision,
            source="diagnostic_sim_truth_body_pose",
        )
        self._last_measurement = state
        try:
            self.gate.observe_measurement(state)
        except ContractError:
            pass

    def _watchdog_tick(self) -> None:
        decision = self.gate.tick()
        if not decision.allowed:
            out = self.Twist()
            self.gated_pub.publish(out)

    def _fill_identity(self, msg: Any, identity: CommandIdentity) -> None:
        msg.run_id = identity.run_id
        msg.epoch = identity.epoch
        msg.request_id = identity.request_id
        msg.goal_id = identity.goal_id
        msg.route_id = identity.route_id
        msg.command_id = identity.command_id
        msg.generation = identity.generation
        msg.map_epoch = identity.map_epoch
        msg.map_revision = identity.map_revision

    def _identity_from_msg(self, msg: Any) -> CommandIdentity:
        return CommandIdentity(
            run_id=str(msg.run_id), epoch=int(msg.epoch), request_id=str(msg.request_id), goal_id=str(msg.goal_id),
            route_id=str(msg.route_id), command_id=str(msg.command_id), generation=int(msg.generation),
            map_epoch=str(msg.map_epoch), map_revision=int(msg.map_revision),
        )


class NavigationHttpRuntime:
    def __init__(self, service: Any, adapter: P2BBackendAdapter, scan_port: RosScanPort, config: Mapping[str, Any]) -> None:
        self.service = service
        self.adapter = adapter
        self.scan_port = scan_port
        self.config = dict(config)
        self.p2a = load_p2a_core()
        self._lock = threading.Lock()
        self.jobs = {}
        self.terminals = []
        self.last_error = None
        self._arrival_tolerance_xy = float(config.get("pilot_contract", {}).get("arrival_tolerance_xy_m", 0.25))
        self._arrival_tolerance_z = float(config.get("pilot_contract", {}).get("arrival_tolerance_z_m", 0.20))
        self._monitor_stop = False
        self._monitor_thread = threading.Thread(target=self._monitor_arrival, name="p2b-arrival-monitor", daemon=True)
        self._monitor_thread.start()

    def submit_goal(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        request_id = require_identifier("request_id", payload.get("request_id"))
        goal_id = require_identifier("goal_id", payload.get("goal_id"))
        target = payload.get("target")
        if not isinstance(target, Mapping):
            raise ContractError("invalid_target")
        job_id = str(uuid.uuid4())
        with self._lock:
            self.jobs[job_id] = {"status": "planning", "request_id": request_id, "goal_id": goal_id}
        thread = threading.Thread(target=self._goal_worker, args=(job_id, request_id, goal_id, target, payload), daemon=True)
        thread.start()
        return {"ok": True, "status": "planning", "job_id": job_id, "request_id": request_id, "goal_id": goal_id}

    def cancel(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        reason = str(payload.get("reason", "http_cancel"))
        result = self.service.cancel_active(reason)
        with self._lock:
            self.terminals.append({"kind": "cancel", "reason": reason, "result": result, "time": time.monotonic()})
        return result

    def state(self) -> Dict[str, Any]:
        measurement = None
        try:
            m = self.scan_port.measurement_provider()
            measurement = {
                "state_sequence": m.state_sequence,
                "monotonic_s": m.monotonic_s,
                "position_world_m": m.position_world_m,
                "velocity_world_mps": m.velocity_world_mps,
                "horizontal_speed_mps": m.horizontal_speed_mps,
                "map_epoch": m.map_epoch,
                "map_revision": m.map_revision,
                "source": m.source,
            }
        except Exception:
            pass
        with self._lock:
            return {
                "ok": True,
                "service": self.service.state(),
                "jobs": dict(self.jobs),
                "terminals": list(self.terminals[-20:]),
                "measurement": measurement,
                "gate": self.adapter.gate.snapshot(),
                "last_error": self.last_error,
                "run_id": self.config.get("run_id"),
                "run_epoch_ns": self.config.get("run_epoch_ns"),
            }

    def _goal_worker(self, job_id: str, request_id: str, goal_id: str, target: Mapping[str, Any], payload: Mapping[str, Any]) -> None:
        try:
            if not self.scan_port.wait_body_ready(float(payload.get("body_ready_timeout_s", 5.0))):
                raise RuntimeError("body_pose_not_ready")
            now = time.monotonic()
            map_epoch = require_identifier("map_epoch", payload.get("map_epoch", self.config.get("pilot_contract", {}).get("map_epoch", "map")))
            map_revision = require_int("map_revision", payload.get("map_revision", self.config.get("pilot_contract", {}).get("map_revision", 0)), 0)
            frame_id = require_identifier("frame", payload.get("frame", target.get("frame", "world")))
            z = target.get("z_m", target.get("body_z_m", self.config.get("pilot_contract", {}).get("measured_body_height_reference_m", 0.35)))
            request = self.p2a.GoalRequest(
                request_id=request_id,
                goal_id=goal_id,
                target=self.p2a.SpatialTarget(require_finite("target_x_m", target.get("x_m")), require_finite("target_y_m", target.get("y_m")), require_finite("target_z_m", z), None, frame_id, "m"),
                evidence=self.p2a.EvidenceSnapshot(str(payload.get("observation_id", request_id)), now, frame_id, "m", map_epoch, map_revision, 1, True, "diagnostic_sim_truth_http"),
                model_arguments={"source": "p2b_http"},
            )
            result = self.service.submit_goal(request)
            with self._lock:
                self.jobs[job_id].update({"status": result.get("status"), "result": result})
        except Exception as exc:
            with self._lock:
                self.jobs[job_id].update({"status": "failed", "error": str(exc)})
                self.last_error = str(exc)

    def _monitor_arrival(self) -> None:
        while not self._monitor_stop:
            time.sleep(0.05)
            owner = getattr(self.service, "active_owner", None)
            if owner is None or self.adapter.gate.owner is None:
                continue
            try:
                measurement = self.scan_port.measurement_provider()
            except Exception:
                continue
            route_target = self.adapter.route_targets.get(owner.route_id)
            if route_target is None:
                continue
            dx = float(measurement.position_world_m[0]) - float(route_target[0])
            dy = float(measurement.position_world_m[1]) - float(route_target[1])
            dz = float(measurement.position_world_m[2]) - float(route_target[2])
            if math.hypot(dx, dy) > self._arrival_tolerance_xy or abs(dz) > self._arrival_tolerance_z:
                continue
            stop = self.adapter.stop(owner.command, "arrived_hold")
            if getattr(stop, "status", None) == "stopped":
                feedback = self.p2a.Feedback(
                    run_id=owner.command.run_id, epoch=owner.command.epoch, goal_id=owner.goal_id,
                    route_id=owner.route_id, command_id=owner.command_id, feedback_seq=owner.last_feedback_seq + 1,
                    status="arrived", message="arrived_after_quiescence", map_epoch=self.service.map_epoch,
                    map_revision=self.service.map_revision,
                )
                result = self.service.receive_feedback(feedback)
                with self._lock:
                    self.terminals.append({"kind": "arrived", "route_id": owner.route_id, "result": result, "time": time.monotonic()})


def _make_handler(runtime: NavigationHttpRuntime):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, data: Mapping[str, Any]) -> None:
            raw = json.dumps(data, sort_keys=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _read_json(self) -> Dict[str, Any]:
            n = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
            if not isinstance(data, dict):
                raise ValueError("json_body_must_be_object")
            return data

        def do_GET(self) -> None:
            if self.path != "/state":
                self._send(404, {"ok": False, "error": "not_found"})
                return
            self._send(200, runtime.state())

        def do_POST(self) -> None:
            try:
                payload = self._read_json()
                if self.path == "/goal":
                    self._send(202, runtime.submit_goal(payload))
                elif self.path == "/cancel":
                    self._send(200, runtime.cancel(payload))
                else:
                    self._send(404, {"ok": False, "error": "not_found"})
            except Exception as exc:
                self._send(400, {"ok": False, "error": str(exc)})

        def log_message(self, fmt: str, *args: Any) -> None:
            return
    return Handler


def load_config(path: pathlib.Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config_must_be_object")
    if data.get("schema") not in {"p2b_backend_adapter_config_v1", "p2b_backend_adapter_config_v2"}:
        raise ValueError("invalid_config_schema")
    return data


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run P2B Foxy ROS adapter with localhost HTTP API")
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    config = load_config(pathlib.Path(args.config))
    import rclpy
    from rclpy.executors import MultiThreadedExecutor
    rclpy.init(args=None)
    node = rclpy.create_node("p2b_backend_adapter")
    topics = ScanTopics(**config.get("topics", {}))
    gate_cfg = config.get("gate", {})
    gate = CommandGate(GateConfig(**gate_cfg))
    pilot = config.get("pilot_contract", {})
    scan_port = RosScanPort(node, topics, gate, str(pilot.get("map_epoch", "map")), int(pilot.get("map_revision", 0)))
    pct_cfg = config.get("pct_worker", {})
    pct_client = PctIpcClient(PctIpcClientConfig(host=pct_cfg.get("host", "127.0.0.1"), port=int(pct_cfg.get("port", 47631)), connect_timeout_s=float(pct_cfg.get("connect_timeout_s", 0.2)), response_timeout_s=float(pct_cfg.get("response_timeout_s", 5.0))))
    evidence_cfg = config.get("applied_evidence", {})
    reader = AppliedEvidenceReader(pathlib.Path(evidence_cfg.get("current_command_path", "/shared/current_command.json")))
    stop_cfg = StopEvidenceConfig(float(evidence_cfg.get("stop_command_norm", 0.01)), float(evidence_cfg.get("stop_speed_mps", 0.10)), float(evidence_cfg.get("stop_yaw_rate_radps", 0.15)))
    adapter = P2BBackendAdapter(pct_client, scan_port, gate, scan_port.measurement_provider, frame_id=str(pilot.get("frame_id", "world")), optimize=bool(pct_cfg.get("optimize", True)), applied_reader=reader, expected_run_epoch_ns=int(config.get("run_epoch_ns", 0)), stop_evidence_config=stop_cfg)
    p2a = load_p2a_core()
    service = p2a.PersistentNavigationService(str(config.get("run_id", "p2b-run")), str(pilot.get("map_epoch", "map")), int(pilot.get("map_revision", 0)), backend=adapter, max_evidence_age_s=float(config.get("max_evidence_age_s", 10.0)))
    runtime = NavigationHttpRuntime(service, adapter, scan_port, config)
    http_cfg = config.get("http", {})
    server = ThreadingHTTPServer((str(http_cfg.get("host", "127.0.0.1")), int(http_cfg.get("port", 8765))), _make_handler(runtime))
    http_thread = threading.Thread(target=server.serve_forever, name="p2b-http", daemon=True)
    http_thread.start()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        server.shutdown()
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
