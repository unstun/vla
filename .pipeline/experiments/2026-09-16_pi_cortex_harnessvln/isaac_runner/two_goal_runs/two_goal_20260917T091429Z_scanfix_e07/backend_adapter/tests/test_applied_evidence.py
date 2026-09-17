import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend_adapter.applied_evidence import AppliedEvidenceReader, ContractError, StopEvidenceWindow, finish_request_payload, stop_evidence_confirmed


def snapshot(now_ns=10_000_000_000, **overrides):
    data = {
        "schema_version": 1,
        "run_id": "run1",
        "run_epoch_ns": 123,
        "source": "run_pct_scan_building.py external-goal status snapshot",
        "output_dir": "/run/out",
        "sim_step": 42,
        "sim_time_s": 2.1,
        "wall_monotonic_s": now_ns / 1.0e9,
        "wall_monotonic_ns": now_ns,
        "sim_time_timestamp_ns": 2100000000,
        "applied_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0},
        "admitted_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0},
        "raw_command": {"vx": 0.0, "vy": 0.0, "wz": 0.0},
        "command_sequence": 17,
        "command_stale": False,
        "command_reason": "active",
        "command_source_timestamp_ns": now_ns,
        "command_watchdog_events": 0,
        "command_sequence_gaps": 0,
        "measured": {"horizontal_speed_mps": 0.01, "yaw_rate_radps": 0.01, "base_xyz": [0.0, 0.0, 0.35], "base_quat_wxyz": [1.0, 0.0, 0.0, 0.0], "command_obs_error": 0.0},
        "state_epoch": {"state_sequence": 42, "telemetry_sequence": 100},
        "freshness": {"writer_monotonic_ns": now_ns, "max_reader_age_s": 2.0, "atomic_replace": True},
        "clock_domains": {},
    }
    for key, value in overrides.items():
        data[key] = value
    return data


class AppliedEvidenceTests(unittest.TestCase):
    def test_fresh_applied_zero_and_stillness_confirms_stop(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "current_command.json"
            path.write_text(json.dumps(snapshot()), encoding="utf-8")
            snap = AppliedEvidenceReader(path, monotonic_ns=lambda: 10_500_000_000).read()
            self.assertTrue(stop_evidence_confirmed(snap, "run1", 123))

    def test_stale_or_wrong_epoch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "current_command.json"
            path.write_text(json.dumps(snapshot()), encoding="utf-8")
            with self.assertRaises(ContractError):
                AppliedEvidenceReader(path, monotonic_ns=lambda: 13_000_000_001).read()
            snap = AppliedEvidenceReader(path, monotonic_ns=lambda: 10_500_000_000).read()
            with self.assertRaises(ContractError):
                stop_evidence_confirmed(snap, "run1", 999)

    def test_nonzero_applied_or_stale_command_does_not_confirm(self):
        data = snapshot(applied_command={"vx": 0.1, "vy": 0.0, "wz": 0.0})
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "current_command.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            snap = AppliedEvidenceReader(path, monotonic_ns=lambda: 10_500_000_000).read()
            self.assertFalse(stop_evidence_confirmed(snap, "run1", 123))
        data = snapshot(command_stale=True)
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "current_command.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            snap = AppliedEvidenceReader(path, monotonic_ns=lambda: 10_500_000_000).read()
            self.assertFalse(stop_evidence_confirmed(snap, "run1", 123))

    def test_stop_evidence_window_requires_post_cancel_dwell_and_advancing_state(self):
        window = StopEvidenceWindow()
        window.reset(10_000_000_000)
        data1 = snapshot(now_ns=10_100_000_000, command_source_timestamp_ns=10_100_000_000)
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "current_command.json"
            path.write_text(json.dumps(data1), encoding="utf-8")
            s1 = AppliedEvidenceReader(path, monotonic_ns=lambda: 10_200_000_000).read()
            self.assertFalse(window.observe(s1, "run1", 123))
            data2 = snapshot(now_ns=10_200_000_000, command_source_timestamp_ns=10_200_000_000, sim_time_s=3.15, sim_step=70, state_epoch={"state_sequence": 70, "telemetry_sequence": 101}, command_sequence=18)
            path.write_text(json.dumps(data2), encoding="utf-8")
            s2 = AppliedEvidenceReader(path, monotonic_ns=lambda: 10_300_000_000).read()
            self.assertTrue(window.observe(s2, "run1", 123))

    def test_stop_evidence_window_rejects_pre_cancel_cached_sample(self):
        window = StopEvidenceWindow()
        window.reset(10_500_000_000)
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "current_command.json"
            path.write_text(json.dumps(snapshot(now_ns=10_100_000_000, command_source_timestamp_ns=10_100_000_000)), encoding="utf-8")
            snap = AppliedEvidenceReader(path, monotonic_ns=lambda: 10_200_000_000).read()
            self.assertFalse(window.observe(snap, "run1", 123))

    def test_finish_request_payload_matches_runner_schema(self):
        payload = finish_request_payload("run1", "req1", 123, "FINISHED", monotonic_ns=11)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["backend_terminal_status"], "FINISHED")
        with self.assertRaises(ContractError):
            finish_request_payload("run1", "req1", 123, "DONE")


if __name__ == "__main__":
    unittest.main()
