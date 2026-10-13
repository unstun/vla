"""Diagnostic-only observation inside the planner container (loaded by Python at start-up).

Active only when DIAG_CONTAINER_OUT is set, which diag_launch.py does for instrumented runs; the pinned
image, sources and run_local_episode.py are unchanged. For every Python process it records each cyclic
garbage collection (start and duration in CLOCK_MONOTONIC ns, generation, collected, thread). In the
lite3_sim_bridge process it also records, for every complete body state, when the telemetry thread offered
it (CompleteStateStream.offer) and when the 10 ms timer delivered it (take), and the start and duration of
each FoxyBridgeNode._publish_latest callback. Records are kept in append-only buffers and written by index
every 0.5 s and at a normal interpreter exit: <out>/<pid>_<kind>.i64 (int64 rows), with <out>/<pid>_cmdline.txt naming the
process. No signal handler is installed (the observed processes' shutdown must not change), so up to 0.5 s
before a SIGTERM/SIGKILL teardown can be lost. This module shadows Ubuntu's own sitecustomize (an apport
crash hook) in the container's Python processes, a difference from diag_v31_clock04's container.
"""
import os

OUT = os.environ.get("DIAG_CONTAINER_OUT")
if OUT:
    try:
        import array
        import gc
        import importlib.abc
        import importlib.util
        import sys
        import threading
        import time

        PID = os.getpid()
        buffers = {"gc": array.array("q"), "offer": array.array("q"), "take": array.array("q"),
                   "publish": array.array("q")}
        widths = {"gc": 5, "offer": 3, "take": 2, "publish": 2}
        # Append-only buffers flushed by index: writers never take a lock (one extend call appends a whole row
        # atomically under the GIL), and only the two flush paths share flush_lock, so no row is lost and the
        # files stay in append order.
        flushed = {kind: 0 for kind in buffers}
        flush_lock = threading.Lock()
        started = {}

        def on_gc(phase, info):
            ident = threading.get_ident()
            if phase == "start":
                started[ident] = time.monotonic_ns()
                return
            begin = started.pop(ident, None)
            if begin is not None:
                buffers["gc"].extend((begin, time.monotonic_ns() - begin, info["generation"],
                                      info.get("collected", 0), ident & 0x7FFFFFFFFFFFFFFF))

        gc.callbacks.append(on_gc)

        def flush_once():
            with flush_lock:
                for kind, rows in buffers.items():
                    end = len(rows)
                    end -= end % widths[kind]
                    if end > flushed[kind]:
                        with open(os.path.join(OUT, f"{PID}_{kind}.i64"), "ab") as f:
                            rows[flushed[kind]:end].tofile(f)
                        flushed[kind] = end

        def flush():
            os.makedirs(OUT, exist_ok=True)
            try:
                with open("/proc/self/cmdline", "rb") as f:
                    command = f.read().replace(b"\0", b" ").decode(errors="replace")
                with open(os.path.join(OUT, f"{PID}_cmdline.txt"), "w") as f:
                    f.write(command + "\n")
            except OSError:
                pass
            while True:
                time.sleep(.5)
                flush_once()

        import atexit
        atexit.register(flush_once)
        threading.Thread(target=flush, daemon=True, name="diag-flush").start()

        def patch_state_stream(module):
            cls = module.CompleteStateStream
            offer, take = cls.offer, cls.take

            def timed_offer(self, state, receive_monotonic_ns, monitor_accepted=True):
                result = offer(self, state, receive_monotonic_ns, monitor_accepted)
                buffers["offer"].extend((int(state.simulation_time_ns), int(receive_monotonic_ns), int(bool(result))))
                return result

            def timed_take(self):
                taken = take(self)
                if taken is not None:
                    buffers["take"].extend((int(taken[0].simulation_time_ns), time.monotonic_ns()))
                return taken

            cls.offer, cls.take = timed_offer, timed_take

        def patch_bridge_node(module):
            cls = module.FoxyBridgeNode
            publish = cls._publish_latest

            def timed_publish(self):
                begin = time.monotonic_ns()
                try:
                    return publish(self)
                finally:
                    buffers["publish"].extend((begin, time.monotonic_ns() - begin))

            cls._publish_latest = timed_publish

        PATCHES = {"lite3_sim_bridge.state_stream": patch_state_stream,
                   "lite3_sim_bridge.foxy_bridge_node": patch_bridge_node}

        class PatchOnImport(importlib.abc.MetaPathFinder):
            def find_spec(self, name, path, target=None):
                if name not in PATCHES:
                    return None
                sys.meta_path.remove(self)
                try:
                    spec = importlib.util.find_spec(name)
                finally:
                    sys.meta_path.insert(0, self)
                if spec is None or spec.loader is None:
                    return spec
                original = spec.loader.exec_module

                def exec_module(module):
                    original(module)
                    PATCHES[name](module)
                spec.loader.exec_module = exec_module
                return spec

        sys.meta_path.insert(0, PatchOnImport())
    except Exception:  # observation must never break the observed process
        pass
