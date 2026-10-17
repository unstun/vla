"""Measured original100ms captured-scan deadline; never change capture data."""
from concurrent.futures import TimeoutError as FutureTimeout
import json
from pathlib import Path
import threading
import time

PERIOD_S = .1
ERROR = 'Captured scan did not finish before the next sensor period'


class ScanDeadline:
    def __init__(self):
        self.records = []

    def submit(self, executor, scan, *args, **kwargs):
        row = dict(index=args[0], submitted_wall_s=time.monotonic(), period_s=PERIOD_S)
        self.records.append(row)
        def work():
            row['started_wall_s'] = time.monotonic()
            row['thread_id'] = threading.get_native_id()
            cpu = time.thread_time()
            sched = Path(f"/proc/self/task/{row['thread_id']}/schedstat")
            before = list(map(int, sched.read_text().split())) if sched.exists() else None
            try:
                return scan(*args, **kwargs)
            except BaseException as exc:
                row['worker_exception'] = repr(exc)
                raise
            finally:
                row['finished_wall_s'] = time.monotonic()
                row['thread_cpu_s'] = time.thread_time() - cpu
                row['queue_s'] = row['started_wall_s'] - row['submitted_wall_s']
                row['worker_wall_s'] = row['finished_wall_s'] - row['started_wall_s']
                row['total_s'] = row['finished_wall_s'] - row['submitted_wall_s']
                if before:
                    after = list(map(int, sched.read_text().split()))
                    row['runnable_wait_s'] = (after[1] - before[1]) / 1e9
        future = executor.submit(work)
        future.scan_timing = row
        return future

    def result(self, future):
        row = future.scan_timing
        row['checked_wall_s'] = time.monotonic()
        row['wall_at_check_s'] = row['checked_wall_s'] - row['submitted_wall_s']
        # Native time can catch up after wall lag. The next native capture
        # does not imply that the original100ms wall budget has elapsed.
        remaining = row['submitted_wall_s'] + PERIOD_S - row['checked_wall_s']
        try:
            value = future.result(timeout=max(0., remaining))
        except FutureTimeout:
            if future.done():
                # Preserve a worker-raised TimeoutError, or check a completion
                # racing the wait timeout against its actual finish timestamp.
                value = future.result()
            else:
                row['deadline_failed'] = True
                raise RuntimeError(ERROR) from None
        row['waited_wall_s'] = time.monotonic() - row['checked_wall_s']
        if row['finished_wall_s'] - row['submitted_wall_s'] > PERIOD_S:
            row['deadline_failed'] = True
            raise RuntimeError(ERROR)
        row['deadline_failed'] = False
        return value

    def save(self, path):
        Path(path).write_text(''.join(json.dumps(row) + '\n' for row in self.records))
