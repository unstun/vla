"""Replay a recorded trial's control commands through the same Newton physics, off the live stack.

Diagnostic only; no navigation, planner or network. It rebuilds the trial's robot and Building exactly as
newton_episode.py does (factory PD startup, stance hold, automatic contact capacity), then steps the
recorded `requested_command` of every control row. Like the episode, it publishes a body pose every 5
physics substeps (here: records the publish instant), submits the geometric LiDAR scan of a captured state
to a worker thread every 5 control steps, and writes JSON rows and compressed clouds from a writer thread.
An in-process thread sleeps 20 ms in a loop and records how late it wakes (the clock client's cadence).

Outputs in $BENCH_OUT: steps.jsonl (per control step), publishes.npy (pose publish instants, ns),
probe_in.npy (in-process wake-up lateness, ns), summary.json. It also compares each replayed joint state
with the trial's recorded one, which tells whether the replay reproduces the trial's physical states.
"""
import json
import os
from pathlib import Path
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import hashlib

import numpy as np
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")

E = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(E / "scripts"))
from robot_scene import StairRobot  # noqa: E402
from geometric_lidar import GeometricLidar  # noqa: E402
from factory_navigation_startup import initialize  # noqa: E402


def main():
    out = Path(os.environ["BENCH_OUT"])
    trial = Path(os.environ["BENCH_TRIAL"])
    limit = int(os.environ.get("BENCH_STEPS", "0")) or None
    out.mkdir(parents=True, exist_ok=False)
    scenario = json.loads((trial / "inputs/stair_scenario.json").read_text())
    recorded = []
    with open(trial / "telemetry.jsonl") as f:
        for line in f:
            row = json.loads(line)
            recorded.append((row["state_sequence"], row["requested_command"], row["joint_q"], row["physics_time_s"],
                             row["control_wall_s"]))
    recorded = recorded[:limit]
    backend_payload = json.loads((trial / "backend_latest.json").read_text())

    robot = StairRobot(startup_mode="factory_pd", stance_hold=True, automatic_contact_capacity=True,
                       scenario=scenario)
    lidar = GeometricLidar(robot, None, emitter_self_exclusion=True, visible_human_only=True)
    initialize(robot, out)

    stop = threading.Event()
    lateness = []

    def probe():
        while not stop.is_set():
            start = time.monotonic_ns()
            time.sleep(.02)
            lateness.append(time.monotonic_ns() - start - 20_000_000)

    publishes = []

    def observer(current):
        if current.steps % 5 == 0:
            publishes.append((time.monotonic_ns(), current.steps))

    robot.physics_observer = observer
    probe_thread = threading.Thread(target=probe, daemon=True, name="bench-probe")
    probe_thread.start()
    (out / "clouds").mkdir()
    rows_path = (out / "steps.jsonl").open("w")
    sink = (out / "writer_sink.jsonl").open("w")
    records = []
    worst_joint_error = 0.
    first_divergent = None
    with ThreadPoolExecutor(max_workers=1) as writer, ThreadPoolExecutor(max_workers=1) as scanner:
        io_jobs, pending = deque(), None

        def save_line(stream, value):
            stream.write(json.dumps(value) + "\n")
            stream.flush()

        def save_cloud(points, world, index):
            path = out / "clouds" / f"{index:05d}.npz"
            np.savez_compressed(path, sensor_points=points, world_points=world)
            save_line(sink, {"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

        scan_index = 0
        for index, (sequence, command, joint_q, sim_time, trial_wall) in enumerate(recorded):
            while io_jobs and io_jobs[0].done():
                io_jobs.popleft().result()
            loop_started = time.monotonic_ns()
            robot.step(command)
            physics_finished = time.monotonic_ns()
            row = robot.telemetry()
            pose = robot.body_and_sensor()
            error = float(np.max(np.abs(np.asarray(row["joint_q"]) - np.asarray(joint_q))))
            worst_joint_error = max(worst_joint_error, error)
            if first_divergent is None and error > 1e-6:
                first_divergent = {"state_sequence": sequence, "joint_q_error": error}
            record = {"state_sequence": sequence, "sim_time_s": row["physics_time_s"], "trial_sim_time_s": sim_time,
                      "control_wall_s": (physics_finished - loop_started) / 1e9, "trial_control_wall_s": trial_wall,
                      "stance_mode": row.get("stance_mode"), "joint_q_error": error,
                      "step_started_ns": loop_started, "step_finished_ns": physics_finished}
            records.append(record)
            io_jobs.append(writer.submit(save_line, rows_path, row))
            if pending is not None and pending[0].done():
                points, world, info, _, _ = pending[0].result()
                io_jobs.append(writer.submit(save_cloud, points, world, pending[1]))
                pending = None
            if sequence % 5 == 0:
                if pending is not None:
                    raise RuntimeError("Captured scan did not finish before the next sensor period")
                captured = robot.model.state()
                captured.body_q.assign(robot.state.body_q)
                pending = (scanner.submit(lidar.scan, scan_index, sim_time, override_pose=pose, captured_state=captured),
                           scan_index)
                scan_index += 1
                io_jobs.append(writer.submit(save_line, sink, {"sim_time_s": sim_time, "data": backend_payload}))
        if pending is not None:
            pending[0].result(timeout=5)
        for job in io_jobs:
            job.result(timeout=10)
    stop.set()
    probe_thread.join(timeout=1)
    rows_path.close()
    sink.close()
    with open(out / "steps_summary.jsonl", "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    np.save(out / "publishes.npy", np.asarray(publishes, dtype=np.int64))
    np.save(out / "probe_in.npy", np.asarray(lateness, dtype=np.int64))
    walls = np.array([r["control_wall_s"] for r in records])
    stamps = np.asarray(publishes, dtype=np.int64)
    gaps = np.diff(stamps[:, 0]) / 1e9 if len(stamps) > 1 else np.zeros(0)
    late = np.asarray(lateness) / 1e6
    summary = {
        "trial": str(trial), "control_steps": len(records), "physics_steps": robot.steps,
        "sim_time_s": [records[0]["sim_time_s"], records[-1]["sim_time_s"]],
        "replay_reproduces_trial_states": first_divergent is None, "first_divergent": first_divergent,
        "worst_joint_q_error": worst_joint_error,
        "control_wall_s": {"median": float(np.median(walls)), "p90": float(np.quantile(walls, .9)),
                           "p99": float(np.quantile(walls, .99)), "max": float(walls.max()),
                           "over_0.15": int((walls > .15).sum()), "over_0.25": int((walls > .25).sum())},
        "pose_publish_gap_s": {"median": float(np.median(gaps)), "p99": float(np.quantile(gaps, .99)),
                               "max": float(gaps.max()), "over_0.2": int((gaps > .2).sum()),
                               "over_0.25": int((gaps > .25).sum())},
        "in_process_probe_lateness_ms": {"samples": len(late), "median": float(np.median(late)),
                                         "p99": float(np.quantile(late, .99)), "max": float(late.max()),
                                         "over_50": int((late > 50).sum()), "over_180": int((late > 180).sum())},
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
