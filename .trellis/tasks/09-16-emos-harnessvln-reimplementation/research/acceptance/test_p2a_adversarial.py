"""Lead-owned acceptance checks, independent of the executor's happy-path suite."""

from dataclasses import replace
from pathlib import Path
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / '.pipeline/experiments/2026-09-16_pi_cortex_harnessvln/navigation_service'))
from core import (BackendOutcome, BackendUnavailable, EvidenceSnapshot, Feedback, GoalRequest,
                  NavigationBackendPort, PersistentNavigationService, Route, SpatialTarget)


class Backend(NavigationBackendPort):
    def __init__(self):
        self.commands = []
        self.stops = []
        self.submit_status = 'accepted'
        self.stop_status = 'pending'
        self.on_plan = None
        self.on_submit = None

    def plan_route(self, run_id, epoch, request):
        if self.on_plan:
            self.on_plan(request)
        return Route('route-' + request.goal_id, request.goal_id, 'map',
                     request.evidence.map_epoch, ((0.0, 0.0, 0.0), (request.target.x_m, 0.0, 0.0)))

    def submit_route(self, command, route):
        self.commands.append(command)
        if self.on_submit:
            self.on_submit(command)
        return BackendOutcome(self.submit_status)

    def stop(self, command, reason):
        self.stops.append(command)
        return BackendOutcome(self.stop_status)


