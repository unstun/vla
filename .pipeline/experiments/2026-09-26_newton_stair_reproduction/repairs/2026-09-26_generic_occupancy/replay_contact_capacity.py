"""Continuous same-command physics replay using Newton's capacity estimator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from materialize import BASE
sys.path.insert(0, str(BASE / "scripts"))
import numpy as np
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
from flat_scene import FlatSceneRobot, FlatStaticHuman


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", action="store_true")
    args = parser.parse_args()
    out = Path(os.environ["NEWTON_RUN_DIR"])
    source = BASE / "runs/flat_static_human_live_v3/telemetry.jsonl"
    reference = [json.loads(line) for line in source.open()]
    robot = FlatSceneRobot(FlatStaticHuman(out), automatic_contact_capacity=not args.legacy)
    samples = []
    maximum_start_delta = 0.
    with (out / "telemetry.jsonl").open("w") as log:
        for i, recorded in enumerate(reference):
            robot.step(recorded["command"])
            row = robot.telemetry()
            row["body_sensor"] = robot.body_and_sensor()
            row["command"] = recorded["command"]
            row["source_state_sequence"] = recorded["state_sequence"]
            log.write(json.dumps(row) + "\n")
            if i < 350:
                maximum_start_delta = max(maximum_start_delta, float(np.max(np.abs(
                    np.asarray(row["joint_q"]) - np.asarray(recorded["joint_q"])))))
            samples.append({"physics_time_s": row["physics_time_s"], "base_z": row["body_sensor"]["position"][2],
                            "base_up_z": row["base_up_z"], "contacts": row["contacts"]})
    result = {"source_commands_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "automatic_contact_capacity": not args.legacy,
              "solver_nconmax": robot.solver.mjw_data.naconmax,
              "solver_njmax": robot.solver.mjw_data.njmax,
              "collision_pipeline_capacity": robot.contacts.rigid_contact_max,
              "physics_steps": robot.steps, "physics_duration_s": samples[-1]["physics_time_s"],
              "prefix_max_joint_q_difference": maximum_start_delta,
              "minimum_base_z": min(r["base_z"] for r in samples),
              "minimum_base_up_z": min(r["base_up_z"] for r in samples),
              "maximum_contacts": max(r["contacts"] for r in samples),
              "last_sample": samples[-1],
              "claim": "Same recorded command sequence, one continuous policy/physics state, no resets. This isolates contact-capacity behavior; it is not closed-loop navigation."}
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
