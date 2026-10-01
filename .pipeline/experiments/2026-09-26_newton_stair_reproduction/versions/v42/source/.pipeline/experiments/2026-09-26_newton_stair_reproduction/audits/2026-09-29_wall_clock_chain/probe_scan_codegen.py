"""Offline measurement of the two in-process GIL holders found in diag_v31_clock03.

1. Per-scan kernel rebuild: newton.intersect_ray (newton/_src/geometry/raycast.py) defines
   `_intersect_ray_kernel` inside the function, so each call constructs a new wp.Kernel (Python AST
   parse and codegen, under the GIL) before Warp finds the cached binary. This measures
   GeometricLidar.scan with that pinned code path, the time spent inside wp.Kernel construction, and
   the same scans with one kernel built once and reused (outputs compared bitwise).
2. Full garbage collections: the duration of gc.collect(2) at the heap of a freshly built worker and
   after retaining telemetry-like rows as newton_episode.py does (one dict per 20 ms control step).
Diagnostic only; the robot is built as in the trials but not stepped (static scene, fixed pose).
"""
import gc
import json
import os
from pathlib import Path
import sys
import time

import numpy as np
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")

H = Path(__file__).resolve().parent
E = H.parents[1]
sys.path.insert(0, str(E / "scripts"))
from robot_scene import StairRobot  # noqa: E402
from geometric_lidar import GeometricLidar  # noqa: E402
import newton  # noqa: E402
from newton._src.geometry import raycast  # noqa: E402

kernel_ns = []
original_init = wp.Kernel.__init__


def timed_init(self, *args, **kwargs):
    started = time.perf_counter_ns()
    try:
        return original_init(self, *args, **kwargs)
    finally:
        kernel_ns.append(time.perf_counter_ns() - started)


gc_events = []
gc_started = {}


def gc_callback(phase, info):
    if phase == "start":
        gc_started["t"] = time.perf_counter_ns()
    else:
        gc_events.append((info["generation"], time.perf_counter_ns() - gc_started.get("t", time.perf_counter_ns()),
                          info.get("collected", 0)))


def scans(lidar, robot, count):
    walls, outputs = [], []
    pose = robot.body_and_sensor()
    for index in range(count):
        started = time.perf_counter_ns()
        points, world, info, _, extra = lidar.scan(index, 0.0, override_pose=pose, captured_state=robot.state)
        walls.append((time.perf_counter_ns() - started) / 1e6)
        outputs.append((extra["ranges"].copy(), extra["shape_id"].copy()))
    return walls, outputs


def main():
    out = H / "probe_scan_codegen.json"
    scenario = json.loads((E / "runs/v31_historical_full01/inputs/stair_scenario.json").read_text())
    robot = StairRobot(startup_mode="factory_pd", stance_hold=True, automatic_contact_capacity=True, scenario=scenario)
    lidar = GeometricLidar(robot, None, emitter_self_exclusion=True, visible_human_only=True)
    lidar.scan(0, 0.0, override_pose=robot.body_and_sensor(), captured_state=robot.state)  # warm the module load
    gc.callbacks.append(gc_callback)
    wp.Kernel.__init__ = timed_init
    kernel_ns.clear()
    gc_events.clear()
    pinned_walls, pinned_outputs = scans(lidar, robot, 40)
    pinned_kernel_ms = [k / 1e6 for k in kernel_ns]
    pinned_gc = list(gc_events)
    wp.Kernel.__init__ = original_init

    # Same code, kernel constructed once: capture the first kernel object and reuse it.
    cached = {}
    original_kernel_decorator = wp.kernel

    def caching_kernel(*args, **kwargs):
        decorator = original_kernel_decorator(*args, **kwargs)

        def wrap(function):
            key = (function.__qualname__, json.dumps(kwargs.get("module_options", {}), sort_keys=True))
            if key not in cached:
                cached[key] = decorator(function)
            return cached[key]
        return wrap

    raycast.wp.kernel = caching_kernel
    try:
        wp.Kernel.__init__ = timed_init
        kernel_ns.clear()
        gc_events.clear()
        cached_walls, cached_outputs = scans(lidar, robot, 40)
        cached_kernel_ms = [k / 1e6 for k in kernel_ns]
        cached_gc = list(gc_events)
    finally:
        raycast.wp.kernel = original_kernel_decorator
        wp.Kernel.__init__ = original_init
    identical = all(np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
                    for a, b in zip(pinned_outputs, cached_outputs))

    gc.callbacks.remove(gc_callback)
    heap = {}
    for retained_steps in (0, 1000, 28000):
        rows = []
        template = json.loads(next(open(E / "runs/v31_historical_full01/telemetry.jsonl")))
        for _ in range(retained_steps):
            rows.append(json.loads(json.dumps(template)))
        durations = []
        for _ in range(3):
            started = time.perf_counter_ns()
            gc.collect(2)
            durations.append((time.perf_counter_ns() - started) / 1e6)
        heap[str(retained_steps)] = {"tracked_objects": len(gc.get_objects()), "full_collection_ms": durations}
        del rows

    def stats(values):
        values = np.asarray(values)
        return {"n": int(len(values)), "median": float(np.median(values)), "max": float(values.max()),
                "total": float(values.sum())}

    result = {
        "pinned_per_scan": {"scan_wall_ms": stats(pinned_walls), "kernel_constructions": len(pinned_kernel_ms),
                            "kernel_construction_ms": stats(pinned_kernel_ms) if pinned_kernel_ms else None,
                            "gc_collections": [[g, round(d / 1e6, 2), c] for g, d, c in pinned_gc]},
        "kernel_built_once": {"scan_wall_ms": stats(cached_walls), "kernel_constructions": len(cached_kernel_ms),
                              "gc_collections": [[g, round(d / 1e6, 2), c] for g, d, c in cached_gc]},
        "outputs_bitwise_identical": identical,
        "full_collection_by_retained_rows": heap,
        "gc_thresholds": gc.get_threshold(),
    }
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
