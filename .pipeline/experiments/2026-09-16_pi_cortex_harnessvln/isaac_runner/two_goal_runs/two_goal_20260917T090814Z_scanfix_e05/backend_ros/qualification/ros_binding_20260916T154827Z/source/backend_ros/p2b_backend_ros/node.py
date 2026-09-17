"""Runnable Foxy rclpy node for P2B local HTTP navigation control."""

from __future__ import annotations

import argparse
import dataclasses
import json
import pathlib
import threading
import time
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple

from backend_adapter.adapter_core import P2BBackendAdapter
from backend_adapter.applied_evidence import AppliedEvidenceReader, StopEvidenceConfig
from backend_adapter.contracts import CommandIdentity, ContractError, GateConfig, MeasuredState, NativeRoute, ScanAdmission
from backend_adapter.control_gate import CommandGate
from backend_adapter.p2a_bridge import load_p2a_core
from backend_adapter.pct_ipc import PctIpcClient, PctIpcClientConfig
from backend_adapter.scan_wire import ScanPort

from .config import load_runtime_config, render_wire_contract
from .runtime import NavigationHttpRuntime, pct_start_from_body_pose, start_http_server


class RosUnavailable(RuntimeError):
    pass


class RosScanPort(ScanPort):
    def __init__(self, node: Any, config: Mapping[str, Any], gate: CommandGate) -> None:
        self.node = node
        self.config = config
        self.gate = gate
        self.map_epoch = str(config.get("map", {}).get("epoch", "map"))
        self.map_revision = int(config.get("map", {}).get("revision", 0))
        self.nominal_body_height_m = float(config.get("map", {}).get("nominal_body_height_m", 0.35))
        self._condition = threading.Condition()
        self._admissions = []
        self._last_measurement = None  # type: Optional[MeasuredState]
        self._state_seq = 0
        self._active_owner_key = None
        self._owner_admitted_s = None  # type: Optional[float]
        self._owner_first_heartbeat_s = None  # type: Optional[float]
        self._last_raw_command_s = None  # type: Optional[float]
        self._last_block_reason = "no_owner"
        self._last_admission = None  # type: Optional[Dict[str, Any]]
        self._faults = []  # type: List[Dict[str, Any]]
        self._last_odom_stamp_ns = None  # type: Optional[int]
        self._load_ros_types()
        topics = config.get("topics", {})
        self.route_pub = node.create_publisher(self.P2BRoute, topics.get("route_topic", "/p2b/route"), 10)
        self.cancel_pub = node.create_publisher(self.P2BCancel, topics.get("cancel_topic", "/p2b/scan_cancel"), 10)
        self.gated_pub = node.create_publisher(self.Twist, topics.get("gated_cmd_topic", "/quad_0/cmd_vel"), 20)
        self.admission_sub = node.create_subscription(self.P2BAdmission, topics.get("admission_topic", "/p2b/scan_admission"), self._on_admission, 20)
        self.raw_sub = node.create_subscription(self.P2BStampedTwist, topics.get("raw_cmd_topic", "/quad_0/raw_scan_cmd_vel"), self._on_raw_command, 50)
        self.odom_sub = node.create_subscription(self.Odometry, topics.get("body_pose_topic", "/quad_0/body_pose"), self._on_body_pose, 50)
        self.watchdog_timer = node.create_timer(0.02, self._watchdog_tick)

    def _load_ros_types(self) -> None:
        try:
            from geometry_msgs.msg import PoseStamped, Twist
            from nav_msgs.msg import Odometry, Path
            from scan_planner_msgs.msg import P2BAdmission, P2BCancel, P2BRoute, P2BStampedTwist
        except Exception as exc:
            raise RosUnavailable("p2b_overlay_messages_unavailable") from exc
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
        age_s = time.monotonic() - self._last_measurement.monotonic_s
        stale_s = float(self.config.get("gate", {}).get("odom_stale_s", 0.25))
        if age_s > stale_s:
            raise RuntimeError("body_pose_stale")
        return self._last_measurement

    def pct_start_provider(self) -> MeasuredState:
        return pct_start_from_body_pose(self.measurement_provider(), self.nominal_body_height_m)

    def wait_body_ready(self, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                self.measurement_provider()
                return True
            except Exception:
                pass
            time.sleep(0.02)
        return False

    def submit_route(self, identity: CommandIdentity, route: NativeRoute) -> ScanAdmission:
        msg = self.P2BRoute()
        self._fill_identity(msg, identity)
        msg.path = self._route_to_path(route)
        with self._condition:
            self.route_pub.publish(msg)
            admission = self._wait_admission(identity, {"accepted", "rejected"}, 2.0, {"fsm"})
        if admission.status == "accepted":
            self._mark_owner_admitted(identity)
        return admission

    def request_stop(self, identity: CommandIdentity, reason: str) -> ScanAdmission:
        msg = self.P2BCancel()
        self._fill_identity(msg, identity)
        msg.reason = reason
        with self._condition:
            self.cancel_pub.publish(msg)
            return self._wait_admission(identity, {"stopped", "pending", "uncertain", "rejected"}, 2.0, {"controller"})

    def snapshot(self) -> Dict[str, Any]:
        return {
            "last_raw_command_s": self._last_raw_command_s,
            "owner_admitted_s": self._owner_admitted_s,
            "owner_first_heartbeat_s": self._owner_first_heartbeat_s,
            "last_block_reason": self._last_block_reason,
            "last_admission": self._last_admission,
            "faults": list(self._faults[-20:]),
            "last_body_pose_age_s": None if self._last_measurement is None else time.monotonic() - self._last_measurement.monotonic_s,
        }

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

    def _wait_admission(self, identity: CommandIdentity, statuses: Set[str], timeout_s: float, consumers: Set[str]) -> ScanAdmission:
        deadline = time.monotonic() + timeout_s
        while True:
            for idx, admission in enumerate(list(self._admissions)):
                if admission.identity.matches(identity) and admission.status in statuses and (admission.consumer in consumers or admission.status == "rejected"):
                    self._admissions.pop(idx)
                    return admission
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                return ScanAdmission("pending", identity, "scan_admission_timeout", consumer=next(iter(consumers)))
            self._condition.wait(remaining)

    def _on_admission(self, msg: Any) -> None:
        try:
            identity = self._identity_from_msg(msg)
            consumer = str(getattr(msg, "consumer", ""))
            admission = ScanAdmission(
                status=str(msg.status),
                identity=identity,
                message=str(msg.message),
                consumer=consumer,
                hold_confirmed=bool(msg.hold_confirmed),
                measured_stillness_confirmed=bool(msg.measured_stillness_confirmed),
            )
        except Exception as exc:
            self._fault("malformed_admission", str(exc))
            return
        self._last_admission = {
            "status": admission.status,
            "consumer": admission.consumer,
            "message": admission.message,
            "identity": admission.identity.to_dict(),
        }
        with self._condition:
            self._admissions.append(admission)
            self._condition.notify_all()

    def _on_raw_command(self, msg: Any) -> None:
        try:
            identity = self._identity_from_msg(msg)
        except Exception as exc:
            self._fault("invalid_raw_identity", str(exc))
            self._last_block_reason = "invalid_raw_identity"
            self._publish_zero()
            return
        self._last_raw_command_s = time.monotonic()
        owner = self.gate.owner
        if owner is not None and owner.matches(identity):
            self.gate.observe_heartbeat(self._last_raw_command_s)
            if self._owner_first_heartbeat_s is None:
                self._owner_first_heartbeat_s = self._last_raw_command_s
            if not self._applied_evidence_ready():
                self.gate.close("applied_evidence_stale")
                self._last_block_reason = "applied_evidence_stale"
                self._publish_zero()
                return
        try:
            command = (float(msg.twist.linear.x), float(msg.twist.linear.y), float(msg.twist.angular.z))
            decision = self.gate.gate_raw_command(identity, command)
        except Exception as exc:
            self._fault("invalid_raw_command", str(exc))
            if owner is not None and owner.matches(identity):
                self.gate.close("invalid_raw_command")
            self._last_block_reason = "invalid_raw_command"
            self._publish_zero()
            return
        self._last_block_reason = decision.reason
        out = self.Twist()
        out.linear.x, out.linear.y, out.angular.z = decision.command_xyz_yaw
        self.gated_pub.publish(out)

    def _on_body_pose(self, msg: Any) -> None:
        now = time.monotonic()
        if not self._valid_body_pose_header(msg):
            return
        try:
            state = MeasuredState(
                state_sequence=self._state_seq + 1,
                monotonic_s=now,
                position_world_m=(float(msg.pose.pose.position.x), float(msg.pose.pose.position.y), float(msg.pose.pose.position.z)),
                velocity_world_mps=(float(msg.twist.twist.linear.x), float(msg.twist.twist.linear.y), float(msg.twist.twist.linear.z)),
                map_epoch=self.map_epoch,
                map_revision=self.map_revision,
                source="diagnostic_sim_truth_body_pose",
            )
        except Exception as exc:
            self.gate.close("invalid_body_pose")
            self._fault("invalid_body_pose", str(exc))
            return
        self._state_seq += 1
        self._last_measurement = state
        try:
            self.gate.observe_measurement(state)
        except ContractError:
            self.gate.close("stale_body_pose_sequence")

    def _watchdog_tick(self) -> None:
        owner = self.gate.owner
        if owner is None:
            self._publish_zero()
            self._last_block_reason = "no_owner"
            return
        self._track_owner_change(owner)
        now = time.monotonic()
        if self._owner_first_heartbeat_s is None:
            grace = float(self.config.get("gate", {}).get("initial_heartbeat_grace_s", 1.0))
            if self._owner_admitted_s is not None and now - self._owner_admitted_s > grace:
                self.gate.close("initial_heartbeat_missing")
                self._last_block_reason = "initial_heartbeat_missing"
            else:
                self._last_block_reason = "awaiting_initial_generation_heartbeat"
            self._publish_zero()
            return
        if not self._applied_evidence_ready():
            self.gate.close("applied_evidence_stale")
            self._last_block_reason = "applied_evidence_stale"
            self._publish_zero()
            return
        decision = self.gate.tick(now_s=now)
        self._last_block_reason = decision.reason
        if not decision.allowed:
            self._publish_zero()

    def _publish_zero(self) -> None:
        out = self.Twist()
        self.gated_pub.publish(out)

    def _applied_evidence_ready(self) -> bool:
        reader = getattr(getattr(self, "adapter", None), "applied_reader", None)
        if reader is None:
            return True
        try:
            snapshot = reader.read()
            if snapshot.run_id != str(self.config.get("run_id")):
                self._fault("applied_snapshot_run_mismatch", snapshot.run_id)
                return False
            expected_epoch = int(self.config.get("run_epoch_ns", 0))
            if expected_epoch and snapshot.run_epoch_ns != expected_epoch:
                self._fault("applied_snapshot_epoch_mismatch", str(snapshot.run_epoch_ns))
                return False
            return True
        except Exception as exc:
            self._fault("applied_snapshot_unready", str(exc))
            return False

    def _valid_body_pose_header(self, msg: Any) -> bool:
        header = getattr(msg, "header", None)
        frame_id = str(getattr(header, "frame_id", "")) if header is not None else ""
        expected_frame = str(self.config.get("map", {}).get("frame_id", "world"))
        if frame_id and frame_id != expected_frame:
            self.gate.close("invalid_body_pose_frame")
            self._fault("invalid_body_pose_frame", frame_id)
            return False
        stamp = getattr(header, "stamp", None) if header is not None else None
        if stamp is None:
            self.gate.close("missing_body_pose_stamp")
            self._fault("missing_body_pose_stamp", "")
            return False
        stamp_ns = int(getattr(stamp, "sec", 0)) * 1000000000 + int(getattr(stamp, "nanosec", 0))
        if stamp_ns <= 0:
            self.gate.close("missing_body_pose_stamp")
            self._fault("missing_body_pose_stamp", str(stamp_ns))
            return False
        if self._last_odom_stamp_ns is not None and stamp_ns <= self._last_odom_stamp_ns:
            self.gate.close("stale_body_pose_stamp")
            self._fault("stale_body_pose_stamp", str(stamp_ns))
            return False
        self._last_odom_stamp_ns = stamp_ns
        return True

    def _fault(self, kind: str, message: str) -> None:
        row = {"monotonic_s": time.monotonic(), "kind": kind, "message": message}
        self._faults.append(row)
        try:
            self.node.get_logger().warn("P2B_BACKEND_ROS_FAULT " + json.dumps(row, sort_keys=True))
        except Exception:
            pass

    def _track_owner_change(self, owner: CommandIdentity) -> None:
        key = tuple(owner.to_dict().items())
        if key != self._active_owner_key:
            self._active_owner_key = key
            self._owner_admitted_s = time.monotonic()
            self._owner_first_heartbeat_s = None

    def _mark_owner_admitted(self, identity: CommandIdentity) -> None:
        self._active_owner_key = tuple(identity.to_dict().items())
        self._owner_admitted_s = time.monotonic()
        self._owner_first_heartbeat_s = None

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
            run_id=str(msg.run_id),
            epoch=int(msg.epoch),
            request_id=str(msg.request_id),
            goal_id=str(msg.goal_id),
            route_id=str(msg.route_id),
            command_id=str(msg.command_id),
            generation=int(msg.generation),
            map_epoch=str(msg.map_epoch),
            map_revision=int(msg.map_revision),
        )


