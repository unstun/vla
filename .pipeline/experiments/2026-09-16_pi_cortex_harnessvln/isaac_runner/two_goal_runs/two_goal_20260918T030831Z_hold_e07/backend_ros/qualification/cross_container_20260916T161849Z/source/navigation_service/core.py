"""Persistent navigation goal lifecycle core.

This module is an interface contract around a future PCT/SCAN backend.  It does
not publish ROS messages, launch Isaac, or emulate robot motion.  Tests inject a
backend port explicitly; the default backend refuses execution.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


TERMINAL_FEEDBACK = {"arrived", "rejected", "failed", "cancelled", "stopped"}


class NavigationRejected(Exception):
    """Boundary validation or lifecycle rejection."""


class BackendUnavailable(Exception):
    """Raised when no real backend has been configured."""


@dataclass(frozen=True)
class EvidenceSnapshot:
    observation_id: str
    captured_monotonic_s: float
    frame_id: str
    units: str
    map_epoch: str
    map_revision: int
    localization_revision: int
    localization_valid: bool
    source: str


@dataclass(frozen=True)
class SpatialTarget:
    x_m: float
    y_m: float
    z_m: float
    yaw_rad: Optional[float]
    frame_id: str
    units: str


@dataclass(frozen=True)
class GoalRequest:
    request_id: str
    goal_id: str
    target: SpatialTarget
    evidence: EvidenceSnapshot
    model_arguments: Dict[str, Any]


@dataclass(frozen=True)
class Route:
    route_id: str
    goal_id: str
    frame_id: str
    map_epoch: str
    waypoints_m: Tuple[Tuple[float, float, float], ...]


@dataclass(frozen=True)
class BackendOutcome:
    status: str
    message: str = ""
    route_id: Optional[str] = None


@dataclass(frozen=True)
class BackendCommand:
    run_id: str
    epoch: int
    request_id: str
    goal_id: str
    route_id: str
    command_id: str


@dataclass(frozen=True)
class Feedback:
    run_id: str
    epoch: int
    goal_id: str
    route_id: str
    command_id: str
    feedback_seq: int
    status: str
    message: str = ""
    map_epoch: Optional[str] = None
    map_revision: Optional[int] = None


@dataclass
class CommandOwner:
    command: BackendCommand
    request_id: str
    goal_id: str
    route_id: str
    command_id: str
    status: str
    started_monotonic_s: float
    last_feedback_seq: int = 0
    terminal_cause: Optional[str] = None
    unresolved_reason: Optional[str] = None

    def identity(self) -> BackendCommand:
        return self.command


class NavigationBackendPort:
    """Explicit backend boundary for PCT route planning and SCAN submission."""

    def plan_route(
        self,
        run_id: str,
        epoch: int,
        request: GoalRequest,
    ) -> Route:
        raise BackendUnavailable("navigation_backend_unavailable")

    def submit_route(self, command: BackendCommand, route: Route) -> BackendOutcome:
        raise BackendUnavailable("navigation_backend_unavailable")

    def stop(self, command: BackendCommand, reason: str) -> BackendOutcome:
        raise BackendUnavailable("navigation_backend_unavailable")


class PersistentNavigationService:
    """One-owner lifecycle state machine for persistent navigation goals."""

    def __init__(
        self,
        run_id: str,
        map_epoch: str,
        map_revision: int,
        backend: Optional[NavigationBackendPort] = None,
        clock: Callable[[], float] = time.monotonic,
        max_evidence_age_s: float = 2.0,
        command_timeout_s: float = 30.0,
    ) -> None:
        if not isinstance(max_evidence_age_s, (int, float)) or not math.isfinite(max_evidence_age_s) or max_evidence_age_s < 0.0:
            raise ValueError("max_evidence_age_s_must_be_finite_nonnegative")
        if not isinstance(command_timeout_s, (int, float)) or not math.isfinite(command_timeout_s) or command_timeout_s < 0.0:
            raise ValueError("command_timeout_s_must_be_finite_nonnegative")
        self.run_id = run_id
        self.epoch = 1
        self.map_epoch = map_epoch
        self.map_revision = map_revision
        self.backend = backend or NavigationBackendPort()
        self.clock = clock
        self.max_evidence_age_s = max_evidence_age_s
        self.command_timeout_s = command_timeout_s
        self.active_owner = None  # type: Optional[CommandOwner]
        self.events = []  # type: List[Dict[str, Any]]
        self._cache = {}  # type: Dict[str, Tuple[str, Dict[str, Any]]]
        self._route_counter = 0
        self._lock = threading.RLock()
        self._admission_depth = 0

    def state(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "epoch": self.epoch,
            "map_epoch": self.map_epoch,
            "map_revision": self.map_revision,
            "active_owner": self._owner_projection(),
            "event_seq": len(self.events),
        }

    def submit_goal(self, request: GoalRequest) -> Dict[str, Any]:
        with self._lock:
            cached = self._cached_or_conflict(request)
            if cached is not None:
                return cached
            try:
                self._validate_request(request)
                if self.active_owner is not None or self._admission_depth:
                    raise NavigationRejected("command_owner_unresolved")
                self._admission_depth += 1
                try:
                    result = self._submit_validated(request)
                finally:
                    self._admission_depth -= 1
            except NavigationRejected as exc:
                result = self._result(False, "rejected", str(exc))
            if self._cacheable_result(result):
                self._save_cache(request, result)
            return result

    def replace_goal(self, request: GoalRequest, reason: str = "replace_goal") -> Dict[str, Any]:
        with self._lock:
            cached = self._cached_or_conflict(request)
            if cached is not None:
                return cached
            try:
                self._validate_request(request)
                if self._admission_depth:
                    raise NavigationRejected("command_owner_unresolved")
                if self.active_owner is not None:
                    stop_result = self.cancel_active(reason=reason)
                    if not stop_result["ok"]:
                        raise NavigationRejected(stop_result["error"])
                    self._validate_request(request)
                if self.active_owner is not None:
                    raise NavigationRejected("command_owner_unresolved")
                self._admission_depth += 1
                try:
                    result = self._submit_validated(request)
                finally:
                    self._admission_depth -= 1
            except NavigationRejected as exc:
                result = self._result(False, "rejected", str(exc))
            if self._cacheable_result(result):
                self._save_cache(request, result)
            return result

    def cancel_active(self, reason: str = "cancel_goal") -> Dict[str, Any]:
        with self._lock:
            return self._request_stop("cancel_goal" if reason == "cancel_goal" else reason)

    def receive_feedback(self, feedback: Feedback) -> Dict[str, Any]:
        with self._lock:
            owner = self.active_owner
            if owner is None:
                self._event("feedback_ignored", "stale", {"reason": "no_active_owner", "feedback": self._feedback_identity(feedback)})
                return self._result(False, "ignored", "no_active_owner")
            stale_reason = self._feedback_stale_reason(owner, feedback)
            if stale_reason is not None:
                self._event("feedback_ignored", "stale", {"reason": stale_reason, "feedback": self._feedback_identity(feedback)})
                return self._result(False, "ignored", stale_reason)
            seq_error = self._validate_feedback_sequence(owner, feedback)
            if seq_error is not None:
                self._event("feedback_ignored", "rejected", {"reason": seq_error, "feedback": self._feedback_identity(feedback)})
                return self._result(False, "rejected", seq_error)
            if feedback.status not in TERMINAL_FEEDBACK and feedback.status != "progress":
                self._event("feedback_ignored", "rejected", {"reason": "unknown_feedback_status", "status": feedback.status})
                return self._result(False, "rejected", "unknown_feedback_status")
            owner.last_feedback_seq = feedback.feedback_seq
            if feedback.status == "progress":
                if self._requires_quiescence(owner):
                    self._event("feedback_ignored", "stopping", {"reason": "stop_pending", "status": feedback.status})
                    return self._result(False, "ignored", "stop_pending")
                owner.status = "executing"
                self._event("feedback_progress", "ok", {"goal_id": owner.goal_id, "route_id": owner.route_id, "message": feedback.message})
                return self._result(True, "ok", data={"owner_status": owner.status})
            if feedback.status == "arrived":
                if self._requires_quiescence(owner):
                    self._event("feedback_ignored", "stopping", {"reason": "stop_pending", "status": feedback.status})
                    return self._result(False, "ignored", "stop_pending")
                owner.status = "succeeded"
                owner.terminal_cause = "arrived"
                self._event("goal_result", "ok", {"goal_id": owner.goal_id, "route_id": owner.route_id, "terminal_cause": "arrived"})
                self.active_owner = None
                return self._result(True, "ok", data={"terminal_cause": "arrived"})
            if feedback.status in {"stopped", "cancelled"}:
                owner.status = feedback.status
                owner.terminal_cause = feedback.status
                self._event("goal_stopped", "ok", {"goal_id": owner.goal_id, "route_id": owner.route_id, "terminal_cause": feedback.status})
                self.active_owner = None
                return self._result(True, "ok", data={"terminal_cause": feedback.status})
            owner.status = "%s_unresolved" % feedback.status
            owner.terminal_cause = feedback.status
            owner.unresolved_reason = feedback.status
            self._event("goal_result_unresolved", "unresolved", {"goal_id": owner.goal_id, "route_id": owner.route_id, "terminal_cause": feedback.status})
            return self._result(False, "failed", "%s_unresolved" % feedback.status)

    def receive_submit_ack(self, feedback: Feedback) -> Dict[str, Any]:
        """Apply a delayed backend submit acknowledgement for the active command."""
        with self._lock:
            owner = self.active_owner
            if owner is None:
                self._event("submit_ack_ignored", "stale", {"reason": "no_active_owner", "feedback": self._feedback_identity(feedback)})
                return self._result(False, "ignored", "no_active_owner")
            stale_reason = self._feedback_stale_reason(owner, feedback)
            if stale_reason is not None:
                self._event("submit_ack_ignored", "stale", {"reason": stale_reason, "feedback": self._feedback_identity(feedback)})
                return self._result(False, "ignored", stale_reason)
            seq_error = self._validate_feedback_sequence(owner, feedback)
            if seq_error is not None:
                self._event("submit_ack_ignored", "rejected", {"reason": seq_error, "feedback": self._feedback_identity(feedback)})
                return self._result(False, "rejected", seq_error)
            if feedback.status == "accepted":
                if self._requires_quiescence(owner):
                    self._event("submit_ack_ignored", "stopping", {"reason": "stop_pending", "status": feedback.status})
                    return self._result(False, "ignored", "stop_pending")
                if owner.status == "executing":
                    self._event("submit_ack_ignored", "stale", {"reason": "already_executing", "status": feedback.status})
                    return self._result(True, "ok", data={"owner_status": owner.status})
                owner.last_feedback_seq = feedback.feedback_seq
                owner.status = "accepted"
                self._event("submit_ack_accepted", "ok", {"goal_id": owner.goal_id, "route_id": owner.route_id})
                return self._result(True, "ok", data={"owner_status": owner.status})
            if feedback.status == "rejected":
                if self._requires_quiescence(owner):
                    self._event("submit_ack_ignored", "stopping", {"reason": "stop_pending", "status": feedback.status})
                    return self._result(False, "ignored", "stop_pending")
                if owner.status not in {"submitting", "submit_pending"}:
                    self._event("submit_ack_ignored", "contradictory", {"reason": "already_admitted", "status": owner.status})
                    return self._result(False, "ignored", "already_admitted")
                owner.last_feedback_seq = feedback.feedback_seq
                owner.status = "rejected"
                owner.terminal_cause = "submit_rejected"
                self._event("submit_ack_rejected", "rejected", {"goal_id": owner.goal_id, "route_id": owner.route_id})
                self.active_owner = None
                return self._result(False, "rejected", "backend_rejected")
            self._event("submit_ack_ignored", "rejected", {"reason": "unknown_submit_ack_status", "status": feedback.status})
            return self._result(False, "rejected", "unknown_submit_ack_status")

    def check_timeout(self) -> Dict[str, Any]:
        with self._lock:
            owner = self.active_owner
            if owner is None:
                return self._result(True, "ok", data={"timeout": False})
            age = self.clock() - owner.started_monotonic_s
            if age <= self.command_timeout_s:
                return self._result(True, "ok", data={"timeout": False, "age_s": age})
            stop_result = self._request_stop("command_timeout")
            if stop_result["ok"]:
                return self._result(False, "failed", "command_timeout_stopped")
            if self.active_owner is not None:
                self.active_owner.status = "timeout_stop_unresolved"
                self.active_owner.unresolved_reason = "command_timeout"
            self._event("command_timeout", "unresolved", {"goal_id": owner.goal_id, "route_id": owner.route_id, "age_s": age})
            return self._result(False, "failed", "command_timeout_unresolved")

    def invalidate_map(self, map_epoch: str, map_revision: int, reason: str = "map_changed") -> Dict[str, Any]:
        with self._lock:
            self.map_epoch = map_epoch
            self.map_revision = map_revision
            self.epoch += 1
            if self.active_owner is not None:
                self.active_owner.status = "map_invalidated_unresolved"
                self.active_owner.unresolved_reason = reason
                self._event("map_invalidated", "unresolved", {"reason": reason, "active_goal": self.active_owner.goal_id})
                return self._result(False, "failed", "map_invalidated_active_command_unresolved")
            self._event("map_invalidated", "ok", {"reason": reason})
            return self._result(True, "ok", data={"map_epoch": map_epoch, "map_revision": map_revision})

    def _submit_validated(self, request: GoalRequest) -> Dict[str, Any]:
        try:
            route = self.backend.plan_route(self.run_id, self.epoch, request)
        except Exception as exc:
            self._event("plan_failed", "failed", {"request_id": request.request_id, "error": str(exc)})
            return self._result(False, "failed", str(exc))
        if not isinstance(route, Route):
            self._event("plan_failed", "failed", {"request_id": request.request_id, "error": "invalid_route"})
            return self._result(False, "failed", "invalid_route")
        self._validate_request(request)
        self._validate_route(route, request)
        command_id = self._command_id(request, route)
        command = BackendCommand(self.run_id, self.epoch, request.request_id, request.goal_id, route.route_id, command_id)
        owner = CommandOwner(
            command=command,
            request_id=request.request_id,
            goal_id=request.goal_id,
            route_id=route.route_id,
            command_id=command_id,
            status="submitting",
            started_monotonic_s=self.clock(),
        )
        self.active_owner = owner
        self._event("route_planned", "ok", {"goal_id": request.goal_id, "route_id": route.route_id, "command_id": command_id})
        try:
            outcome = self.backend.submit_route(command, route)
        except Exception as exc:
            if self.active_owner is owner:
                owner.status = "submit_unresolved"
                owner.unresolved_reason = str(exc)
            self._event("submit_failed_after_command", "unresolved", {"goal_id": request.goal_id, "route_id": route.route_id, "error": str(exc)})
            return self._result(False, "failed", "submit_outcome_uncertain")
        if self.active_owner is not owner:
            outcome_status = outcome.status if isinstance(outcome, BackendOutcome) else type(outcome).__name__
            self._event("submit_outcome_after_owner_released", "stale", {"goal_id": request.goal_id, "route_id": route.route_id, "outcome": outcome_status})
            if owner.terminal_cause == "arrived":
                return self._result(True, "completed", data={"terminal_cause": "arrived"})
            return self._result(False, "failed", owner.terminal_cause or "completed_during_submit")
        if owner.status not in {"submitting"}:
            return self._merge_submit_return_after_callback(owner, outcome, route, request, command_id)
        malformed = self._submit_outcome_error(outcome, route)
        if malformed is not None:
            owner.status = "submit_unresolved"
            owner.unresolved_reason = malformed
            self._event("submit_malformed", "unresolved", {"goal_id": request.goal_id, "route_id": route.route_id, "error": malformed})
            return self._result(False, "failed", malformed)
        if outcome.status == "accepted":
            if self.active_owner is owner:
                owner.status = "accepted"
            self._event("submit_accepted", "ok", {"goal_id": request.goal_id, "route_id": route.route_id, "command_id": command_id})
            return self._result(True, "accepted", data={"goal_id": request.goal_id, "route_id": route.route_id, "command_id": command_id})
        if outcome.status == "rejected":
            if self.active_owner is owner:
                self.active_owner = None
            self._event("submit_rejected", "rejected", {"goal_id": request.goal_id, "route_id": route.route_id, "message": outcome.message})
            return self._result(False, "rejected", "backend_rejected")
        if outcome.status == "pending":
            if self.active_owner is owner:
                owner.status = "submit_pending"
                owner.unresolved_reason = "submit_ack_pending"
            self._event("submit_pending", "pending", {"goal_id": request.goal_id, "route_id": route.route_id, "message": outcome.message})
            return self._result(False, "pending", "submit_ack_pending")
        if outcome.status == "uncertain":
            if self.active_owner is owner:
                owner.status = "submit_unresolved"
                owner.unresolved_reason = "submit_uncertain"
            self._event("submit_uncertain", "unresolved", {"goal_id": request.goal_id, "route_id": route.route_id, "message": outcome.message})
            return self._result(False, "failed", "submit_outcome_uncertain")
        if self.active_owner is owner:
            owner.status = "submit_unresolved"
            owner.unresolved_reason = "unknown_backend_submit_status"
        self._event("submit_unknown", "unresolved", {"goal_id": request.goal_id, "route_id": route.route_id, "message": outcome.message, "status": outcome.status})
        return self._result(False, "failed", "unknown_backend_submit_status")

    def _validate_request(self, request: GoalRequest) -> None:
        if not isinstance(request.request_id, str) or not request.request_id:
            raise NavigationRejected("invalid_request_id")
        if not isinstance(request.goal_id, str) or not request.goal_id:
            raise NavigationRejected("invalid_goal_id")
        if request.target.units != "m" or request.evidence.units != "m":
            raise NavigationRejected("invalid_units")
        if request.target.frame_id != request.evidence.frame_id:
            raise NavigationRejected("frame_mismatch")
        for value in (request.target.x_m, request.target.y_m, request.target.z_m):
            if not math.isfinite(value):
                raise NavigationRejected("invalid_target_coordinates")
        if request.target.yaw_rad is not None and not math.isfinite(request.target.yaw_rad):
            raise NavigationRejected("invalid_target_coordinates")
        if not math.isfinite(request.evidence.captured_monotonic_s):
            raise NavigationRejected("invalid_evidence_timestamp")
        evidence_age = self.clock() - request.evidence.captured_monotonic_s
        if evidence_age < 0.0:
            raise NavigationRejected("future_evidence")
        if request.evidence.map_epoch != self.map_epoch or request.evidence.map_revision != self.map_revision:
            raise NavigationRejected("stale_or_changed_map_evidence")
        if not request.evidence.localization_valid:
            raise NavigationRejected("invalid_localization_evidence")
        if evidence_age > self.max_evidence_age_s:
            raise NavigationRejected("expired_evidence")

    def _validate_route(self, route: Route, request: GoalRequest) -> None:
        if route.goal_id != request.goal_id:
            raise NavigationRejected("route_goal_mismatch")
        if route.frame_id != request.target.frame_id:
            raise NavigationRejected("route_frame_mismatch")
        if route.map_epoch != self.map_epoch:
            raise NavigationRejected("route_map_epoch_mismatch")
        if not route.waypoints_m:
            raise NavigationRejected("empty_route")
        for point in route.waypoints_m:
            if len(point) != 3 or any(not math.isfinite(v) for v in point):
                raise NavigationRejected("invalid_route_waypoint")

    def _feedback_stale_reason(self, owner: CommandOwner, feedback: Feedback) -> Optional[str]:
        command = owner.identity()
        if feedback.run_id != command.run_id:
            return "wrong_run"
        if feedback.epoch != command.epoch:
            return "old_epoch"
        if feedback.goal_id != command.goal_id or feedback.route_id != command.route_id or feedback.command_id != command.command_id:
            return "identity_mismatch"
        if feedback.status in {"stopped", "cancelled"}:
            return None
        if feedback.map_epoch is not None and feedback.map_epoch != self.map_epoch:
            return "feedback_map_epoch_mismatch"
        if feedback.map_revision is not None and feedback.map_revision != self.map_revision:
            return "feedback_map_revision_mismatch"
        return None

    def _cached_or_conflict(self, request: GoalRequest) -> Optional[Dict[str, Any]]:
        fingerprint = self._fingerprint(request)
        saved = self._cache.get(request.request_id)
        if saved is None:
            return None
        saved_fingerprint, result = saved
        if saved_fingerprint != fingerprint:
            result = self._result(False, "rejected", "request_id_conflict")
            self._event("request_conflict", "rejected", {"request_id": request.request_id})
            return result
        self._event("request_duplicate", "ok", {"request_id": request.request_id})
        return copy.deepcopy(result)

    def _save_cache(self, request: GoalRequest, result: Dict[str, Any]) -> None:
        self._cache[request.request_id] = (self._fingerprint(request), copy.deepcopy(result))

    def _fingerprint(self, request: GoalRequest) -> str:
        payload = {
            "request_id": request.request_id,
            "goal_id": request.goal_id,
            "target": request.target.__dict__,
            "evidence": request.evidence.__dict__,
            "model_arguments": request.model_arguments,
        }
        return json.dumps(payload, sort_keys=True, allow_nan=True, separators=(",", ":"))

    def _cacheable_result(self, result: Dict[str, Any]) -> bool:
        if result.get("error") in {"command_owner_unresolved", "stop_not_confirmed"}:
            return False
        return result.get("status") != "ignored"

    def _request_stop(self, reason: str) -> Dict[str, Any]:
        owner = self.active_owner
        if owner is None:
            result = self._result(True, "ok", data={"terminal_cause": "no_active_command"})
            self._event("cancel_no_active", "ok", {"reason": reason})
            return result
        command = owner.identity()
        owner.status = "stopping"
        owner.unresolved_reason = reason
        self._event("stop_requested", "pending", {"goal_id": owner.goal_id, "route_id": owner.route_id, "reason": reason})
        try:
            outcome = self.backend.stop(command, reason)
        except Exception as exc:
            if self.active_owner is owner:
                owner.status = "stop_unresolved"
                owner.unresolved_reason = str(exc)
            self._event("stop_failed", "unresolved", {"error": str(exc), "goal_id": owner.goal_id})
            return self._result(False, "failed", str(exc))
        if self.active_owner is not owner:
            self._event("stop_outcome_after_owner_changed", "stale", {"goal_id": owner.goal_id, "route_id": owner.route_id})
            return self._result(True, "ok", data={"terminal_cause": "stop_callback_changed_owner"})
        malformed = self._stop_outcome_error(outcome, owner)
        if malformed is not None:
            owner.status = "stop_unresolved"
            owner.unresolved_reason = malformed
            self._event("stop_malformed", "unresolved", {"goal_id": owner.goal_id, "error": malformed})
            return self._result(False, "failed", malformed)
        if outcome.status == "stopped":
            owner.status = "cancelled"
            owner.terminal_cause = "cancelled"
            self._event("stop_confirmed", "ok", {"goal_id": owner.goal_id, "route_id": owner.route_id})
            self.active_owner = None
            return self._result(True, "ok", data={"terminal_cause": "cancelled"})
        owner.status = "stop_unresolved"
        owner.unresolved_reason = outcome.status
        self._event("stop_unresolved", outcome.status, {"goal_id": owner.goal_id, "message": outcome.message})
        return self._result(False, "failed", "stop_not_confirmed")

    def _requires_quiescence(self, owner: CommandOwner) -> bool:
        return owner.status in {
            "stopping",
            "stop_unresolved",
            "timeout_stop_unresolved",
            "map_invalidated_unresolved",
            "failed_unresolved",
            "rejected_unresolved",
            "submit_unresolved",
        }

    def _validate_feedback_sequence(self, owner: CommandOwner, feedback: Feedback) -> Optional[str]:
        if not isinstance(feedback.feedback_seq, int) or isinstance(feedback.feedback_seq, bool):
            return "invalid_feedback_seq"
        if feedback.feedback_seq <= owner.last_feedback_seq:
            return "stale_feedback_seq"
        return None

    def _submit_outcome_error(self, outcome: Any, route: Route) -> Optional[str]:
        if not isinstance(outcome, BackendOutcome):
            return "malformed_submit_outcome"
        if outcome.status not in {"accepted", "rejected", "pending", "uncertain"}:
            return "unknown_backend_submit_status"
        if outcome.route_id is not None and outcome.route_id != route.route_id:
            return "submit_route_id_mismatch"
        return None

    def _stop_outcome_error(self, outcome: Any, owner: CommandOwner) -> Optional[str]:
        if not isinstance(outcome, BackendOutcome):
            return "malformed_stop_outcome"
        if outcome.status not in {"stopped", "pending", "uncertain"}:
            return "unknown_backend_stop_status"
        if outcome.route_id is not None and outcome.route_id != owner.route_id:
            return "stop_route_id_mismatch"
        return None

    def _merge_submit_return_after_callback(
        self,
        owner: CommandOwner,
        outcome: Any,
        route: Route,
        request: GoalRequest,
        command_id: str,
    ) -> Dict[str, Any]:
        malformed = self._submit_outcome_error(outcome, route)
        if malformed is not None:
            owner.status = "submit_unresolved"
            owner.unresolved_reason = malformed
            self._event("submit_malformed_after_sync_feedback", "unresolved", {"goal_id": request.goal_id, "route_id": route.route_id, "error": malformed})
            return self._result(False, "failed", malformed)
        if outcome.status == "accepted" and owner.status in {"accepted", "executing"}:
            self._event("submit_accepted_after_sync_feedback", "ok", {"goal_id": request.goal_id, "route_id": route.route_id, "command_id": command_id, "owner_status": owner.status})
            return self._result(True, "accepted", data={"goal_id": request.goal_id, "route_id": route.route_id, "command_id": command_id, "owner_status": owner.status})
        if outcome.status == "pending" and owner.status in {"accepted", "executing"}:
            self._event("submit_pending_after_sync_feedback", "ok", {"goal_id": request.goal_id, "route_id": route.route_id, "owner_status": owner.status})
            return self._result(True, "accepted", data={"goal_id": request.goal_id, "route_id": route.route_id, "command_id": command_id, "owner_status": owner.status})
        self._event("submit_outcome_after_sync_feedback", "unresolved", {"goal_id": request.goal_id, "route_id": route.route_id, "owner_status": owner.status, "outcome": outcome.status})
        return self._result(False, "failed", owner.unresolved_reason or owner.status)

    def _command_id(self, request: GoalRequest, route: Route) -> str:
        raw = "%s:%s:%s:%s:%s" % (self.run_id, self.epoch, request.request_id, request.goal_id, route.route_id)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _event(self, kind: str, status: str, data: Dict[str, Any]) -> None:
        self.events.append(
            {
                "seq": len(self.events) + 1,
                "monotonic_s": self.clock(),
                "run_id": self.run_id,
                "epoch": self.epoch,
                "kind": kind,
                "status": status,
                "data": copy.deepcopy(data),
            }
        )

    def _result(
        self,
        ok: bool,
        status: str,
        error: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = {"ok": ok, "status": status, "state": self.state()}
        if error is not None:
            result["error"] = error
        if data is not None:
            result["data"] = copy.deepcopy(data)
        return result

    def _owner_projection(self) -> Optional[Dict[str, Any]]:
        owner = self.active_owner
        if owner is None:
            return None
        return {
            "request_id": owner.request_id,
            "command_run_id": owner.command.run_id,
            "command_epoch": owner.command.epoch,
            "goal_id": owner.goal_id,
            "route_id": owner.route_id,
            "command_id": owner.command_id,
            "status": owner.status,
            "last_feedback_seq": owner.last_feedback_seq,
            "terminal_cause": owner.terminal_cause,
            "unresolved_reason": owner.unresolved_reason,
        }

    def _feedback_identity(self, feedback: Feedback) -> Dict[str, Any]:
        return {
            "run_id": feedback.run_id,
            "epoch": feedback.epoch,
            "goal_id": feedback.goal_id,
            "route_id": feedback.route_id,
            "command_id": feedback.command_id,
            "feedback_seq": feedback.feedback_seq,
        }