class Acceptance(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.backend = Backend()
        self.service = PersistentNavigationService('run', 'map-1', 1, self.backend,
                                                   clock=lambda: self.now,
                                                   max_evidence_age_s=2.0,
                                                   command_timeout_s=5.0)

    def request(self, suffix='1'):
        return GoalRequest('request-' + suffix, 'goal-' + suffix,
                           SpatialTarget(1.0, 0.0, 0.0, None, 'map', 'm'),
                           EvidenceSnapshot('obs-' + suffix, self.now, 'map', 'm', 'map-1', 1, 1, True, 'rgbd_lio'),
                           {'target_id': 'target-' + suffix})

    def feedback(self, status, seq=1):
        command = self.backend.commands[-1]
        return Feedback(command.run_id, command.epoch, command.goal_id,
                        command.route_id, command.command_id, seq, status)

    def test_late_accept_progress_arrival_cannot_override_pending_stop(self):
        self.service.submit_goal(self.request())
        self.service.cancel_active()
        self.service.receive_submit_ack(self.feedback('accepted', 1))
        self.service.receive_feedback(self.feedback('progress', 2))
        self.service.receive_feedback(self.feedback('arrived', 3))
        second = self.service.submit_goal(self.request('2'))
        self.assertFalse(second['ok'], 'A delayed old arrival released unresolved stop ownership')
        self.assertEqual(len(self.backend.commands), 1)

    def test_failure_without_stop_receipt_keeps_motion_owner(self):
        self.service.submit_goal(self.request())
        self.service.receive_feedback(self.feedback('failed'))
        self.assertIsNotNone(self.service.active_owner, 'Failure is not proof of stopped execution')
        self.service.submit_goal(self.request('2'))
        self.assertEqual(len(self.backend.commands), 1)

    def test_synchronous_failure_is_not_reported_as_success(self):
        self.backend.on_submit = lambda command: self.service.receive_feedback(self.feedback('failed'))
        result = self.service.submit_goal(self.request())
        self.assertFalse(result['ok'], result)

    def test_map_change_cancellation_uses_original_command_identity(self):
        self.service.submit_goal(self.request())
        original = self.backend.commands[0]
        self.service.invalidate_map('map-2', 2)
        self.service.cancel_active()
        self.assertTrue(self.backend.stops)
        self.assertTrue(all(stop == original for stop in self.backend.stops), 'Epoch changed before old command could be stopped')
        result = self.service.receive_feedback(self.feedback('stopped', 3))
        self.assertIsNone(self.service.active_owner, result)

    def test_evidence_is_rechecked_after_route_planning(self):
        self.backend.on_plan = lambda request: setattr(self, 'now', self.now + 3.0)
        result = self.service.submit_goal(self.request())
        self.assertFalse(result['ok'], result)
        self.assertEqual(len(self.backend.commands), 0, 'Expired evidence still reached the motion backend')

    def test_nonfinite_and_future_evidence_is_rejected(self):
        for timestamp in [float('nan'), float('inf'), 1000.0]:
            with self.subTest(timestamp=timestamp):
                self.setUp()
                request = self.request()
                request = replace(request, evidence=replace(request.evidence, captured_monotonic_s=timestamp))
                result = self.service.submit_goal(request)
                self.assertFalse(result['ok'], result)
                self.assertEqual(self.backend.commands, [])

    def test_unknown_submit_reply_does_not_release_uncertain_motion(self):
        self.backend.submit_status = 'corrupt_reply'
        self.service.submit_goal(self.request())
        self.assertIsNotNone(self.service.active_owner)
        self.service.submit_goal(self.request('2'))
        self.assertEqual(len(self.backend.commands), 1)

    def test_timeout_requests_stop_not_only_a_status_change(self):
        self.service.submit_goal(self.request())
        self.now += 6.0
        self.service.check_timeout()
        self.assertTrue(self.backend.stops, 'Timeout did not request any hold/stop from the backend')
        self.assertIsNotNone(self.service.active_owner)

    def test_concurrent_submits_cannot_create_two_command_owners(self):
        entered, release = threading.Event(), threading.Event()
        lock = threading.Lock()
        first = [True]
        def slow_plan(request):
            with lock:
                is_first, first[0] = first[0], False
            if is_first:
                entered.set()
                release.wait(2.0)
        self.backend.on_plan = slow_plan
        results = []
        def submit(request):
            try:
                results.append(self.service.submit_goal(request))
            except Exception as error:
                results.append({'rejected_exception': type(error).__name__})
        a = threading.Thread(target=submit, args=(self.request('1'),))
        b = threading.Thread(target=submit, args=(self.request('2'),))
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
        self.assertLessEqual(len(self.backend.commands), 1, results)

    def test_late_rejection_ack_cannot_clear_pending_stop(self):
        self.service.submit_goal(self.request())
        self.service.cancel_active()
        self.service.receive_submit_ack(self.feedback('rejected', 1))
        self.service.submit_goal(self.request('2'))
        self.assertEqual(len(self.backend.commands), 1, 'Late contradictory rejection released a possibly moving command')

    def test_stop_receipt_with_original_map_is_valid_after_map_change(self):
        self.service.submit_goal(self.request())
        self.service.invalidate_map('map-2', 2)
        self.service.cancel_active()
        receipt = replace(self.feedback('stopped', 1), map_epoch='map-1', map_revision=1)
        self.service.receive_feedback(receipt)
        self.assertIsNone(self.service.active_owner, 'Original command stop receipt rejected just because map changed')

    def test_reentrant_admission_during_planning_cannot_dispatch_twice(self):
        nested = []
        def during_plan(request):
            self.backend.on_plan = None
            nested.append(self.service.submit_goal(self.request('2')))
        self.backend.on_plan = during_plan
        self.service.submit_goal(self.request())
        self.assertLessEqual(len(self.backend.commands), 1, nested)

    def test_stop_callback_cannot_erase_a_new_command_owner(self):
        self.service.submit_goal(self.request())
        nested = []
        def stop(command, reason):
            self.backend.stops.append(command)
            self.service.receive_feedback(self.feedback('stopped', 1))
            nested.append(self.service.submit_goal(self.request('2')))
            return BackendOutcome('stopped')
        self.backend.stop = stop
        self.service.cancel_active()
        if nested[0]['ok']:
            self.assertIsNotNone(self.service.active_owner, 'Stop return erased the callback-admitted owner')
            self.assertEqual(self.service.active_owner.goal_id, 'goal-2')
        else:
            self.assertEqual(len(self.backend.commands), 1)

    def test_invalid_feedback_does_not_poison_sequence_state(self):
        self.service.submit_goal(self.request())
        invalid = self.service.receive_feedback(self.feedback('progress', float('nan')))
        self.assertFalse(invalid['ok'], invalid)
        self.assertEqual(self.service.active_owner.last_feedback_seq, 0)
        unknown = self.service.receive_feedback(self.feedback('nonsense', 1000))
        self.assertFalse(unknown['ok'], unknown)
        valid = self.service.receive_feedback(self.feedback('progress', 1))
        self.assertTrue(valid['ok'], valid)

    def test_malformed_submit_reply_is_structured_and_retains_owner(self):
        def submit(command, route):
            self.backend.commands.append(command)
            return None
        self.backend.submit_route = submit
        result = self.service.submit_goal(self.request())
        self.assertFalse(result['ok'], result)
        self.assertIsNotNone(self.service.active_owner)

    def test_reply_for_different_route_is_not_acceptance(self):
        def submit(command, route):
            self.backend.commands.append(command)
            return BackendOutcome('accepted', route_id='another-route')
        self.backend.submit_route = submit
        result = self.service.submit_goal(self.request())
        self.assertFalse(result['ok'], result)
        self.assertIsNotNone(self.service.active_owner)

    def test_configuration_cannot_disable_freshness_with_nan(self):
        with self.assertRaises((ValueError, TypeError)):
            PersistentNavigationService('run', 'map-1', 1, self.backend,
                                        clock=lambda: self.now, max_evidence_age_s=float('nan'))

    def test_rejection_after_acceptance_or_motion_cannot_release_owner(self):
        for progress in [False, True]:
            with self.subTest(progress=progress):
                self.setUp()
                self.service.submit_goal(self.request())
                if progress:
                    self.service.receive_feedback(self.feedback('progress', 1))
                self.service.receive_submit_ack(self.feedback('rejected', 2))
                self.service.submit_goal(self.request('2'))
                self.assertEqual(len(self.backend.commands), 1,
                                 'Contradictory rejection released an acknowledged command without stop proof')

    def test_stop_reply_for_other_route_cannot_release_owner(self):
        self.service.submit_goal(self.request())
        self.backend.stop = lambda command, reason: BackendOutcome('stopped', route_id='other-route')
        result = self.service.cancel_active()
        self.assertFalse(result['ok'], result)
        self.service.submit_goal(self.request('2'))
        self.assertEqual(len(self.backend.commands), 1)

    def test_backend_unavailable_exception_after_dispatch_does_not_release_owner(self):
        def submit(command, route):
            self.backend.commands.append(command)
            raise BackendUnavailable('backend_disconnected_after_write')
        self.backend.submit_route = submit
        self.service.submit_goal(self.request())
        self.service.submit_goal(self.request('2'))
        self.assertEqual(len(self.backend.commands), 1,
                         'An exception type alone cannot prove that dispatch had no side effect')

    def test_successful_synchronous_callback_is_not_reported_as_failure(self):
        for status in ['accepted', 'progress']:
            with self.subTest(status=status):
                self.setUp()
                if status == 'accepted':
                    self.backend.on_submit = lambda command: self.service.receive_submit_ack(self.feedback('accepted'))
                else:
                    self.backend.on_submit = lambda command: self.service.receive_feedback(self.feedback('progress'))
                result = self.service.submit_goal(self.request())
                self.assertTrue(result['ok'], result)
                self.assertIsNotNone(self.service.active_owner)
                expected = 'accepted' if status == 'accepted' else 'executing'
                self.assertEqual(self.service.active_owner.status, expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
