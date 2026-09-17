import threading
import unittest
from dataclasses import replace

from core import (
    BackendUnavailable,
    BackendOutcome,
    EvidenceSnapshot,
    Feedback,
    GoalRequest,
    NavigationBackendPort,
    PersistentNavigationService,
    Route,
    SpatialTarget,
)


class ManualClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TraceBackend(NavigationBackendPort):
    def __init__(self):
        self.trace = []
        self.submit_status = "accepted"
        self.stop_status = "stopped"
        self.raise_on_submit = None
        self.raise_on_stop = None
        self.plan_status = "ok"
        self.plan_callback = None
        self.submit_callback = None
        self.stop_callback = None
        self._route_counter = 0

    def plan_route(self, run_id, epoch, request):
        self.trace.append(("plan", request.goal_id, request.request_id))
        if self.plan_callback is not None:
            self.plan_callback(request)
        if self.plan_status == "raise":
            raise RuntimeError("planner_down")
        self._route_counter += 1
        return Route(
            route_id="route-%d" % self._route_counter,
            goal_id=request.goal_id,
            frame_id=request.target.frame_id,
            map_epoch=request.evidence.map_epoch,
            waypoints_m=((0.0, 0.0, 0.0), (request.target.x_m, request.target.y_m, request.target.z_m)),
        )

    def submit_route(self, command, route):
        self.trace.append(("submit", command.goal_id, command.route_id, command.command_id))
        if self.submit_callback is not None:
            self.submit_callback(command, route)
        if self.raise_on_submit is not None:
            raise self.raise_on_submit
        return BackendOutcome(self.submit_status)

    def stop(self, command, reason):
        self.trace.append(("stop", command.goal_id, command.route_id, reason))
        if self.stop_callback is not None:
            self.stop_callback(command, reason)
        if self.raise_on_stop is not None:
            raise self.raise_on_stop
        return BackendOutcome(self.stop_status)


