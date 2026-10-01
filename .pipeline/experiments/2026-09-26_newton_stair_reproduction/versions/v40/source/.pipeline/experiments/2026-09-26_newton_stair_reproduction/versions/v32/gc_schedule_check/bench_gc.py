"""K3: v31's recorded commands through the same physics, LiDAR scan thread and writer thread, with a GC schedule.

Derived from audits/2026-09-29_wall_clock_chain/bench_physics.py. Differences: it retains what
newton_episode.py retains (every telemetry row, a video state every 4 steps, one cloud record per scan) and
applies BENCH_GC_MODE at the same places as v32's scripts/newton_episode.py:
  none            no freezing (v31);
  freeze          gc.freeze() before the loop and after every 50th step (candidate 1, attempt01/);
  collect_freeze  gc.collect(); gc.freeze() at the same places (v32).
Every collection is logged with gc.callbacks (start, duration, generation, collected, main thread,
explicit). At the end, gc.collect() first reclaims the unfrozen garbage still pending since the last window;
then gc.unfreeze(); gc.collect() counts exactly what the schedule had frozen although it was garbage (the
leak). Run 01 (run01/) counted both together, an upper bound. Outputs in $BENCH_OUT: gc_events.npy,
summary.json.
"""
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from collections import deque

import numpy as np
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")

E = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(E / "scripts"))
from robot_scene import StairRobot  # noqa: E402
from geometric_lidar import GeometricLidar  # noqa: E402
from factory_navigation_startup import initialize  # noqa: E402

MODE = os.environ["BENCH_GC_MODE"]
assert MODE in ("none", "freeze", "collect_freeze")
events = []
started = {}
explicit = [False]


def on_gc(phase, info):
    ident = threading.get_ident()
    if phase == "start":
        started[ident] = time.monotonic_ns()
        return
    begin = started.pop(ident, None)
    if begin is not None:
        events.append((begin, time.monotonic_ns() - begin, info["generation"], info.get("collected", 0),
                       int(ident == threading.main_thread().ident), int(explicit[0])))


def schedule():
    if MODE == "collect_freeze":
        explicit[0] = True
        gc.collect()
        explicit[0] = False
    if MODE in ("freeze", "collect_freeze"):
        gc.freeze()


