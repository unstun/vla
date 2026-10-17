"""P2A backend port backed by native PCT IPC, SCAN admission and command gate."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from .contracts import CommandIdentity, MeasuredState, NativeRoute, PlannerRequest, ScanAdmission
from .applied_evidence import AppliedEvidenceReader, StopEvidenceConfig, StopEvidenceWindow
from .control_gate import CommandGate
from .p2a_bridge import load_p2a_core
from .pct_ipc import PctIpcClient, PctIpcClientConfig, PlannerRejected, PlannerUnavailable
from .scan_wire import ScanPort, validate_stop_admission


@dataclass
class _StopState:
    identity: CommandIdentity
    reason: str
    stop_request_source_ns: int
    hold_confirmed: bool = False
    last_message: str = ""
    last_error: str = ""


class P2BBackendAdapter(load_p2a_core().NavigationBackendPort):  # type: ignore[misc]
    """Concrete P2A backend port.

    `plan_route` makes a bounded IPC request to the separate native PCT worker.
    Production launch should normally perform slow PCT work outside the P2A
    service lock, then call the lifecycle core with a route cached in this
    adapter.  The direct call remains bounded by `PctIpcClientConfig` and fails
    explicitly if no worker is available.
    """

    def __init__(
        self,
        pct_client: PctIpcClient,
        scan_port: ScanPort,
        gate: CommandGate,
        measurement_provider: Callable[[], MeasuredState],
        frame_id: str = "world",
        optimize: bool = True,
        clock: Callable[[], float] = time.monotonic,
        applied_reader: Optional[AppliedEvidenceReader] = None,
        expected_run_epoch_ns: Optional[int] = None,
        stop_evidence_config: Optional[StopEvidenceConfig] = None,
    ) -> None:
        self.pct_client = pct_client
        self.scan_port = scan_port
        self.gate = gate
        self.measurement_provider = measurement_provider
        self.frame_id = frame_id
        self.optimize = optimize
        self.clock = clock
        self.applied_reader = applied_reader
        self.expected_run_epoch_ns = expected_run_epoch_ns
        self.stop_evidence_config = stop_evidence_config or StopEvidenceConfig()
        self.stop_evidence_window = StopEvidenceWindow(self.stop_evidence_config)
        self._prepared_route = None  # type: Optional[NativeRoute]
        self._generation = 0
        self._route_revisions = {}
        self._command_identities = {}  # type: Dict[Tuple[str, int, str, str, str, str], CommandIdentity]
        self._stop_states = {}  # type: Dict[Tuple[str, int, str, str, str, str], _StopState]
        self.route_targets = {}
        self.p2a = load_p2a_core()

    def prepare_route(self, request_id: str, route: NativeRoute) -> None:
        self._prepared_route = route

    def plan_route(self, run_id: str, epoch: int, request: Any) -> Any:
        current = self.measurement_provider()
        if current.map_epoch != request.evidence.map_epoch or current.map_revision != request.evidence.map_revision:
            raise self.p2a.NavigationRejected("measured_map_mismatch")
        if self._prepared_route is not None:
            route = self._prepared_route
            self._prepared_route = None
            if route.goal_id != request.goal_id:
                raise self.p2a.NavigationRejected("prepared_route_goal_mismatch")
            return self._to_p2a_route(route)
        planner_request = PlannerRequest(
            request_id=request.request_id,
            goal_id=request.goal_id,
            start_xyz_m=current.position_world_m,
            target_xyz_m=(request.target.x_m, request.target.y_m, request.target.z_m),
            frame_id=request.target.frame_id or self.frame_id,
            map_epoch=request.evidence.map_epoch,
            map_revision=request.evidence.map_revision,
            optimize=self.optimize,
        )
        native_route = self.pct_client.plan(planner_request)
        return self._to_p2a_route(native_route)

    def submit_route(self, command: Any, route: Any) -> Any:
        self._generation += 1
        identity = self._identity_from_p2a(command, route, self._generation)
        self._command_identities[self._command_key(command)] = identity
        native_route = self._native_from_p2a(route)
        admission = self.scan_port.submit_route(identity, native_route)
        if not isinstance(admission, ScanAdmission):
            return self.p2a.BackendOutcome("uncertain", "malformed_scan_admission", route_id=route.route_id)
        if not admission.identity.matches(identity):
            return self.p2a.BackendOutcome("uncertain", "scan_admission_identity_mismatch", route_id=route.route_id)
        if admission.status == "accepted":
            self.gate.admit(identity)
            return self.p2a.BackendOutcome("accepted", admission.message, route_id=route.route_id)
        if admission.status == "rejected":
            return self.p2a.BackendOutcome("rejected", admission.message, route_id=route.route_id)
        if admission.status == "pending":
            return self.p2a.BackendOutcome("pending", admission.message, route_id=route.route_id)
        return self.p2a.BackendOutcome("uncertain", admission.message or "scan_submit_uncertain", route_id=route.route_id)

    def stop(self, command: Any, reason: str) -> Any:
        identity = self._identity_from_p2a_command(command)
        key = self._command_key(command)
        state = self._stop_states.get(key)
        if state is None:
            self.gate.request_cancel(identity, reason)
            state = _StopState(identity=identity, reason=reason, stop_request_source_ns=time.monotonic_ns())
            self._stop_states[key] = state
            try:
                admission = self.scan_port.request_stop(identity, reason)
            except Exception as exc:
                state.last_error = str(exc)
                return self.p2a.BackendOutcome("uncertain", str(exc), route_id=command.route_id)
            outcome = self._consume_stop_admission(command, state, admission)
            if outcome.status not in {"pending", "stopped"}:
                return outcome
        return self._evaluate_stop_state(command, state)

    def poll_stop(self, command: Any) -> Any:
        key = self._command_key(command)
        state = self._stop_states.get(key)
        if state is None:
            return self.p2a.BackendOutcome("pending", "stop_not_requested", route_id=command.route_id)
        return self._evaluate_stop_state(command, state)

    def _consume_stop_admission(self, command: Any, state: _StopState, admission: Any) -> Any:
        identity = state.identity
        if not isinstance(admission, ScanAdmission):
            state.last_error = "malformed_scan_stop"
            return self.p2a.BackendOutcome("uncertain", state.last_error, route_id=command.route_id)
        try:
            validate_stop_admission(admission, identity)
        except Exception as exc:
            state.last_error = str(exc)
            return self.p2a.BackendOutcome("uncertain", state.last_error, route_id=command.route_id)
        state.last_message = admission.message
        if admission.status == "stopped":
            state.hold_confirmed = True
            if self.gate.owner is not None:
                self.gate.confirm_consumer_hold(identity)
            if self.applied_reader is not None:
                self.stop_evidence_window.reset(state.stop_request_source_ns)
        elif admission.status == "pending":
            return self.p2a.BackendOutcome("pending", admission.message, route_id=command.route_id)
        else:
            state.last_error = admission.message or admission.status
            return self.p2a.BackendOutcome("uncertain", state.last_error, route_id=command.route_id)
        return self.p2a.BackendOutcome("pending", "stop_evidence_pending", route_id=command.route_id)

    def _evaluate_stop_state(self, command: Any, state: _StopState) -> Any:
        if not state.hold_confirmed:
            return self.p2a.BackendOutcome("pending", state.last_message or "controller_hold_pending", route_id=command.route_id)
        if self.applied_reader is not None:
            if self.expected_run_epoch_ns is None:
                return self.p2a.BackendOutcome("uncertain", "missing_expected_run_epoch_ns", route_id=command.route_id)
            try:
                snapshot = self.applied_reader.read()
                if not self.stop_evidence_window.observe(snapshot, command.run_id, self.expected_run_epoch_ns):
                    return self.p2a.BackendOutcome("pending", "applied_stop_evidence_pending", route_id=command.route_id)
            except Exception as exc:
                return self.p2a.BackendOutcome("pending", str(exc), route_id=command.route_id)
        elif not self.gate.stop_confirmed():
            return self.p2a.BackendOutcome("pending", "measured_stillness_pending", route_id=command.route_id)
        self._release_gate_owner_after_stop(state.identity)
        self._stop_states.pop(self._command_key(command), None)
        return self.p2a.BackendOutcome("stopped", state.last_message or "stop_confirmed", route_id=command.route_id)


    def _release_gate_owner_after_stop(self, identity: CommandIdentity) -> None:
        if self.gate.clear_owner_if_quiescent():
            return
        if self.applied_reader is not None and self.gate.owner is not None and self.gate.owner.matches(identity):
            self.gate.owner = None
            self.gate.closed_reason = "no_owner"
            self.gate.cancel_pending = False
            self.gate.hold_ack = False
            self.gate.still_since_s = None

    def _to_p2a_route(self, route: NativeRoute) -> Any:
        self._route_revisions[route.route_id] = route.map_revision
        self.route_targets[route.route_id] = route.waypoints_m[-1]
        return self.p2a.Route(
            route_id=route.route_id,
            goal_id=route.goal_id,
            frame_id=route.frame_id,
            map_epoch=route.map_epoch,
            waypoints_m=route.waypoints_m,
        )

    def _native_from_p2a(self, route: Any) -> NativeRoute:
        return NativeRoute(
            route_id=route.route_id,
            goal_id=route.goal_id,
            frame_id=route.frame_id,
            map_epoch=route.map_epoch,
            map_revision=self._route_revisions.get(route.route_id, 0),
            waypoints_m=tuple(tuple(p) for p in route.waypoints_m),
        )

    def _identity_from_p2a(self, command: Any, route: Any, generation: int) -> CommandIdentity:
        return CommandIdentity(
            run_id=command.run_id,
            epoch=command.epoch,
            request_id=command.request_id,
            goal_id=command.goal_id,
            route_id=command.route_id,
            command_id=command.command_id,
            generation=generation,
            map_epoch=route.map_epoch,
            map_revision=self._route_revisions.get(route.route_id, 0),
        )

    def _command_key(self, command: Any) -> Tuple[str, int, str, str, str, str]:
        return (command.run_id, command.epoch, command.request_id, command.goal_id, command.route_id, command.command_id)

    def _identity_from_p2a_command(self, command: Any) -> CommandIdentity:
        key = self._command_key(command)
        stored = self._command_identities.get(key)
        if stored is not None:
            return stored
        owner = self.gate.owner
        if owner is None:
            raise RuntimeError("command_identity_unknown")
        expected = key
        actual = (owner.run_id, owner.epoch, owner.request_id, owner.goal_id, owner.route_id, owner.command_id)
        if expected != actual:
            raise RuntimeError("active_gate_owner_mismatch")
        return owner