class NavigationServiceTests(unittest.TestCase):
    def setUp(self):
        self.clock = ManualClock()
        self.backend = TraceBackend()
        self.service = PersistentNavigationService(
            run_id="run-a",
            map_epoch="map-a",
            map_revision=7,
            backend=self.backend,
            clock=self.clock,
            max_evidence_age_s=5.0,
            command_timeout_s=10.0,
        )

    def evidence(self, observation_id="obs-1", map_epoch="map-a", map_revision=7, localization_valid=True):
        return EvidenceSnapshot(
            observation_id=observation_id,
            captured_monotonic_s=self.clock(),
            frame_id="map",
            units="m",
            map_epoch=map_epoch,
            map_revision=map_revision,
            localization_revision=3,
            localization_valid=localization_valid,
            source="rgbd_lio",
        )

    def request(self, request_id="req-1", goal_id="goal-1", x=1.0, evidence=None):
        return GoalRequest(
            request_id=request_id,
            goal_id=goal_id,
            target=SpatialTarget(x_m=x, y_m=0.0, z_m=0.0, yaw_rad=None, frame_id="map", units="m"),
            evidence=evidence or self.evidence(),
            model_arguments={"label": goal_id, "raw_text": "test target"},
        )

    def accepted_owner(self):
        result = self.service.submit_goal(self.request())
        self.assertTrue(result["ok"], result)
        owner = self.service.active_owner
        self.assertIsNotNone(owner)
        return owner

    def feedback(self, owner, seq=1, status="arrived", epoch=None, goal_id=None, route_id=None):
        return Feedback(
            run_id="run-a",
            epoch=self.service.epoch if epoch is None else epoch,
            goal_id=owner.goal_id if goal_id is None else goal_id,
            route_id=owner.route_id if route_id is None else route_id,
            command_id=owner.command_id,
            feedback_seq=seq,
            status=status,
            map_epoch=self.service.map_epoch,
            map_revision=self.service.map_revision,
        )

    def feedback_for_command(self, command, seq=1, status="arrived"):
        return Feedback(
            run_id=command.run_id,
            epoch=command.epoch,
            goal_id=command.goal_id,
            route_id=command.route_id,
            command_id=command.command_id,
            feedback_seq=seq,
            status=status,
            map_epoch=self.service.map_epoch,
            map_revision=self.service.map_revision,
        )

    def test_default_backend_refuses_execution(self):
        service = PersistentNavigationService("run-a", "map-a", 7, clock=self.clock)
        result = service.submit_goal(self.request())
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "navigation_backend_unavailable")
        self.assertIsNone(service.active_owner)

    def test_two_goals_sequence_requires_terminal_feedback_between_submits(self):
        owner = self.accepted_owner()
        blocked = self.service.submit_goal(self.request("req-2", "goal-2", x=2.0))
        self.assertEqual(blocked["error"], "command_owner_unresolved")
        arrived = self.service.receive_feedback(self.feedback(owner, seq=1, status="arrived"))
        self.assertTrue(arrived["ok"])
        second = self.service.submit_goal(self.request("req-2", "goal-2", x=2.0))
        self.assertTrue(second["ok"], second)
        self.assertEqual([item[0] for item in self.backend.trace], ["plan", "submit", "plan", "submit"])

    def test_duplicate_request_is_idempotent_and_conflicting_payload_is_rejected(self):
        request = self.request()
        first = self.service.submit_goal(request)
        again = self.service.submit_goal(request)
        self.assertEqual(first, again)
        conflict = self.request(request_id="req-1", goal_id="goal-1", x=9.0)
        result = self.service.submit_goal(conflict)
        self.assertEqual(result["error"], "request_id_conflict")
        self.assertEqual([item[0] for item in self.backend.trace], ["plan", "submit"])

    def test_replacement_orders_stop_before_second_submit(self):
        self.accepted_owner()
        result = self.service.replace_goal(self.request("req-2", "goal-2", x=2.0))
        self.assertTrue(result["ok"], result)
        self.assertEqual([item[0] for item in self.backend.trace], ["plan", "submit", "stop", "plan", "submit"])
        self.assertEqual(self.service.active_owner.goal_id, "goal-2")

    def test_replacement_blocks_when_stop_ack_missing(self):
        self.backend.stop_status = "uncertain"
        self.accepted_owner()
        result = self.service.replace_goal(self.request("req-2", "goal-2", x=2.0))
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "stop_not_confirmed")
        self.assertEqual([item[0] for item in self.backend.trace], ["plan", "submit", "stop"])
        self.assertEqual(self.service.active_owner.goal_id, "goal-1")
        self.assertEqual(self.service.active_owner.status, "stop_unresolved")

    def test_late_old_feedback_cannot_resurrect_cancelled_goal(self):
        old_owner = self.accepted_owner()
        self.service.replace_goal(self.request("req-2", "goal-2", x=2.0))
        result = self.service.receive_feedback(self.feedback(old_owner, seq=1, status="arrived"))
        self.assertEqual(result["status"], "ignored")
        self.assertEqual(self.service.active_owner.goal_id, "goal-2")

    def test_old_epoch_feedback_is_ignored_after_map_change(self):
        owner = self.accepted_owner()
        self.service.invalidate_map("map-b", 8)
        result = self.service.receive_feedback(self.feedback(owner, seq=1, status="arrived", epoch=1))
        self.assertEqual(result["error"], "stop_pending")
        self.assertEqual(self.service.active_owner.status, "map_invalidated_unresolved")
        stopped = self.service.receive_feedback(self.feedback(owner, seq=2, status="stopped", epoch=1))
        self.assertTrue(stopped["ok"], stopped)
        self.assertIsNone(self.service.active_owner)

    def test_uncertain_submit_keeps_owner_and_blocks_replacement(self):
        self.backend.submit_status = "uncertain"
        result = self.service.submit_goal(self.request())
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "submit_outcome_uncertain")
        self.assertIsNotNone(self.service.active_owner)
        replacement = self.service.submit_goal(self.request("req-2", "goal-2", x=2.0))
        self.assertEqual(replacement["error"], "command_owner_unresolved")

    def test_pending_submit_requires_correlated_late_ack(self):
        self.backend.submit_status = "pending"
        result = self.service.submit_goal(self.request())
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "submit_ack_pending")
        owner = self.service.active_owner
        wrong = Feedback(
            run_id="run-a",
            epoch=self.service.epoch,
            goal_id=owner.goal_id,
            route_id="different-route",
            command_id=owner.command_id,
            feedback_seq=1,
            status="accepted",
            map_epoch=self.service.map_epoch,
            map_revision=self.service.map_revision,
        )
        self.assertEqual(self.service.receive_submit_ack(wrong)["error"], "identity_mismatch")
        accepted = self.service.receive_submit_ack(self.feedback(owner, seq=1, status="accepted"))
        self.assertTrue(accepted["ok"], accepted)
        self.assertEqual(self.service.active_owner.status, "accepted")

    def test_late_ack_after_cancel_cannot_resurrect_old_goal(self):
        self.backend.submit_status = "pending"
        pending = self.service.submit_goal(self.request())
        self.assertFalse(pending["ok"])
        old_owner = self.service.active_owner
        self.backend.submit_status = "accepted"
        replaced = self.service.replace_goal(self.request("req-2", "goal-2", x=2.0))
        self.assertTrue(replaced["ok"], replaced)
        late = self.service.receive_submit_ack(self.feedback(old_owner, seq=1, status="accepted"))
        self.assertEqual(late["error"], "identity_mismatch")
        self.assertEqual(self.service.active_owner.goal_id, "goal-2")

    def test_pending_stop_latches_until_explicit_stopped_receipt(self):
        self.backend.stop_status = "pending"
        owner = self.accepted_owner()
        cancel = self.service.cancel_active()
        self.assertFalse(cancel["ok"])
        self.assertEqual(self.service.receive_submit_ack(self.feedback(owner, seq=1, status="accepted"))["error"], "stop_pending")
        self.assertEqual(self.service.receive_feedback(self.feedback(owner, seq=2, status="progress"))["error"], "stop_pending")
        self.assertEqual(self.service.receive_feedback(self.feedback(owner, seq=3, status="arrived"))["error"], "stop_pending")
        second = self.service.submit_goal(self.request("req-2", "goal-2", x=2.0))
        self.assertEqual(second["error"], "command_owner_unresolved")
        stopped = self.service.receive_feedback(self.feedback(owner, seq=4, status="stopped"))
        self.assertTrue(stopped["ok"], stopped)
        second = self.service.submit_goal(self.request("req-2", "goal-2", x=2.0))
        self.assertTrue(second["ok"], second)

    def test_late_rejection_ack_during_pending_stop_does_not_clear_owner(self):
        self.backend.stop_status = "pending"
        owner = self.accepted_owner()
        self.service.cancel_active()
        rejected = self.service.receive_submit_ack(self.feedback(owner, seq=1, status="rejected"))
        self.assertEqual(rejected["error"], "stop_pending")
        second = self.service.submit_goal(self.request("req-2", "goal-2", x=2.0))
        self.assertEqual(second["error"], "command_owner_unresolved")

    def test_rejection_ack_after_acceptance_or_motion_does_not_clear_owner(self):
        owner = self.accepted_owner()
        rejected = self.service.receive_submit_ack(self.feedback(owner, seq=1, status="rejected"))
        self.assertEqual(rejected["error"], "already_admitted")
        self.assertIsNotNone(self.service.active_owner)
        progress = self.service.receive_feedback(self.feedback(owner, seq=2, status="progress"))
        self.assertTrue(progress["ok"], progress)
        rejected = self.service.receive_submit_ack(self.feedback(owner, seq=3, status="rejected"))
        self.assertEqual(rejected["error"], "already_admitted")
        second = self.service.submit_goal(self.request("req-2", "goal-2", x=2.0))
        self.assertEqual(second["error"], "command_owner_unresolved")

    def test_synchronous_feedback_during_submit_is_correlated_without_resurrection(self):
        def on_submit(command, route):
            result = self.service.receive_feedback(self.feedback_for_command(command, seq=1, status="arrived"))
            self.assertTrue(result["ok"], result)

        self.backend.submit_callback = on_submit
        result = self.service.submit_goal(self.request())
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "completed")
        self.assertIsNone(self.service.active_owner)
        self.assertIn("submit_outcome_after_owner_released", [event["kind"] for event in self.service.events])

    def test_synchronous_failed_feedback_during_submit_is_not_success(self):
        def on_submit(command, route):
            result = self.service.receive_feedback(self.feedback_for_command(command, seq=1, status="failed"))
            self.assertFalse(result["ok"], result)

        self.backend.submit_callback = on_submit
        result = self.service.submit_goal(self.request())
        self.assertFalse(result["ok"], result)
        self.assertIsNotNone(self.service.active_owner)
        self.assertEqual(self.service.active_owner.status, "failed_unresolved")

    def test_synchronous_successful_callback_merges_with_submit_return(self):
        def on_submit_ack(command, route):
            result = self.service.receive_submit_ack(self.feedback_for_command(command, seq=1, status="accepted"))
            self.assertTrue(result["ok"], result)

        self.backend.submit_callback = on_submit_ack
        result = self.service.submit_goal(self.request())
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.service.active_owner.status, "accepted")

        self.setUp()

        def on_submit_progress(command, route):
            result = self.service.receive_feedback(self.feedback_for_command(command, seq=1, status="progress"))
            self.assertTrue(result["ok"], result)

        self.backend.submit_callback = on_submit_progress
        result = self.service.submit_goal(self.request())
        self.assertTrue(result["ok"], result)
        self.assertEqual(self.service.active_owner.status, "executing")

    def test_transport_failure_after_submission_keeps_owner(self):
        self.backend.raise_on_submit = RuntimeError("socket_lost_after_write")
        result = self.service.submit_goal(self.request())
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "submit_outcome_uncertain")
        self.assertEqual(self.service.active_owner.status, "submit_unresolved")
        self.assertEqual(self.service.active_owner.unresolved_reason, "socket_lost_after_write")

    def test_oserror_after_submission_keeps_owner(self):
        self.backend.raise_on_submit = OSError("pipe_broken_after_write")
        result = self.service.submit_goal(self.request())
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "submit_outcome_uncertain")
        self.assertEqual(self.service.active_owner.status, "submit_unresolved")

    def test_backend_unavailable_after_submit_keeps_owner(self):
        def submit_raises(command, route):
            self.backend.trace.append(("submit", command.goal_id, command.route_id, command.command_id))
            raise BackendUnavailable("backend_disconnected_after_write")

        self.backend.submit_route = submit_raises
        result = self.service.submit_goal(self.request())
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["error"], "submit_outcome_uncertain")
        self.assertEqual(self.service.active_owner.status, "submit_unresolved")

    def test_stop_throw_after_possible_side_effect_keeps_owner(self):
        self.accepted_owner()
        self.backend.raise_on_stop = RuntimeError("stop_socket_lost_after_write")
        result = self.service.cancel_active()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "stop_socket_lost_after_write")
        self.assertEqual(self.service.active_owner.status, "stop_unresolved")

    def test_connection_error_after_stop_keeps_owner(self):
        self.accepted_owner()
        self.backend.raise_on_stop = ConnectionError("stop_connection_lost")
        result = self.service.cancel_active()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "stop_connection_lost")
        self.assertEqual(self.service.active_owner.status, "stop_unresolved")

    def test_stop_callback_new_owner_is_not_erased_by_outer_stop_return(self):
        self.accepted_owner()
        nested = []

        def on_stop(command, reason):
            self.service.receive_feedback(self.feedback_for_command(command, seq=1, status="stopped"))
            nested.append(self.service.submit_goal(self.request("req-2", "goal-2", x=2.0)))

        self.backend.stop_callback = on_stop
        result = self.service.cancel_active()
        self.assertTrue(result["ok"], result)
        if nested[0]["ok"]:
            self.assertEqual(self.service.active_owner.goal_id, "goal-2")
        else:
            self.assertEqual(nested[0]["error"], "command_owner_unresolved")

    def test_stop_reply_for_wrong_route_does_not_release_owner(self):
        self.accepted_owner()

        def stop_wrong_route(command, reason):
            self.backend.trace.append(("stop", command.goal_id, command.route_id, reason))
            return BackendOutcome("stopped", route_id="wrong-route")

        self.backend.stop = stop_wrong_route
        result = self.service.cancel_active()
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["error"], "stop_route_id_mismatch")
        self.assertIsNotNone(self.service.active_owner)

    def test_replacement_revalidates_freshness_after_stop_confirmation(self):
        self.accepted_owner()
        replacement = self.request("req-2", "goal-2", x=2.0)

        def on_stop(command, reason):
            self.clock.advance(6.0)

        self.backend.stop_callback = on_stop
        result = self.service.replace_goal(replacement)
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "expired_evidence")
        self.assertEqual([item[0] for item in self.backend.trace], ["plan", "submit", "stop"])

    def test_timeout_is_explicit_and_does_not_release_owner(self):
        self.backend.stop_status = "pending"
        owner = self.accepted_owner()
        self.clock.advance(11.0)
        result = self.service.check_timeout()
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "command_timeout_unresolved")
        self.assertIs(self.service.active_owner, owner)
        self.assertEqual(owner.status, "timeout_stop_unresolved")
        self.assertIn(("stop", "goal-1", "route-1", "command_timeout"), self.backend.trace)

    def test_backend_plan_failure_does_not_create_success_or_owner(self):
        self.backend.plan_status = "raise"
        result = self.service.submit_goal(self.request())
        self.assertFalse(result["ok"])
        self.assertEqual(result["error"], "planner_down")
        self.assertIsNone(self.service.active_owner)

    def test_evidence_rechecked_after_route_planning(self):
        self.backend.plan_callback = lambda request: self.clock.advance(6.0)
        result = self.service.submit_goal(self.request())
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["error"], "expired_evidence")
        self.assertEqual([item[0] for item in self.backend.trace], ["plan"])

    def test_reentrant_admission_during_planning_rejected(self):
        nested = []

        def during_plan(request):
            self.backend.plan_callback = None
            nested.append(self.service.submit_goal(self.request("req-2", "goal-2", x=2.0)))

        self.backend.plan_callback = during_plan
        first = self.service.submit_goal(self.request())
        self.assertTrue(first["ok"], first)
        self.assertEqual(nested[0]["error"], "command_owner_unresolved")
        self.assertEqual(len([item for item in self.backend.trace if item[0] == "submit"]), 1)

    def test_unknown_submit_reply_keeps_uncertain_owner(self):
        self.backend.submit_status = "corrupt_reply"
        result = self.service.submit_goal(self.request())
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["error"], "unknown_backend_submit_status")
        self.assertEqual(self.service.active_owner.status, "submit_unresolved")
        second = self.service.submit_goal(self.request("req-2", "goal-2", x=2.0))
        self.assertEqual(second["error"], "command_owner_unresolved")

    def test_malformed_submit_reply_and_route_mismatch_keep_owner(self):
        original_submit = self.backend.submit_route

        def submit_none(command, route):
            self.backend.trace.append(("submit", command.goal_id, command.route_id, command.command_id))
            return None

        self.backend.submit_route = submit_none
        result = self.service.submit_goal(self.request())
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["error"], "malformed_submit_outcome")
        self.assertIsNotNone(self.service.active_owner)

        self.setUp()

        def submit_wrong_route(command, route):
            self.backend.trace.append(("submit", command.goal_id, command.route_id, command.command_id))
            return BackendOutcome("accepted", route_id="wrong-route")

        self.backend.submit_route = submit_wrong_route
        result = self.service.submit_goal(self.request())
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["error"], "submit_route_id_mismatch")
        self.assertIsNotNone(self.service.active_owner)
        self.backend.submit_route = original_submit

    def test_stale_map_changed_and_invalid_payloads_are_rejected_before_backend(self):
        stale = self.request(evidence=self.evidence(map_revision=6))
        self.assertEqual(self.service.submit_goal(stale)["error"], "stale_or_changed_map_evidence")
        bad_loc = self.request("req-2", "goal-2", evidence=self.evidence(localization_valid=False))
        self.assertEqual(self.service.submit_goal(bad_loc)["error"], "invalid_localization_evidence")
        expired_evidence = self.evidence("obs-old")
        self.clock.advance(6.0)
        expired = self.request("req-3", "goal-3", evidence=expired_evidence)
        self.assertEqual(self.service.submit_goal(expired)["error"], "expired_evidence")
        bad_units = GoalRequest(
            request_id="req-4",
            goal_id="goal-4",
            target=SpatialTarget(x_m=1.0, y_m=0.0, z_m=0.0, yaw_rad=None, frame_id="map", units="cm"),
            evidence=self.evidence("obs-4"),
            model_arguments={},
        )
        self.assertEqual(self.service.submit_goal(bad_units)["error"], "invalid_units")
        self.assertEqual(self.backend.trace, [])

    def test_nonfinite_coordinates_rejected(self):
        bad = GoalRequest(
            request_id="req-bad",
            goal_id="goal-bad",
            target=SpatialTarget(x_m=float("nan"), y_m=0.0, z_m=0.0, yaw_rad=None, frame_id="map", units="m"),
            evidence=self.evidence("obs-bad"),
            model_arguments={},
        )
        self.assertEqual(self.service.submit_goal(bad)["error"], "invalid_target_coordinates")
        self.assertEqual(self.backend.trace, [])

    def test_nonfinite_and_future_evidence_timestamps_rejected(self):
        for index, (timestamp, expected) in enumerate([
            (float("nan"), "invalid_evidence_timestamp"),
            (float("inf"), "invalid_evidence_timestamp"),
            (self.clock() + 1.0, "future_evidence"),
        ]):
            with self.subTest(timestamp=timestamp):
                request = self.request(
                    request_id="req-ts-%d" % index,
                    goal_id="goal-ts-%d" % index,
                    evidence=replace(self.evidence("obs-ts-%d" % index), captured_monotonic_s=timestamp),
                )
                self.assertEqual(self.service.submit_goal(request)["error"], expected)
                self.assertEqual(self.backend.trace, [])

    def test_invalid_feedback_sequence_and_status_do_not_mutate_sequence(self):
        owner = self.accepted_owner()
        invalid = self.service.receive_feedback(self.feedback(owner, seq=float("nan"), status="progress"))
        self.assertFalse(invalid["ok"], invalid)
        self.assertEqual(self.service.active_owner.last_feedback_seq, 0)
        unknown = self.service.receive_feedback(self.feedback(owner, seq=1000, status="nonsense"))
        self.assertFalse(unknown["ok"], unknown)
        self.assertEqual(self.service.active_owner.last_feedback_seq, 0)
        valid = self.service.receive_feedback(self.feedback(owner, seq=1, status="progress"))
        self.assertTrue(valid["ok"], valid)

    def test_nan_config_rejected(self):
        with self.assertRaises(ValueError):
            PersistentNavigationService("run-a", "map-a", 7, backend=self.backend, clock=self.clock, max_evidence_age_s=float("nan"))
        with self.assertRaises(ValueError):
            PersistentNavigationService("run-a", "map-a", 7, backend=self.backend, clock=self.clock, command_timeout_s=float("nan"))

    def test_concurrent_submits_cannot_dispatch_two_commands(self):
        entered = threading.Event()
        release = threading.Event()
        first_lock = threading.Lock()
        first = [True]

        def slow_first_plan(request):
            with first_lock:
                is_first = first[0]
                first[0] = False
            if is_first:
                entered.set()
                release.wait(2.0)

        self.backend.plan_callback = slow_first_plan
        results = []

        def submit(request):
            results.append(self.service.submit_goal(request))

        a = threading.Thread(target=submit, args=(self.request("req-1", "goal-1"),))
        b = threading.Thread(target=submit, args=(self.request("req-2", "goal-2"),))
        try:
            a.start()
            entered.wait(0.2)
            b.start()
            b.join(0.1)
        finally:
            release.set()
            a.join(2.0)
            b.join(2.0)
        self.assertFalse(a.is_alive() or b.is_alive())
        self.assertLessEqual(len([item for item in self.backend.trace if item[0] == "submit"]), 1, results)

    def test_feedback_sequence_and_identity_checks(self):
        owner = self.accepted_owner()
        progress = self.service.receive_feedback(self.feedback(owner, seq=1, status="progress"))
        self.assertTrue(progress["ok"], progress)
        duplicate = self.service.receive_feedback(self.feedback(owner, seq=1, status="arrived"))
        self.assertEqual(duplicate["error"], "stale_feedback_seq")
        wrong_route = self.service.receive_feedback(self.feedback(owner, seq=2, status="arrived", route_id="old-route"))
        self.assertEqual(wrong_route["error"], "identity_mismatch")
        arrived = self.service.receive_feedback(self.feedback(owner, seq=2, status="arrived"))
        self.assertTrue(arrived["ok"], arrived)
        self.assertIsNone(self.service.active_owner)


if __name__ == "__main__":
    unittest.main()
