"""Instrumented Newton worker: runs the unchanged pinned scripts/newton_episode.py as __main__.

Added observation only (no behavior change):
- every control step (Lite3Newton.step): wall time, main-thread CPU time, and the process's
  rusage_info_v6 deltas (CPU time, the part on performance cores, time runnable but waiting for a CPU,
  page-ins) into diagnostics/steps.npy, and the absolute values at each step's start and end into
  diagnostics/steps_abs.npy, so that the time between steps can be measured as well;
- every physics substep (Lite3Newton._motor_substep): start, wall time and main-thread CPU time;
- a Python watchdog thread that polls every 10 ms and logs every wake-up time into
  diagnostics/watchdog_wakeups.npy (a continuous liveness signal: it cannot wake while another thread
  holds the GIL). While a control step has run for more than 150 ms, it also records every thread's
  Python stack (sys._current_frames(), under the GIL) every 50 ms, up to 8 times per step, and how late
  its own wake-up was, into diagnostics/stall_stacks.jsonl;
- the same stack samples when more than 150 ms pass between the end of one control step and the start of
  the next (kind "between_sample");
- every cyclic garbage collection (gc.callbacks): start, wall duration, generation, collected count, the
  thread that ran it, whether it was the main thread, whether it was an explicit gc.collect() call
  (gc.collect is wrapped to mark the calling thread; the wrapper calls the original), and the collecting
  thread's CPU time during it, into diagnostics/gc_events.npy;
- every telemetry frame the worker's TelemetryPublisherServer handles: when it was enqueued (message type,
  stamp) and when the sender thread sent it (start, end, success), into
  diagnostics/telemetry_frames_enqueued.npy and diagnostics/telemetry_frames_sent.npy, from preallocated
  arrays so the recording itself makes no garbage;
- the names and idents of all threads every 2 s, to read those stacks.

This file imports nothing from Warp or Newton itself. It patches lite3_newton through an import hook when
the pinned code first imports it, so newton_episode.py's own preamble (kernel cache directory, wp.init)
runs first, exactly as in a trial. Attempt 1 initialized Warp here first; the pinned preamble then reset
the kernel cache directory and every kernel was compiled cold (diag_v31_clock01, invalid). Attempt 2 used
faulthandler.dump_traceback_later, which walks thread stacks without the GIL: it raced with the running
main thread, looped in dump_frame, and the main thread deadlocked in cancel_dump_traceback_later
(diag_v31_clock02, invalid). This version captures stacks only under the GIL.
"""
import importlib.abc
import importlib.util
import gc
import json
import os
from pathlib import Path
import runpy
import sys
import threading
import time
import traceback

import numpy as np

H = Path(__file__).resolve().parent
E = H.parents[1]
sys.path.insert(0, str(H))
import rusage_v6  # noqa: E402

out = Path(os.environ["NEWTON_RUN_DIR"])
diagnostics = out / "diagnostics"
diagnostics.mkdir(exist_ok=True)
stacks = open(diagnostics / "stall_stacks.jsonl", "w")
current = {"started": None, "ended": None, "physics_steps": 0, "captures": 0, "next_ns": 0}
steps = []
steps_abs = []
substeps = np.zeros((800_000, 4), dtype=np.int64)
count = [0]


def patch(module):
    original_step = module.Lite3Newton.step
    original_substep = module.Lite3Newton._motor_substep

    def step(self, command):
        usage = rusage_v6.read()
        started, thread_cpu = time.monotonic_ns(), time.thread_time_ns()
        current.update(ended=None, physics_steps=self.steps, captures=0, next_ns=150_000_000)
        current["started"] = started
        try:
            return original_step(self, command)
        finally:
            current["started"] = None
            finished, thread_after = time.monotonic_ns(), time.thread_time_ns()
            current.update(ended=finished, physics_steps=self.steps, captures=0, next_ns=150_000_000)
            after = rusage_v6.read()
            row = (started, finished - started, thread_after - thread_cpu, after[0] - usage[0], after[1] - usage[1],
                   after[2] - usage[2], after[3] - usage[3], self.steps)
            steps.append(row)
            steps_abs.append((started, finished, thread_cpu, thread_after, usage[0], after[0], usage[1], after[1],
                              usage[2], after[2], usage[3], after[3], self.steps))
            if row[1] > 150_000_000:
                with lock:
                    stacks.write(json.dumps({"kind": "step_end", "started_ns": row[0], "wall_ms": row[1] / 1e6,
                        "main_thread_cpu_ms": row[2] / 1e6, "process_cpu_ms": row[3] / 1e6,
                        "process_pcore_cpu_ms": row[4] / 1e6, "process_runnable_ms": row[5] / 1e6,
                        "pageins": row[6], "physics_steps": row[7]}) + "\n")
                    stacks.flush()

    def motor_substep(self, *, feedforward_torque=None):
        started, thread_cpu = time.monotonic_ns(), time.thread_time_ns()
        try:
            return original_substep(self, feedforward_torque=feedforward_torque)
        finally:
            index = count[0]
            if index < len(substeps):
                substeps[index] = (started, time.monotonic_ns() - started, time.thread_time_ns() - thread_cpu,
                                   self.steps)
                count[0] = index + 1

    module.Lite3Newton.step = step
    module.Lite3Newton._motor_substep = motor_substep


frames = np.zeros((2, 1_500_000, 6), dtype=np.int64)   # [enqueue, send] x rows x (type, stamp, t0, t1, ok, 0)
frame_count = [0, 0]


