"""Actual threaded queue, native-clock catch-up and hard100ms regressions."""
from concurrent.futures import ThreadPoolExecutor
import sys
from pathlib import Path
import threading
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'v198'))
from realtime_pacer import NativeClockPacer
from scan_deadline import ScanDeadline, PERIOD_S, ERROR


class ScanDeadlineTest(unittest.TestCase):
    def test_native_catchup_does_not_shorten_original_wall_budget(self):
        scheduler = ScanDeadline()
        value = object()
        with ThreadPoolExecutor(max_workers=1) as pool:
            def scan(index):
                time.sleep(.025)
                return value
            pacer = NativeClockPacer(0.)
            pacer.wall_start_s -= .2
            future = scheduler.submit(pool, scan, 0)
            for i in range(1, 6):
                pacer.wait(.02*i)
            self.assertFalse(future.done())
            self.assertIs(scheduler.result(future), value)
        self.assertLess(scheduler.records[0]['total_s'], PERIOD_S)
        self.assertLess(scheduler.records[0]['wall_at_check_s'], PERIOD_S)

    def test_true_overrun_is_rejected_at_original_budget(self):
        scheduler = ScanDeadline()
        release = threading.Event()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = scheduler.submit(pool, lambda index: release.wait(1), 0)
            begin = time.monotonic()
            try:
                with self.assertRaisesRegex(RuntimeError, ERROR):
                    scheduler.result(future)
                self.assertGreaterEqual(time.monotonic()-begin, .08)
            finally:
                release.set()

    def test_late_completed_result_cannot_bypass_budget(self):
        scheduler = ScanDeadline()
        with ThreadPoolExecutor(max_workers=1) as pool:
            def scan(index):
                time.sleep(.12)
                return 'late'
            future = scheduler.submit(pool, scan, 0)
            future.result(timeout=1)
            with self.assertRaisesRegex(RuntimeError, ERROR):
                scheduler.result(future)

    def test_queue_wait_counts_toward_budget(self):
        scheduler = ScanDeadline()
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(time.sleep, .08)
            def scan(index):
                time.sleep(.04)
                return 'queued'
            future = scheduler.submit(pool, scan, 0)
            with self.assertRaisesRegex(RuntimeError, ERROR):
                scheduler.result(future)
        self.assertGreater(scheduler.records[0]['queue_s'], .05)

    def test_worker_exception_propagates(self):
        scheduler = ScanDeadline()
        with ThreadPoolExecutor(max_workers=1) as pool:
            def scan(index):
                raise ValueError('ray failure')
            future = scheduler.submit(pool, scan, 0)
            with self.assertRaisesRegex(ValueError, 'ray failure'):
                scheduler.result(future)

    def test_capture_arguments_and_payload_are_unchanged(self):
        scheduler = ScanDeadline()
        pose, captured, payload = {}, object(), object()
        calls = []
        def scan(index, stamp, *, override_pose, captured_state):
            calls.append((index, stamp, override_pose, captured_state))
            return payload
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = scheduler.submit(pool, scan, 7, 12.62147045135498,
                override_pose=pose, captured_state=captured)
            self.assertIs(scheduler.result(future), payload)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][:2], (7, 12.62147045135498))
        self.assertIs(calls[0][2], pose)
        self.assertIs(calls[0][3], captured)
        self.assertEqual(PERIOD_S, .1)

    def test_worker_timeout_is_not_misreported_as_scheduler_timeout(self):
        scheduler = ScanDeadline()
        with ThreadPoolExecutor(max_workers=1) as pool:
            def scan(index):
                raise TimeoutError('ray internal timeout')
            future = scheduler.submit(pool, scan, 0)
            with self.assertRaisesRegex(TimeoutError, 'ray internal timeout'):
                scheduler.result(future)


if __name__ == '__main__':
    unittest.main()
