"""gpu5070ti: build the worker's scene as the replay and the launcher do, then compile every Warp module on the CPU,
so the first physics run does not pay the kernel compile inside the factory startup's wall limit."""
import json, os, sys, time
from pathlib import Path
E = Path.home() / "vla_exec/vla/.pipeline/experiments/2026-09-26_newton_stair_reproduction"
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
sys.path.insert(0, str(E / "scripts"))
from robot_scene import StairRobot  # noqa: E402
from geometric_lidar import GeometricLidar  # noqa: E402
import onnxruntime, newton, mujoco, mujoco_warp  # noqa: E402,F401
scenario = json.loads((E / "runs/v31_historical_full01/inputs/stair_scenario.json").read_text())
t = time.monotonic()
robot = StairRobot(startup_mode="factory_pd", stance_hold=True, automatic_contact_capacity=True, scenario=scenario)
lidar = GeometricLidar(robot, None, emitter_self_exclusion=True, visible_human_only=True)
built = time.monotonic() - t
t = time.monotonic()
wp.force_load(device="cpu", block_dim=1)
print(json.dumps({"warp": wp.__version__, "newton": newton.__version__, "onnxruntime": onnxruntime.__version__,
                  "scene_build_s": round(built, 1), "force_load_s": round(time.monotonic() - t, 1),
                  "cache": os.environ["WARP_CACHE_PATH"]}))