class LayeredPctClient:
    def __init__(self, inner: PctIpcClient, pct_layer: Optional[int]) -> None:
        self.inner = inner
        self.pct_layer = pct_layer
        self._history = []  # type: List[Dict[str, Any]]
        self._lock = threading.Lock()

    def plan(self, request: Any) -> Any:
        if self.pct_layer is None:
            forwarded = request
        else:
            start_layer = getattr(request, "start_layer", None)
            target_layer = getattr(request, "target_layer", None)
            if start_layer is None or target_layer is None:
                forwarded = dataclasses.replace(
                    request,
                    start_layer=self.pct_layer if start_layer is None else start_layer,
                    target_layer=self.pct_layer if target_layer is None else target_layer,
                )
            else:
                forwarded = request
        started = time.monotonic()
        record = {
            "request_id": getattr(forwarded, "request_id", None),
            "goal_id": getattr(forwarded, "goal_id", None),
            "started_monotonic_s": started,
            "request": forwarded.to_wire() if hasattr(forwarded, "to_wire") else repr(forwarded),
        }
        try:
            route = self.inner.plan(forwarded)
            record.update({
                "ok": True,
                "elapsed_s": time.monotonic() - started,
                "route_id": getattr(route, "route_id", None),
                "waypoints_m": [list(point) for point in getattr(route, "waypoints_m", ())],
                "planner": getattr(route, "planner", None),
                "z_semantics": getattr(route, "z_semantics", None),
            })
            return route
        except Exception as exc:
            record.update({"ok": False, "elapsed_s": time.monotonic() - started, "error": str(exc)})
            raise
        finally:
            with self._lock:
                self._history.append(record)
                self._history = self._history[-50:]

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "configured_pct_layer": self.pct_layer,
                "plan_history": list(self._history),
            }