def patch_transport(module):
    header = module.HEADER_STRUCT if hasattr(module, "HEADER_STRUCT") else None
    if header is None:
        from lite3_sim_bridge.protocol import HEADER_STRUCT as header
    cls = module.TelemetryPublisherServer
    original_enqueue, original_send = cls._enqueue, cls._send_now

    def enqueue(self, message_type, frame_bytes):
        now = time.monotonic_ns()
        index = frame_count[0]
        if index < frames.shape[1]:
            frames[0, index, :5] = (int(message_type), header.unpack_from(frame_bytes)[7], now, now, 1)
            frame_count[0] = index + 1
        return original_enqueue(self, message_type, frame_bytes)

    def send_now(self, connection, frame_bytes):
        begin = time.monotonic_ns()
        sent = original_send(self, connection, frame_bytes)
        index = frame_count[1]
        if index < frames.shape[1]:
            fields = header.unpack_from(frame_bytes)
            frames[1, index, :5] = (fields[2], fields[7], begin, time.monotonic_ns(), int(bool(sent)))
            frame_count[1] = index + 1
        return sent

    cls._enqueue, cls._send_now = enqueue, send_now


PATCHED_MODULES = {"lite3_newton": patch, "lite3_sim_bridge.transport": patch_transport}


class PatchOnImport(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name not in PATCHED_MODULES:
            return None
        sys.meta_path.remove(self)
        try:
            spec = importlib.util.find_spec(name)
        finally:
            sys.meta_path.insert(0, self)
        original_exec = spec.loader.exec_module

        def exec_module(module):
            original_exec(module)
            PATCHED_MODULES[name](module)
        spec.loader.exec_module = exec_module
        return spec


sys.meta_path.insert(0, PatchOnImport())
stop = threading.Event()
lock = threading.Lock()


wakeups = np.zeros(600_000, dtype=np.int64)
wakeup_count = [0]


def watchdog():
    names = {}
    expected = time.monotonic_ns() + 10_000_000
    while not stop.is_set():
        time.sleep(.01)
        now = time.monotonic_ns()
        index = wakeup_count[0]
        if index < len(wakeups):
            wakeups[index] = now
            wakeup_count[0] = index + 1
        late_ms, expected = (now - expected) / 1e6, now + 10_000_000
        started, ended = current["started"], current["ended"]
        reference, kind = (started, "stall_sample") if started is not None else (ended, "between_sample")
        if reference is None or now - reference < current["next_ns"] or current["captures"] >= 8:
            continue
        frames = sys._current_frames()
        names.update((t.ident, t.name) for t in threading.enumerate())
        record = {"kind": kind, "step_started_ns": reference, "elapsed_ms": (now - reference) / 1e6,
                  "physics_steps_at_start": current["physics_steps"], "watchdog_wake_late_ms": late_ms,
                  "stacks": {names.get(ident, str(ident)): [line.strip() for line in traceback.format_stack(frame)[-10:]]
                             for ident, frame in frames.items() if names.get(ident) != "diag-watchdog"}}
        current["captures"] += 1
        current["next_ns"] += 50_000_000
        with lock:
            stacks.write(json.dumps(record) + "\n")
            stacks.flush()


threading.Thread(target=watchdog, daemon=True, name="diag-watchdog").start()
gc_events = np.zeros((2_000_000, 8), dtype=np.int64)
gc_count = [0]
gc_started = {}
explicit_threads = set()
original_collect = gc.collect


def marked_collect(*args, **kwargs):
    ident = threading.get_ident()
    explicit_threads.add(ident)
    try:
        return original_collect(*args, **kwargs)
    finally:
        explicit_threads.discard(ident)


gc.collect = marked_collect


def gc_callback(phase, info):
    if phase == "start":
        gc_started[threading.get_ident()] = (time.monotonic_ns(), time.thread_time_ns())
        return
    ident = threading.get_ident()
    begun = gc_started.pop(ident, None)
    index = gc_count[0]
    if begun is not None and index < len(gc_events):
        gc_events[index] = (begun[0], time.monotonic_ns() - begun[0], info["generation"], info.get("collected", 0),
                            ident, int(ident == threading.main_thread().ident), int(ident in explicit_threads),
                            time.thread_time_ns() - begun[1])
        gc_count[0] = index + 1


gc.callbacks.append(gc_callback)


def list_threads():
    with open(diagnostics / "threads.jsonl", "w") as f:
        while not stop.is_set():
            f.write(json.dumps({"monotonic_ns": time.monotonic_ns(), "main": threading.main_thread().ident,
                                "threads": [[t.ident, t.name] for t in threading.enumerate()]}) + "\n")
            f.flush()
            stop.wait(2.)


threading.Thread(target=list_threads, daemon=True, name="diag-thread-list").start()
sys.path.insert(0, str(E / "scripts"))
try:
    runpy.run_path(str(E / "scripts/newton_episode.py"), run_name="__main__")
finally:
    stop.set()
    np.save(diagnostics / "steps.npy", np.asarray(steps, dtype=np.int64))
    np.save(diagnostics / "steps_abs.npy", np.asarray(steps_abs, dtype=np.int64))
    np.save(diagnostics / "substeps.npy", substeps[:count[0]])
    np.save(diagnostics / "gc_events.npy", gc_events[:gc_count[0]])
    np.save(diagnostics / "watchdog_wakeups.npy", wakeups[:wakeup_count[0]])
    np.save(diagnostics / "telemetry_frames_enqueued.npy", frames[0, :frame_count[0], :5])
    np.save(diagnostics / "telemetry_frames_sent.npy", frames[1, :frame_count[1], :5])
    stacks.close()
