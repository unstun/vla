"""Bounded no-render probe before recording the Lite3 Newton port."""
import json
import os
from pathlib import Path
import shutil
import warp as wp

wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
from lite3_newton import Lite3Newton, check_golden_policy

out = Path(os.environ["NEWTON_RUN_DIR"])
for name in ("probe_lite3.py", "lite3_newton.py"):
    shutil.copyfile(Path(__file__).with_name(name), out / ("executed_" + name))
golden = check_golden_policy()
(out / "golden_policy.json").write_text(json.dumps(golden, indent=2) + "\n")
print("golden policy", golden, flush=True)
robot = Lite3Newton()
print("joint labels", robot.model.joint_label, flush=True)
with (out / "telemetry.jsonl").open("w") as f:
    for step in range(100):
        robot.step((0., 0., 0.))
        row = robot.telemetry()
        f.write(json.dumps(row) + "\n")
        f.flush()
        if step % 25 == 0:
            print("physics", row["physics_time_s"], "base", row["joint_q"][:3], flush=True)
result = {"golden_policy": golden, "physics_duration_s": row["physics_time_s"],
          "final_base": row["joint_q"][:3], "final_base_up_z": row["base_up_z"],
          "observation_mapping_max_abs": robot.max_observation_mapping_error,
          "applied_torque_max_abs": robot.max_applied_torque_error,
          "solver": "Newton SolverMuJoCo(use_mujoco_cpu=True)",
          "claim": "Two-second zero-command policy/physics probe only"}
(out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2), flush=True)
