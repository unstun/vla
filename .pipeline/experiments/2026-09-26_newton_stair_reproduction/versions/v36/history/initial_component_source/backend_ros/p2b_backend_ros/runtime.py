"""HTTP runtime and pure-Python helpers for the P2B ROS binding."""

from __future__ import annotations

import json
import math
import pathlib
import threading
import time
import uuid
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, Mapping, Optional, Sequence, Tuple

from backend_adapter.applied_evidence import finish_request_payload
from backend_adapter.contracts import ContractError, MeasuredState, PlannerRequest, require_finite, require_identifier, require_int
from backend_adapter.p2a_bridge import load_p2a_core
from .navigation_contract import PeriodicDeadline, normalize_yaw, positive_finite


@dataclass(frozen=True)
class GoalWire:
    request_id: str
    goal_id: str
    target_ground_xyz: Tuple[float, float, float]
    frame_id: str
    map_epoch: str
    map_revision: int
    observation_id: str
    target_yaw_rad: Optional[float] = None


class TerminalLedger:
    def __init__(self, max_records: int = 200, clock: Callable[[], float] = time.monotonic) -> None:
        self.max_records = max_records
        self.clock = clock
        self._records = []
        self._lock = threading.Lock()

    def append(self, request_id: str, goal_id: str, status: str, cause: str, route_id: Optional[str] = None, data: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
        record = {
            "seq": 0,
            "monotonic_s": self.clock(),
            "request_id": request_id,
            "goal_id": goal_id,
            "status": status,
            "cause": cause,
            "route_id": route_id,
            "data": dict(data or {}),
        }
        with self._lock:
            record["seq"] = len(self._records) + 1
            self._records.append(record)
            if len(self._records) > self.max_records:
                self._records = self._records[-self.max_records:]
        return record

    def snapshot(self):
        with self._lock:
            return list(self._records)

    def latest_for(self, request_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            for record in reversed(self._records):
                if record["request_id"] == request_id:
                    return dict(record)
        return None


@dataclass
class StopFlow:
    flow_id: str
    request_id: str
    goal_id: str
    route_id: str
    command_id: str
    intent: str
    reason: str
    started_monotonic_s: float
    status: str = "pending"
    message: str = ""


@dataclass(frozen=True)
class RequestedTarget:
    request_id: str
    goal_id: str
    route_id: str
    command_id: str
    ground_xyz: Tuple[float, float, float]
    body_xyz: Tuple[float, float, float]


STOP_PRIORITY = {"arrival": 1, "fault": 2, "cancel": 3}


def parse_goal_payload(payload: Mapping[str, Any], config: Mapping[str, Any]) -> GoalWire:
    request_id = require_identifier("request_id", payload.get("request_id"))
    goal_id = require_identifier("goal_id", payload.get("goal_id"))
    target = _target_xyz(payload)
    frame_id = require_identifier("frame", payload.get("frame", payload.get("frame_id", config.get("map", {}).get("frame_id", "world"))))
    map_epoch = require_identifier("map_epoch", payload.get("map_epoch", config.get("map", {}).get("epoch")))
    map_revision = require_int("map_revision", payload.get("map_revision", config.get("map", {}).get("revision")), 0)
    observation_id = str(payload.get("observation_id", request_id))
    require_identifier("observation_id", observation_id)
    yaw = payload.get("target_yaw_rad")
    return GoalWire(request_id, goal_id, target, frame_id, map_epoch, map_revision, observation_id,
                    None if yaw is None else normalize_yaw(yaw))


def make_p2a_request(goal: GoalWire, p2a: Any, now_s: float) -> Any:
    return p2a.GoalRequest(
        request_id=goal.request_id,
        goal_id=goal.goal_id,
        target=p2a.SpatialTarget(
            goal.target_ground_xyz[0],
            goal.target_ground_xyz[1],
            goal.target_ground_xyz[2],
            None,
            goal.frame_id,
            "m",
        ),
        evidence=p2a.EvidenceSnapshot(
            goal.observation_id,
            now_s,
            goal.frame_id,
            "m",
            goal.map_epoch,
            goal.map_revision,
            1,
            True,
            "diagnostic_sim_truth_http",
        ),
        model_arguments={"source": "p2b_http", "target_semantics": "ground_xyz"},
    )


def pct_start_from_body_pose(body: MeasuredState, nominal_height_m: float) -> MeasuredState:
    return MeasuredState(
        state_sequence=body.state_sequence,
        monotonic_s=body.monotonic_s,
        position_world_m=(
            body.position_world_m[0],
            body.position_world_m[1],
            body.position_world_m[2] - float(nominal_height_m),
        ),
        velocity_world_mps=body.velocity_world_mps,
        map_epoch=body.map_epoch,
        map_revision=body.map_revision,
        source="diagnostic_sim_truth_ground_start_from_body_pose_minus_nominal_height",
    )


class NavigationHttpRuntime:
    def __init__(
        self,
        service: Any,
        adapter: Any,
        scan_port: Any,
        config: Mapping[str, Any],
        write_finish_request: bool = False,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.service = service
        self.adapter = adapter
        self.scan_port = scan_port
        self.config = dict(config)
        self.write_finish_request = write_finish_request
        self.clock = clock
        self.p2a = load_p2a_core()
        self.ledger = TerminalLedger(clock=clock)
        self.jobs = {}
        self.last_error = None
        self.stop_flow_errors = []
        self.requested_targets = {}  # type: Dict[str, RequestedTarget]
        self._lock = threading.Lock()
        self._stop_flow = None  # type: Optional[StopFlow]
        self._stop_flow_lock = threading.Lock()
        arrival = self.config.get("arrival", {})
        self._arrival_tolerance_xy = float(arrival.get("xy_tolerance_m", 0.25))
        self._arrival_tolerance_z = float(arrival.get("z_tolerance_m", 0.20))
        self._arrival_tolerance_yaw = positive_finite(arrival.get("yaw_tolerance_rad", 0.25), "yaw_tolerance_rad")
        self._monitor_period_s = positive_finite(arrival.get("monitor_period_s", 1/30), "monitor_period_s")
        self._global_frequency = positive_finite(self.config.get("navigation", {}).get("global_planner_frequency", 1.0), "global_planner_frequency")
        self._global_schedule = PeriodicDeadline(self._global_frequency)
        self._global_history = []
        self._global_owner_key = None
        self._stop = False
        self._monitor_thread = threading.Thread(target=self._monitor_arrival, name="p2b-arrival-monitor", daemon=True)
        self._monitor_thread.start()
        self._global_thread = threading.Thread(target=self._monitor_global, name="p2b-global-refresh", daemon=True)
        self._global_thread.start()

    def submit_goal(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        goal = parse_goal_payload(payload, self.config)
        self.scan_port.set_goal_pose_request(goal)
        job_id = str(uuid.uuid4())
        with self._lock:
            self.jobs[job_id] = {"status": "planning", "request_id": goal.request_id, "goal_id": goal.goal_id}
        thread = threading.Thread(target=self._goal_worker, args=(job_id, goal), name="p2b-goal-%s" % goal.goal_id, daemon=True)
        thread.start()
        return {"ok": True, "status": "planning", "job_id": job_id, "request_id": goal.request_id, "goal_id": goal.goal_id}

    def cancel(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        reason = str(payload.get("reason", "http_cancel"))
        owner = getattr(self.service, "active_owner", None)
        if owner is None:
            return {"ok": True, "status": "ok", "data": {"terminal_cause": "no_active_command"}}
        # Do not call service.cancel_active here: the accepted P2A core invokes a
        # synchronous backend stop once and returns pending on low real-time
        # dwell.  The runtime owns the persistent completion flow.
        return self._request_stop_flow(owner, "cancel", reason)

    def state(self) -> Dict[str, Any]:
        measurement = None
        pct_start = None
        try:
            body = self.scan_port.measurement_provider()
            measurement = _measurement_dict(body)
            pct_start = _measurement_dict(pct_start_from_body_pose(body, self._nominal_height()))
        except Exception:
            pass
        with self._lock:
            jobs = {k: dict(v) for k, v in self.jobs.items()}
        owner = getattr(self.service, "active_owner", None)
        return {
            "ok": True,
            "readiness": {
                "body_pose_ready": measurement is not None,
                "http_ready": True,
                "applied_snapshot": self._applied_snapshot_readiness(),
                "active_owner_present": owner is not None,
                "last_error": self.last_error,
            },
            "service": self.service.state(),
            "jobs": jobs,
            "terminal_results": self.ledger.snapshot()[-50:],
            "measurement_body_pose": measurement,
            "pct_start_ground_pose": pct_start,
            "pct": self._pct_snapshot(),
            "gate": self.adapter.gate.snapshot(),
            "scan_port": self.scan_port.snapshot(),
            "stop_flow": None if self._stop_flow is None else dict(self._stop_flow.__dict__),
            "stop_flow_errors": list(self.stop_flow_errors[-20:]),
            "navigation_contract": dict(self.config.get("navigation", {})),
            "global_refresh": {"frequency_hz": self._global_frequency, "clock": "monotonic_wall",
                "skipped_slots": self._global_schedule.skipped_slots, "history": list(self._global_history[-50:])},
            "run_id": self.config.get("run_id"),
            "run_epoch_ns": self.config.get("run_epoch_ns"),
        }

    def shutdown(self) -> None:
        self._stop = True
        self._monitor_thread.join(timeout=1.0)
        self._global_thread.join(timeout=1.0)

    def _refresh_context(self, owner: Any) -> Any:
        current = getattr(self.service, "active_owner", None)
        if (self._stop or current is not owner or self._pending_stop_flow(owner) is not None or
                self.adapter.gate.cancel_pending or self.adapter.gate.closed_reason != "open"):
            return None
        identity = self.adapter._identity_from_p2a_command(owner.command)
        gate_owner = self.adapter.gate.owner
        if gate_owner is None or not gate_owner.matches(identity):
            return None
        target = self._requested_target(owner)
        return None if target is None else (identity, target)

    def _monitor_global(self) -> None:
        while not self._stop:
            time.sleep(min(0.01, 0.1 / self._global_frequency))
            owner = getattr(self.service, "active_owner", None)
            if owner is None:
                self._global_owner_key = None
                continue
            key = (owner.request_id, owner.goal_id, owner.command_id, owner.route_id)
            if key != self._global_owner_key:
                self._global_owner_key = key
                self._global_schedule = PeriodicDeadline(self._global_frequency)
            if not self._global_schedule.due(self.clock()):
                continue
            self._refresh_global_once(owner)

    def _refresh_global_once(self, owner: Any) -> None:
        context = self._refresh_context(owner)
        if context is None:
            return
        identity, target = context
        started = self.clock()
        record = {"started_wall_s": started, "command_id": owner.command_id, "generation": identity.generation,
                  "active_route_id": owner.route_id, "status": "planning"}
        try:
            body = self.scan_port.pct_start_provider()
            if body.map_epoch != identity.map_epoch or body.map_revision != identity.map_revision:
                raise RuntimeError("global_refresh_measured_map_mismatch")
            request = PlannerRequest(owner.request_id, owner.goal_id, body.position_world_m, target.ground_xyz,
                self.adapter.frame_id, identity.map_epoch, identity.map_revision, optimize=self.adapter.optimize)
            route = self.adapter.pct_client.plan(request)
            record["computed_route_id"] = route.route_id
            # Planning may finish after cancel, preemption, timeout or arrival.
            if self._refresh_context(owner) is None:
                record["status"] = "discarded_owner_changed_or_stopping"
            else:
                record["status"] = "published" if self.scan_port.refresh_route(identity, route) else "discarded_gate_closed"
        except Exception as exc:
            record.update(status="failed", error=str(exc))
            if self._refresh_context(owner) is not None:
                self._request_stop_flow(owner, "fault", "global_refresh_failed:" + str(exc))
        finally:
            record["elapsed_wall_s"] = self.clock() - started
            record["overrun"] = record["elapsed_wall_s"] > 1 / self._global_frequency
            self._global_history.append(record)
            self._global_history = self._global_history[-50:]

    def _goal_worker(self, job_id: str, goal: GoalWire) -> None:
        try:
            timeout_s = float(self.config.get("service", {}).get("body_ready_timeout_s", 5.0))
            if not self.scan_port.wait_body_ready(timeout_s):
                raise RuntimeError("body_pose_not_ready")
            readiness = self._applied_snapshot_readiness()
            if readiness["configured"] and not readiness["ready"]:
                raise RuntimeError(readiness["error"] or "applied_snapshot_not_ready")
            request = make_p2a_request(goal, self.p2a, self.clock())
            result = self.service.submit_goal(request)
            route_id = None
            command_id = None
            if isinstance(result.get("data"), dict):
                route_id = result["data"].get("route_id")
                command_id = result["data"].get("command_id")
            if result.get("ok"):
                status = result.get("status", "accepted")
                if route_id and command_id:
                    self._remember_requested_target(goal, str(route_id), str(command_id))
            else:
                status = result.get("status", "rejected")
                self.ledger.append(goal.request_id, goal.goal_id, status, result.get("error", status), route_id, result)
            with self._lock:
                self.jobs[job_id].update({"status": status, "result": result})
        except Exception as exc:
            self.last_error = str(exc)
            self.ledger.append(goal.request_id, goal.goal_id, "failed", str(exc))
            with self._lock:
                self.jobs.setdefault(job_id, {"request_id": goal.request_id, "goal_id": goal.goal_id}).update({"status": "failed", "error": str(exc)})

    def _monitor_arrival(self) -> None:
        while not self._stop:
            time.sleep(self._monitor_period_s)
            owner = getattr(self.service, "active_owner", None)
            if owner is None or self.adapter.gate.owner is None:
                continue
            fault = _gate_fault_reason(self.adapter.gate.snapshot())
            if fault:
                if self._is_expected_pending_stop_closure(owner, fault):
                    continue
                self._request_stop_flow(owner, "fault", fault)
                continue
            if self._pending_stop_flow(owner) is not None:
                continue
            timeout_s = float(self.config.get("service", {}).get("command_timeout_s", 45.0))
            if self.clock() - float(owner.started_monotonic_s) > timeout_s:
                self._request_stop_flow(owner, "fault", "command_timeout")
                continue
            try:
                measurement = self.scan_port.measurement_provider()
            except Exception:
                continue
            readiness = self._applied_snapshot_readiness()
            if readiness["configured"] and not readiness["ready"]:
                continue
            requested = self._requested_target(owner)
            if requested is None:
                continue
            if not _within_arrival(measurement.position_world_m, requested.body_xyz, self._arrival_tolerance_xy, self._arrival_tolerance_z):
                continue
            if not self._within_goal_yaw(owner):
                continue
            self._request_stop_flow(owner, "arrival", "arrived_hold")

    def _within_goal_yaw(self, owner: Any) -> bool:
        try:
            _, target_yaw = self.scan_port.goal_pose(owner)
            return abs(normalize_yaw(target_yaw - self.scan_port.measured_yaw())) <= self._arrival_tolerance_yaw
        except (KeyError, ValueError, RuntimeError):
            return False

    def _remember_requested_target(self, goal: GoalWire, route_id: str, command_id: str) -> None:
        ground = goal.target_ground_xyz
        body = (ground[0], ground[1], ground[2] + self._nominal_height())
        requested = RequestedTarget(goal.request_id, goal.goal_id, route_id, command_id, ground, body)
        with self._lock:
            self.requested_targets[route_id] = requested

    def _requested_target(self, owner: Any) -> Optional[RequestedTarget]:
        with self._lock:
            requested = self.requested_targets.get(owner.route_id)
        if requested is None:
            return None
        if requested.command_id != owner.command_id or requested.request_id != owner.request_id or requested.goal_id != owner.goal_id:
            return None
        return requested

    def _request_stop_flow(self, owner: Any, intent: str, reason: str) -> Dict[str, Any]:
        with self._stop_flow_lock:
            active = self._stop_flow
            if active is not None and active.command_id == owner.command_id and active.status == "pending":
                if STOP_PRIORITY[intent] > STOP_PRIORITY[active.intent]:
                    active.intent = intent
                    active.reason = reason
                    active.message = "intent_promoted"
                return {"ok": True, "status": "stop_pending", "flow_id": active.flow_id, "intent": active.intent}
            flow = StopFlow(
                flow_id=str(uuid.uuid4()),
                request_id=owner.request_id,
                goal_id=owner.goal_id,
                route_id=owner.route_id,
                command_id=owner.command_id,
                intent=intent,
                reason=reason,
                started_monotonic_s=self.clock(),
            )
            self._stop_flow = flow
        thread = threading.Thread(target=self._stop_worker, args=(owner, flow), name="p2b-stop-%s" % flow.goal_id, daemon=True)
        thread.start()
        return {"ok": True, "status": "stop_pending", "flow_id": flow.flow_id, "intent": intent}

    def _pending_stop_flow(self, owner: Any) -> Optional[StopFlow]:
        with self._stop_flow_lock:
            active = self._stop_flow
            if active is None or active.status != "pending":
                return None
            if active.command_id != owner.command_id or active.request_id != owner.request_id or active.goal_id != owner.goal_id or active.route_id != owner.route_id:
                return None
            return active

    def _is_expected_pending_stop_closure(self, owner: Any, closed_reason: str) -> bool:
        active = self._pending_stop_flow(owner)
        if active is None:
            return False
        return closed_reason == active.reason

    def _stop_worker(self, owner: Any, flow: StopFlow) -> None:
        try:
            timeout_s = float(self.config.get("service", {}).get("stop_completion_timeout_s", self.config.get("service", {}).get("command_timeout_s", 45.0)))
            deadline = self.clock() + timeout_s
            outcome = self.adapter.stop(owner.command, flow.reason)
            last_pending = getattr(outcome, "message", "") or getattr(outcome, "status", "stop_waiting")
            while self.clock() <= deadline and not self._stop:
                status = getattr(outcome, "status", "")
                if status == "stopped":
                    self.adapter.gate.clear_owner_if_quiescent()
                    self._finish_stop_flow(owner, flow)
                    return
                if status not in {"pending", "uncertain"}:
                    raise RuntimeError(getattr(outcome, "message", "") or status or "stop_failed")
                last_pending = getattr(outcome, "message", "") or status or "stop_waiting"
                time.sleep(0.02)
                poll_stop = getattr(self.adapter, "poll_stop", None)
                if poll_stop is None:
                    outcome = self.adapter.stop(owner.command, flow.reason)
                else:
                    outcome = poll_stop(owner.command)
            raise TimeoutError(last_pending)
        except Exception as exc:
            flow.status = "failed"
            flow.message = str(exc)
            self.last_error = str(exc)
            self.stop_flow_errors.append({
                "monotonic_s": self.clock(),
                "flow_id": flow.flow_id,
                "request_id": flow.request_id,
                "goal_id": flow.goal_id,
                "intent": flow.intent,
                "error": str(exc),
            })

    def _finish_stop_flow(self, owner: Any, flow: StopFlow) -> None:
        terminal_status = {"arrival": "arrived", "cancel": "cancelled", "fault": "stopped"}[flow.intent]
        terminal_message = {
            "arrival": "arrived_after_quiescence",
            "cancel": flow.reason or "cancelled_after_quiescence",
            "fault": flow.reason or "gate_fault_after_quiescence",
        }[flow.intent]
        ledger_status = terminal_status
        if flow.intent == "arrival":
            geometry_error = self._arrival_geometry_error(owner)
            if geometry_error is not None:
                terminal_status = "stopped"
                ledger_status = "stopped"
                terminal_message = geometry_error
        elif flow.intent == "fault":
            ledger_status = "failed"
        feedback = self.p2a.Feedback(
            run_id=owner.command.run_id,
            epoch=owner.command.epoch,
            goal_id=owner.goal_id,
            route_id=owner.route_id,
            command_id=owner.command_id,
            feedback_seq=owner.last_feedback_seq + 1,
            status=terminal_status,
            message=terminal_message,
            map_epoch=self.service.map_epoch,
            map_revision=self.service.map_revision,
        )
        result = self.service.receive_feedback(feedback)
        if result.get("ok"):
            flow.status = "complete"
            flow.message = terminal_message
            record = self.ledger.append(owner.request_id, owner.goal_id, ledger_status, terminal_message, owner.route_id, result)
            if self.write_finish_request and ledger_status in {"arrived", "failed", "stopped"}:
                self._write_finish(record, "FINISHED" if ledger_status == "arrived" else "FAILED")
        else:
            flow.status = "feedback_rejected"
            flow.message = str(result.get("error", result.get("status", "feedback_rejected")))
            self.stop_flow_errors.append({
                "monotonic_s": self.clock(),
                "flow_id": flow.flow_id,
                "request_id": flow.request_id,
                "goal_id": flow.goal_id,
                "intent": flow.intent,
                "error": flow.message,
            })

    def _arrival_geometry_error(self, owner: Any) -> Optional[str]:
        requested = self._requested_target(owner)
        if requested is None:
            return "arrival_requested_target_missing_after_stop"
        try:
            measurement = self.scan_port.measurement_provider()
        except Exception as exc:
            return "arrival_measurement_missing_after_stop:%s" % exc
        if (_within_arrival(measurement.position_world_m, requested.body_xyz, self._arrival_tolerance_xy, self._arrival_tolerance_z)
                and self._within_goal_yaw(owner)):
            return None
        return "arrival_pose_drift_after_stop"

    def _write_finish(self, record: Mapping[str, Any], status: str) -> None:
        path_s = str(self.config.get("applied_evidence", {}).get("finish_request_path", ""))
        if not path_s:
            return
        payload = finish_request_payload(
            str(self.config.get("run_id")),
            str(record["request_id"]),
            int(self.config.get("run_epoch_ns")),
            status,
        )
        path = pathlib.Path(path_s)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)

    def _nominal_height(self) -> float:
        return float(self.config.get("map", {}).get("nominal_body_height_m", 0.35))

    def _applied_snapshot_readiness(self) -> Dict[str, Any]:
        reader = getattr(self.adapter, "applied_reader", None)
        if reader is None:
            return {"configured": False, "ready": False, "path": None, "error": "not_configured"}
        try:
            snapshot = reader.read()
            expected_run_id = str(self.config.get("run_id", ""))
            if snapshot.run_id != expected_run_id:
                return {"configured": True, "ready": False, "path": str(reader.path), "error": "applied_snapshot_run_mismatch"}
            expected_epoch = int(self.config.get("run_epoch_ns", 0))
            if expected_epoch and snapshot.run_epoch_ns != expected_epoch:
                return {"configured": True, "ready": False, "path": str(reader.path), "error": "applied_snapshot_epoch_mismatch"}
            return {"configured": True, "ready": True, "path": str(reader.path), "error": None}
        except Exception as exc:
            return {"configured": True, "ready": False, "path": str(reader.path), "error": str(exc)}

    def _pct_snapshot(self) -> Dict[str, Any]:
        pct_client = getattr(self.adapter, "pct_client", None)
        snapshot = getattr(pct_client, "snapshot", None)
        if snapshot is None:
            return {"plan_history": []}
        try:
            return dict(snapshot())
        except Exception as exc:
            return {"plan_history": [], "error": str(exc)}


def make_http_handler(runtime: NavigationHttpRuntime):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, data: Mapping[str, Any]) -> None:
            raw = json.dumps(data, sort_keys=True).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _read_json(self) -> Dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
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


def start_http_server(runtime: NavigationHttpRuntime, host: str, port: int) -> ThreadingHTTPServer:
    if host not in {"127.0.0.1", "localhost"}:
        raise ValueError("http_host_must_be_loopback")
    server = ThreadingHTTPServer((host, int(port)), make_http_handler(runtime))
    thread = threading.Thread(target=server.serve_forever, name="p2b-http", daemon=True)
    thread.start()
    return server


def _target_xyz(payload: Mapping[str, Any]) -> Tuple[float, float, float]:
    values = payload.get("target_ground_xyz")
    if values is None:
        target = payload.get("target")
        if not isinstance(target, Mapping):
            raise ContractError("invalid_target_ground_xyz")
        values = [target.get("x_m"), target.get("y_m"), target.get("z_m")]
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) != 3:
        raise ContractError("invalid_target_ground_xyz")
    return (
        require_finite("target_ground_x_m", values[0]),
        require_finite("target_ground_y_m", values[1]),
        require_finite("target_ground_z_m", values[2]),
    )


def _within_arrival(position: Tuple[float, float, float], target: Tuple[float, float, float], xy_tol: float, z_tol: float) -> bool:
    dx = position[0] - target[0]
    dy = position[1] - target[1]
    dz = position[2] - target[2]
    return math.hypot(dx, dy) <= xy_tol and abs(dz) <= z_tol


def _gate_fault_reason(snapshot: Mapping[str, Any]) -> Optional[str]:
    reason = snapshot.get("closed_reason")
    if reason in {None, "open", "no_owner", "consumer_hold_confirmed"}:
        return None
    if str(reason).startswith("cancel"):
        return None
    return str(reason)


def _measurement_dict(state: MeasuredState) -> Dict[str, Any]:
    return {
        "state_sequence": state.state_sequence,
        "monotonic_s": state.monotonic_s,
        "position_world_m": list(state.position_world_m),
        "velocity_world_mps": list(state.velocity_world_mps),
        "horizontal_speed_mps": state.horizontal_speed_mps,
        "map_epoch": state.map_epoch,
        "map_revision": state.map_revision,
        "source": state.source,
    }
