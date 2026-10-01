"""Offline: full-collection cost in a worker-sized heap, with and without gc.freeze().

Builds the trial's robot and LiDAR (the worker's import and object baseline), then retains
telemetry-like rows the way newton_episode.py does (`rows.append(row)`, one dict per control step).
For each retained count it measures gc.collect(2):
- unfrozen: every tracked object is traversed;
- frozen once at start-up: gc.freeze() before the rows are added, so only the rows are traversed;
- frozen periodically: gc.freeze() every 50 rows (1 s of simulation), so at most 50 rows are traversed.
"""
import gc
import json
import os
from pathlib import Path
import sys
import time

import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")

H = Path(__file__).resolve().parent
E = H.parents[1]
sys.path.insert(0, str(E / "scripts"))
from robot_scene import StairRobot  # noqa: E402
from geometric_lidar import GeometricLidar  # noqa: E402


def collect_ms(repeats=3):
    values = []
    for _ in range(repeats):
        started = time.perf_counter_ns()
        gc.collect(2)
        values.append(round((time.perf_counter_ns() - started) / 1e6, 2))
    return values


def main():
    scenario = json.loads((E / "runs/v31_historical_full01/inputs/stair_scenario.json").read_text())
    robot = StairRobot(startup_mode="factory_pd", stance_hold=True, automatic_contact_capacity=True, scenario=scenario)
    lidar = GeometricLidar(robot, None, emitter_self_exclusion=True, visible_human_only=True)
    lidar.scan(0, 0.0, override_pose=robot.body_and_sensor(), captured_state=robot.state)
    template = next(open(E / "runs/v31_historical_full01/telemetry.jsonl"))
    result = {}
    for count in (0, 1000, 28000):
        entry = {}
        gc.unfreeze()
        rows = [json.loads(template) for _ in range(count)]
        entry["unfrozen"] = {"tracked": len(gc.get_objects()), "full_collection_ms": collect_ms()}
        del rows
        gc.collect()
        gc.freeze()
        rows = [json.loads(template) for _ in range(count)]
        entry["frozen_at_startup"] = {"frozen": gc.get_freeze_count(), "tracked": len(gc.get_objects()),
                                      "full_collection_ms": collect_ms()}
        del rows
        gc.unfreeze()
        gc.collect()
        gc.freeze()
        rows = []
        for index in range(count):
            rows.append(json.loads(template))
            if index % 50 == 49:
                gc.freeze()
        entry["frozen_every_50_rows"] = {"frozen": gc.get_freeze_count(), "tracked": len(gc.get_objects()),
                                         "full_collection_ms": collect_ms()}
        del rows
        gc.unfreeze()
        gc.collect()
        result[str(count)] = entry
    (H / "probe_gc_freeze.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