def main():
    out = Path(os.environ["BENCH_OUT"])
    trial = Path(os.environ["BENCH_TRIAL"])
    out.mkdir(parents=True, exist_ok=False)
    scenario = json.loads((trial / "inputs/stair_scenario.json").read_text())
    recorded = []
    with open(trial / "telemetry.jsonl") as f:
        for line in f:
            row = json.loads(line)
            recorded.append((row["state_sequence"], row["requested_command"], row["joint_q"]))
    robot = StairRobot(startup_mode="factory_pd", stance_hold=True, automatic_contact_capacity=True, scenario=scenario)
    lidar = GeometricLidar(robot, None, emitter_self_exclusion=True, visible_human_only=True)
    initialize(robot, out)
    (out / "clouds").mkdir()
    rows, video_states, clouds = [], [], []
    worst = 0.
    sink = (out / "writer_sink.jsonl").open("w")
    rows_file = (out / "rows.jsonl").open("w")
    gc.callbacks.append(on_gc)
    with ThreadPoolExecutor(max_workers=1) as writer, ThreadPoolExecutor(max_workers=1) as scanner:
        io_jobs, pending = deque(), None

        def save_line(stream, value):
            stream.write(json.dumps(value) + "\n")
            stream.flush()

        def save_cloud(points, world, item):
            path = out / item["file"]
            np.savez_compressed(path, sensor_points=points, world_points=world)
            item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            save_line(sink, item)

        scan_index = 0
        schedule()
        loop_started = time.monotonic_ns()
        for step, (sequence, command, joint_q) in enumerate(recorded):
            while io_jobs and io_jobs[0].done():
                io_jobs.popleft().result()
            robot.step(command)
            row = robot.telemetry()
            pose = robot.body_and_sensor()
            sim_time = row["physics_time_s"]
            worst = max(worst, float(np.max(np.abs(np.asarray(row["joint_q"]) - np.asarray(joint_q)))))
            row.update(command=list(command), requested_command=list(command), body_sensor=pose, state_sequence=step + 1)
            if pending is not None and pending[0].done():
                points, world, info, actor, _ = pending[0].result()
                item = {"sim_time_s": pending[3], "stamp_ns": round(pending[3] * 1e9), "body_sensor": pending[2],
                        "sensor": info, "actor_scoring_only": actor, "file": f"clouds/{pending[1]:05d}.npz",
                        "published_at_physics_s": robot.physics_time()}
                clouds.append(item)
                io_jobs.append(writer.submit(save_cloud, points, world, item))
                pending = None
            if (step + 1) % 5 == 0:
                if pending is not None:
                    raise RuntimeError("Captured scan did not finish before the next sensor period")
                captured = robot.model.state()
                captured.body_q.assign(robot.state.body_q)
                pending = (scanner.submit(lidar.scan, scan_index, sim_time, override_pose=pose, captured_state=captured),
                           scan_index, pose, sim_time)
                scan_index += 1
            if (step + 1) % 4 == 0:
                video_states.append({"physics_time_s": sim_time, "body_q": robot.state.body_q.numpy().tolist(),
                                     "joint_q": row["joint_q"], "command": list(command), "command_reason": "active",
                                     "controller_phase": row["controller_phase"], "policy_calls": robot.policy_calls,
                                     "stance_mode": row.get("stance_mode", "OFF"),
                                     "policy_owns_joints": row.get("policy_owns_joints", True),
                                     "navigation_ready": robot.navigation_ready, "goal_sent": True,
                                     "last_backend_error": None})
            io_jobs.append(writer.submit(save_line, rows_file, row))
            rows.append(row)
            if (step + 1) % 50 == 0:
                schedule()
        loop_finished = time.monotonic_ns()
        if pending is not None:
            pending[0].result(timeout=5)
        for job in io_jobs:
            job.result(timeout=10)
    gc.callbacks.remove(on_gc)
    pending_garbage = gc.collect()
    frozen_before_unfreeze = gc.get_freeze_count()
    gc.unfreeze()
    garbage_after_unfreeze = gc.collect()
    sink.close()
    rows_file.close()
    log = np.asarray(events, dtype=np.int64).reshape(-1, 6)
    np.save(out / "gc_events.npy", log)
    loop = log[(log[:, 0] >= loop_started) & (log[:, 0] <= loop_finished)]

    def durations(mask):
        d = loop[mask, 1] / 1e6
        return {"count": int(len(d)), "max_ms": float(d.max()) if len(d) else 0.0,
                "median_ms": float(np.median(d)) if len(d) else 0.0}
    summary = {
        "mode": MODE, "control_steps": len(recorded), "scans": scan_index, "joint_q_worst_error": worst,
        "loop_wall_s": (loop_finished - loop_started) / 1e9,
        "collections_in_loop": {"generation0": durations(loop[:, 2] == 0), "generation1": durations(loop[:, 2] == 1),
                                "generation2_automatic": durations((loop[:, 2] == 2) & (loop[:, 5] == 0)),
                                "explicit": durations(loop[:, 5] == 1)},
        "longest_collection_in_loop_ms": float(loop[:, 1].max() / 1e6) if len(loop) else 0.0,
        "startup_explicit_collection_ms": [round(float(d) / 1e6, 1) for d in
                                           log[(log[:, 0] < loop_started) & (log[:, 5] == 1), 1]],
        "unfrozen_garbage_pending_at_end": pending_garbage,
        "frozen_objects_at_end": frozen_before_unfreeze,
        "frozen_garbage": garbage_after_unfreeze,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "retained": {"rows": len(rows), "video_states": len(video_states), "clouds": len(clouds)},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
