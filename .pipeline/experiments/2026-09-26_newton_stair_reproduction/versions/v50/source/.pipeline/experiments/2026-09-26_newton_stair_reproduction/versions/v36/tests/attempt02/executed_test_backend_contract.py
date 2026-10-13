"""Exercise the real version-owned HTTP/ROS helpers with controlled IPC races."""
from pathlib import Path
from types import SimpleNamespace as NS
import math
import os
import sys
import threading
import unittest

HERE = Path(__file__).resolve().parent
BASE = Path(os.environ["V36_EXPERIMENT_ROOT"]) if "V36_EXPERIMENT_ROOT" in os.environ else HERE.parents[1]
sys.path[:0] = [str(HERE / "backend_ros"), str(BASE / "runtime_sources/backend_adapter")]
from backend_adapter.contracts import CommandIdentity, NativeRoute, MeasuredState
from p2b_backend_ros.navigation_contract import PeriodicDeadline, final_path_yaw, normalize_yaw
from p2b_backend_ros.runtime import NavigationHttpRuntime, RequestedTarget, parse_goal_payload
from p2b_backend_ros.node import RosScanPort


class BackendContract(unittest.TestCase):
    def setUp(self):
        self.identity = CommandIdentity("run", 1, "request", "goal", "route", "command", 2, "map", 1)
        self.owner = NS(request_id="request", goal_id="goal", route_id="route", command_id="command", command=object())
        self.runtime = NavigationHttpRuntime.__new__(NavigationHttpRuntime)
        r = self.runtime
        r.service = NS(active_owner=self.owner)
        r.adapter = NS(gate=NS(owner=self.identity, cancel_pending=False, closed_reason="open"),
            frame_id="world", optimize=True, _identity_from_p2a_command=lambda _: self.identity)
        self.calls = []
        self.faults = []
        r.scan_port = NS(pct_start_provider=lambda: MeasuredState(3, 0.0, (1., 2., .3), (0., 0., 0.), "map", 1),
            refresh_route=lambda identity, route: self.calls.append((identity, route)) or True)
        r.clock = lambda: 10.0
        r._stop = False
        r._stop_flow = None
        r._stop_flow_lock = threading.Lock()
        r._lock = threading.Lock()
        r.requested_targets = {"route": RequestedTarget("request", "goal", "route", "command", (5., 6., 1.), (5., 6., 1.35))}
        r._global_frequency = 1.0
        r._global_history = []
        r._request_stop_flow = lambda owner, intent, reason: self.faults.append((owner, intent, reason))
        self.route = NativeRoute("new-computed-route", "goal", "world", "map", 1,
            ((1., 2., .65), (5., 6., 1.35)), "native_pct", "lite3_body_reference_no_display_offset")
        r.adapter.pct_client = NS(plan=lambda _: self.route)

    def test_global_refresh_uses_latest_measured_ground_start_and_same_identity(self):
        requests = []
        self.runtime.adapter.pct_client.plan = lambda request: requests.append(request) or self.route
        self.runtime._refresh_global_once(self.owner)
        self.assertEqual(requests[0].start_xyz_m, (1., 2., .3))
        self.assertEqual(requests[0].target_xyz_m, (5., 6., 1.))
        self.assertEqual(self.calls[0][0], self.identity)
        self.assertEqual(self.runtime._global_history[-1]["status"], "published")

    def test_cancel_while_pct_computes_discards_result(self):
        def plan(_):
            self.runtime.adapter.gate.cancel_pending = True
            return self.route
        self.runtime.adapter.pct_client.plan = plan
        self.runtime._refresh_global_once(self.owner)
        self.assertFalse(self.calls)
        self.assertEqual(self.runtime._global_history[-1]["status"], "discarded_owner_changed_or_stopping")

    def test_preemption_while_pct_computes_discards_result(self):
        def plan(_):
            self.runtime.service.active_owner = NS(command_id="next-command")
            return self.route
        self.runtime.adapter.pct_client.plan = plan
        self.runtime._refresh_global_once(self.owner)
        self.assertFalse(self.calls)

    def test_global_failure_requests_causal_fault_stop(self):
        def plan(_):
            raise TimeoutError("pct deadline")
        self.runtime.adapter.pct_client.plan = plan
        self.runtime._refresh_global_once(self.owner)
        self.assertFalse(self.calls)
        self.assertEqual(self.faults[0][1], "fault")
        self.assertIn("global_refresh_failed", self.faults[0][2])

    def test_failed_result_after_cancel_cannot_fault_new_goal(self):
        def plan(_):
            self.runtime.service.active_owner = None
            raise TimeoutError("old result")
        self.runtime.adapter.pct_client.plan = plan
        self.runtime._refresh_global_once(self.owner)
        self.assertFalse(self.faults)

    def test_yaw_completion_wraparound_and_boundary(self):
        r = self.runtime
        r._arrival_tolerance_yaw = .25
        r.scan_port.goal_pose = lambda _: ((5., 6., 1.35), -math.pi + .01)
        r.scan_port.measured_yaw = lambda: math.pi - .01
        self.assertTrue(r._within_goal_yaw(self.owner))
        r.scan_port.measured_yaw = lambda: 0.
        self.assertFalse(r._within_goal_yaw(self.owner))

    def test_yaw_unavailable_is_not_completion(self):
        r = self.runtime
        r._arrival_tolerance_yaw = .25
        def missing(_):
            raise KeyError("goal")
        r.scan_port.goal_pose = missing
        self.assertFalse(r._within_goal_yaw(self.owner))

    def test_default_yaw_skips_duplicate_terminal_points(self):
        self.assertAlmostEqual(final_path_yaw(((0,0,0), (0,2,0), (0,2,1))), math.pi/2)
        with self.assertRaises(ValueError):
            final_path_yaw(((0,0,0), (0,0,1)))

    def test_explicit_goal_yaw_and_invalid_numbers(self):
        payload = {"request_id":"r", "goal_id":"g", "target_ground_xyz":[1,2,3], "map_epoch":"m", "map_revision":1,
                   "target_yaw_rad": 3*math.pi}
        self.assertAlmostEqual(abs(parse_goal_payload(payload, {}).target_yaw_rad), math.pi)
        for invalid in (math.nan, math.inf):
            payload["target_yaw_rad"] = invalid
            with self.assertRaises(ValueError):
                parse_goal_payload(payload, {})

    def test_periodic_global_phase_pause_skip_and_rollback(self):
        clock = PeriodicDeadline(1)
        self.assertFalse(clock.due(10))
        self.assertFalse(clock.due(10.99))
        self.assertTrue(clock.due(11))
        self.assertFalse(clock.due(11))
        self.assertTrue(clock.due(15.3))
        self.assertEqual(clock.skipped_slots, 3)
        self.assertFalse(clock.due(15.3))
        self.assertFalse(clock.due(15.2))
        self.assertFalse(clock.due(16.19))
        self.assertTrue(clock.due(16.2))

    def test_goal_pose_is_requested_body_pose_and_fixed_across_refresh(self):
        port = RosScanPort.__new__(RosScanPort)
        port._condition = threading.Condition()
        port._goal_inputs = {("request", "goal"): ((5., 6., 1.), None)}
        port._goal_poses = {}
        port.nominal_body_height_m = .35
        def message():
            return NS(goal_pose=NS(position=NS(), orientation=NS()))
        a = message()
        port._fill_goal_pose(a, self.identity, self.route)
        xyz, yaw = port.goal_pose(self.owner)
        self.assertEqual(xyz, (5., 6., 1.35))
        changed = NS(waypoints_m=((0., 1., 0.), (0., 0., 0.)))
        b = message()
        port._fill_goal_pose(b, self.identity, changed)
        self.assertEqual(port.goal_pose(self.owner)[1], yaw)
        self.assertEqual(a.goal_pose.orientation.z, b.goal_pose.orientation.z)


if __name__ == "__main__":
    unittest.main()
