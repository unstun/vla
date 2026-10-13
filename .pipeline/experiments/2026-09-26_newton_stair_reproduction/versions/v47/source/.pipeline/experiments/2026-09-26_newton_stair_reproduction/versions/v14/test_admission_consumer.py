"""Replay real v13 replies through the actual ROS port wait helper."""
import dataclasses
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

BASE = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("notice_fixture", BASE / "versions/v11/test_failure_notice.py")
fixture_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture_module)
fixture, notice = fixture_module.fixture, fixture_module.notice


class ConsumerReplyTests(unittest.TestCase):
    def wait(self, port, owner, statuses, consumers):
        with port._condition:
            return port._wait_admission(owner, statuses, 0., consumers)

    def test_actual_recorded_failure_then_controller_hold(self):
        port, _ = fixture()
        records = []
        with (BASE / "runs/v13_building_route01/artifacts/reactive_observations.jsonl").open() as stream:
            for line in stream:
                row = json.loads(line)
                if row["event"] == "scan_admission":
                    records.append(row["data"])
        first = next(i for i, r in enumerate(records) if r["message"] == "native_replan_exhausted")
        owner = port._identity_from_msg(SimpleNamespace(**records[first]))
        port.gate.admit(owner)
        port.gate.request_cancel(owner, "native_replan_exhausted")
        for row in records[first:]:
            port._on_admission(SimpleNamespace(**row))
        result = self.wait(port, owner, {"stopped", "pending", "uncertain", "rejected"}, {"controller"})
        self.assertEqual(result.consumer, "controller")
        self.assertEqual(result.status, "stopped")
        self.assertTrue(result.hold_confirmed)
        self.assertFalse(result.measured_stillness_confirmed)

    def test_wrong_consumer_rejection_does_not_end_stop_wait(self):
        port, owner = fixture()
        port._on_admission(notice(owner))
        result = self.wait(port, owner, {"stopped", "rejected"}, {"controller"})
        self.assertEqual(result.status, "pending")
        self.assertEqual(len(port._admissions), 1)

    def test_route_wait_does_not_consume_controller_rejection(self):
        port, owner = fixture()
        port._on_admission(notice(owner, consumer="controller"))
        port._on_admission(notice(owner, status="accepted", message="route_accepted"))
        result = self.wait(port, owner, {"accepted", "rejected"}, {"fsm"})
        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.consumer, "fsm")

    def test_expected_consumer_rejection_and_identity_still_apply(self):
        port, owner = fixture()
        port._on_admission(notice(owner, run_id="other", consumer="controller", status="stopped", hold_confirmed=True))
        port._on_admission(notice(owner, consumer="controller", message="explicit_stop_rejection"))
        result = self.wait(port, owner, {"stopped", "rejected"}, {"controller"})
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.message, "explicit_stop_rejection")


if __name__ == "__main__":
    unittest.main()