def build_runtime(node: Any, config: Mapping[str, Any]) -> NavigationHttpRuntime:
    gate_dict = dict(config.get("gate", {}))
    gate_dict.pop("initial_heartbeat_grace_s", None)
    gate = CommandGate(GateConfig(**gate_dict))
    scan_port = RosScanPort(node, config, gate)
    pct = config.get("pct_worker", {})
    pct_client = PctIpcClient(PctIpcClientConfig(
        host=str(pct.get("host", "127.0.0.1")),
        port=int(pct.get("port", 47631)),
        connect_timeout_s=float(pct.get("connect_timeout_s", 0.20)),
        response_timeout_s=float(pct.get("response_timeout_s", 5.0)),
    ))
    applied = config.get("applied_evidence", {})
    reader = None
    if applied.get("current_command_path"):
        reader = AppliedEvidenceReader(pathlib.Path(str(applied.get("current_command_path"))))
    stop_cfg = StopEvidenceConfig(
        stop_command_norm=float(applied.get("stop_command_norm", 0.01)),
        stop_speed_mps=float(applied.get("stop_speed_mps", 0.10)),
        stop_yaw_rate_radps=float(applied.get("stop_yaw_rate_radps", 0.15)),
        stop_dwell_sim_seconds=float(applied.get("stop_dwell_sim_seconds", 1.0)),
    )
    map_cfg = config.get("map", {})
    pct_layer_value = map_cfg.get("pct_layer")
    pct_layer = None if pct_layer_value is None else int(pct_layer_value)
    adapter = P2BBackendAdapter(
        LayeredPctClient(pct_client, pct_layer),
        scan_port,
        gate,
        scan_port.pct_start_provider,
        frame_id=str(map_cfg.get("frame_id", "world")),
        optimize=bool(pct.get("optimize", True)),
        applied_reader=reader,
        expected_run_epoch_ns=int(config.get("run_epoch_ns", 0)) or None,
        stop_evidence_config=stop_cfg,
    )
    scan_port.adapter = adapter
    p2a = load_p2a_core()
    service_cfg = config.get("service", {})
    service = p2a.PersistentNavigationService(
        str(config.get("run_id", "p2b-run")),
        str(map_cfg.get("epoch", "map")),
        int(map_cfg.get("revision", 0)),
        backend=adapter,
        max_evidence_age_s=float(service_cfg.get("max_evidence_age_s", 10.0)),
        command_timeout_s=float(service_cfg.get("command_timeout_s", 45.0)),
    )
    return NavigationHttpRuntime(service, adapter, scan_port, config)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run P2B Foxy ROS adapter with localhost HTTP API")
    parser.add_argument("--config", type=pathlib.Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--run-epoch-ns", type=int)
    parser.add_argument("--applied-snapshot")
    parser.add_argument("--finish-request")
    parser.add_argument("--pct-port", type=int)
    parser.add_argument("--http-port", type=int)
    parser.add_argument("--print-contract", action="store_true")
    args, ros_args = parser.parse_known_args(argv)
    overrides: Dict[str, Any] = {}
    if args.run_id:
        overrides["run_id"] = args.run_id
    if args.run_epoch_ns:
        overrides["run_epoch_ns"] = args.run_epoch_ns
    if args.applied_snapshot:
        overrides.setdefault("applied_evidence", {})["current_command_path"] = args.applied_snapshot
    if args.finish_request:
        overrides.setdefault("applied_evidence", {})["finish_request_path"] = args.finish_request
    if args.pct_port:
        overrides.setdefault("pct_worker", {})["port"] = args.pct_port
    if args.http_port:
        overrides.setdefault("http", {})["port"] = args.http_port
    config = load_runtime_config(args.config, overrides)
    if args.print_contract:
        import json
        print(json.dumps(render_wire_contract(config), indent=2, sort_keys=True))
        return 0
    import rclpy
    from rclpy.executors import MultiThreadedExecutor
    rclpy.init(args=ros_args or None)
    node = rclpy.create_node("p2b_backend_ros")
    runtime = build_runtime(node, config)
    http = config.get("http", {})
    server = start_http_server(runtime, str(http.get("host", "127.0.0.1")), int(http.get("port", 8765)))
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    finally:
        server.shutdown()
        runtime.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
