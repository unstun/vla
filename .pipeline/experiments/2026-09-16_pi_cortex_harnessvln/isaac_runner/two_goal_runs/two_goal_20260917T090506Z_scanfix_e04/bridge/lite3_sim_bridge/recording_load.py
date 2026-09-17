"""Move HD encoding and bulk evidence writes off the physics thread.

Video encoding and multi-megabyte JSONL writes ran inline in the control loop.
That cost is what stretched 45 simulation seconds into 105.9 wall seconds, and
the resulting 2.35x slowdown is exactly what pushed a 0.1 s simulation-period
feedback stream past a 0.25 s wall-clock deadline. Recording load was therefore
not a side concern; it was part of the causal chain.

Isaac's rendering call must stay on the thread that owns the simulation, so
``render()`` is *not* moved here. Only the work after the frame exists --
encoding it, and serialising evidence rows -- runs on this worker.

Correctness rules:

* Bounded queue. An unbounded one would trade a stall for unbounded memory.
* Never silently drop. Evidence is the product; when the queue is full the
  producer blocks, and the blocking time is measured and reported.
* A worker exception is re-raised on the producer thread at the next submit or
  at ``close()``. A crashed writer must fail the run, not truncate the record.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Callable, Optional


class AsyncRecorder:
    """Single background worker for encoding and bulk file writes."""

    def __init__(self, name: str = "lite3-recorder", max_pending: int = 64) -> None:
        if max_pending <= 0:
            raise ValueError("max_pending must be positive")
        self._queue = queue.Queue(maxsize=max_pending)  # type: queue.Queue
        self._error = None  # type: Optional[BaseException]
        self._error_lock = threading.Lock()
        self._closed = False
        self._submitted = 0
        self._completed = 0
        self._max_queue_depth = 0
        self._blocked_submits = 0
        self._total_block_ns = 0
        self._max_block_ns = 0
        self._thread = threading.Thread(target=self._run, name=name, daemon=True)
        self._thread.start()

    def submit(self, work: Callable[[], None]) -> None:
        """Queue one unit of recording work, blocking only if the queue is full."""
        self._raise_worker_error()
        if self._closed:
            raise RuntimeError("recorder is closed")
        started_ns = time.monotonic_ns()
        try:
            self._queue.put(work, block=False)
        except queue.Full:
            self._blocked_submits += 1
            self._queue.put(work, block=True)
            blocked_ns = time.monotonic_ns() - started_ns
            self._total_block_ns += blocked_ns
            self._max_block_ns = max(self._max_block_ns, blocked_ns)
        self._submitted += 1
        self._max_queue_depth = max(self._max_queue_depth, self._queue.qsize())

    def _run(self) -> None:
        while True:
            work = self._queue.get()
            if work is None:
                self._queue.task_done()
                return
            try:
                work()
            except BaseException as error:  # noqa: BLE001 - reported to the producer
                with self._error_lock:
                    if self._error is None:
                        self._error = error
            finally:
                self._completed += 1
                self._queue.task_done()

    def _raise_worker_error(self) -> None:
        with self._error_lock:
            error = self._error
        if error is not None:
            raise RuntimeError("recording worker failed") from error

    def close(self, timeout_seconds: float = 120.0) -> None:
        """Drain every queued item, then stop. Raises if the worker failed."""
        if self._closed:
            self._raise_worker_error()
            return
        self._closed = True
        self._queue.put(None)
        self._thread.join(timeout=timeout_seconds)
        if self._thread.is_alive():
            raise RuntimeError("recording worker did not finish within the timeout")
        self._raise_worker_error()

    def metrics(self) -> dict:
        return {
            "submitted": self._submitted,
            "completed": self._completed,
            "max_queue_depth": self._max_queue_depth,
            "blocked_submits": self._blocked_submits,
            "max_submit_block_ns": self._max_block_ns,
            "total_submit_block_ns": self._total_block_ns,
            "mean_submit_block_ns": (
                int(self._total_block_ns / self._blocked_submits)
                if self._blocked_submits
                else 0
            ),
        }
