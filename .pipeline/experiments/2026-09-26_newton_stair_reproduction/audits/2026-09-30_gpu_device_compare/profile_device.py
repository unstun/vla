"""Sequential same-scene device comparison; preserve controller safety checks."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os
import random
import sys
import time

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
ROOT = BASE.parents[2]
VERSION = BASE / "versions/v37"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=("parent_cpu", "v37_cpu", "v37_cuda", "v38_cuda_solver_graph", "v37_cuda_target_replay", "v38_cuda_solver_graph_target_replay", "v40_cpu_solver_graph"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert str(ROOT) == "/home/sun/vla_exec/vla", "Use the authorized execution copy"
    out = args.output.resolve()
    assert out.is_relative_to(HERE / "runs") and out.is_dir()
    os.environ["WARP_CACHE_PATH"] = str(HERE / "worker_cache")
    os.environ["CUDA_CACHE_PATH"] = str(HERE / "cuda_cache")
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"
    import numpy as np
    import warp as wp
    wp.config.kernel_cache_dir = str(HERE / "worker_cache")
    wp.init()
    device = "cuda:0" if args.case not in ("parent_cpu", "v37_cpu", "v40_cpu_solver_graph") else "cpu"
    version = BASE / "versions" / ("v40" if args.case.startswith("v40_") else "v38" if args.case.startswith("v38_") else "v37")
    wp.set_device(device)
    random.seed(0)
    np.random.seed(0)
    manifest = json.loads((version / "manifest.json").read_text())
    assert all(sha(ROOT / name) == digest for name, digest in manifest["source_files"].items()), "Source sync mismatch"
    sys.path[:0] = [str(version / "physics"), str(BASE / "scripts"),
                   str(BASE.parent / "2026-09-26_newton_macos_policy/scripts")]
    if args.case == "parent_cpu":
        from robot_scene import StairRobot
    elif args.case.startswith("v40_"):
        from robot_scene_v40 import StairRobot
    elif args.case.startswith("v38_"):
        from robot_scene_v38 import StairRobot
    else:
        from robot_scene_v37 import StairRobot
    from lite3_reference.robots.lite3 import POLICY_DT, SIM_DT
    started = time.monotonic()
    scenario = json.loads((BASE / "inputs/historical_full_building.json").read_text())
    options = dict(startup_mode="policy", stance_hold=False,
                   automatic_contact_capacity=True, scenario=scenario)
    if args.case != "parent_cpu":
        options["model_device"] = device
    if args.case.startswith(("v38_", "v40_")):
        options["use_solver_graph"] = True
    robot = StairRobot(**options)
    assert str(robot.model.device) == device
    assert not robot.solver.use_mujoco_cpu and robot.collision_pipeline is not None
    assert SIM_DT == .001 and POLICY_DT == .02
    source = {str(Path(inspect.getfile(cls))): sha(Path(inspect.getfile(cls))) for cls in
              (StairRobot, StairRobot.__bases__[0], robot.solver.__class__)}
    identity = {"case": args.case, "device": device, "manifest_sha256": sha(version / "manifest.json"),
        "module_sha256": source, "scenario_sha256": sha(BASE / "inputs/historical_full_building.json"),
        "building_vertices_sha256": hashlib.sha256(robot.building_vertices.tobytes()).hexdigest(),
        "building_faces_sha256": hashlib.sha256(robot.building_faces.tobytes()).hexdigest(),
        "contact_capacity": int(robot.contact_capacity), "collision_buffer": int(robot.contacts.rigid_contact_max),
        "body_count": robot.model.body_count, "shape_count": robot.model.shape_count,
        "runtime_versions": {name: importlib.metadata.version(name) for name in
                             ("newton", "warp-lang", "mujoco", "mujoco-warp", "onnxruntime")}}
    (out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    samples = {key: [] for key in ("policy_infer", "collision_method", "solver_method", "motor_substep", "body_pose", "array_numpy")}

    def observe(obj, name, key):
        original = getattr(obj, name)
        def timed(*arguments, **keywords):
            before = time.perf_counter()
            try:
                return original(*arguments, **keywords)
            finally:
                samples[key].append(time.perf_counter() - before)
        setattr(obj, name, timed)

    observe(robot, "infer", "policy_infer")
    observe(robot, "_motor_substep", "motor_substep")
    observe(robot.collision_pipeline, "collide", "collision_method")
    observe(robot.solver, "step", "solver_method")
    array_type = type(robot.state.joint_q)
    original_numpy = array_type.numpy
    def timed_numpy(array):
        before = time.perf_counter()
        try:
            return original_numpy(array)
        finally:
            samples["array_numpy"].append(time.perf_counter() - before)
    array_type.numpy = timed_numpy
    poses = []
    def body_observer(current):
        if current.steps % 5 == 0:
            before = time.perf_counter()
            pose = current.body_and_sensor()
            samples["body_pose"].append(time.perf_counter() - before)
            w, x, y, z = pose["quaternion"]
            poses.append({"step": current.steps, **pose, "up_z": 1. - 2. * (x*x + y*y)})
    robot.physics_observer = body_observer
    replay = args.case.endswith("_target_replay")
    replay_source = HERE / "runs/v37_cuda_attempt01/trace.json"
    source_trace = json.loads(replay_source.read_text()) if replay else None
    if replay:
        identity["target_replay_source_sha256"] = sha(replay_source)
        identity["control_mode"] = "Recorded 50 Hz targets; PD and physics continuous; no policy inference in measured phases"
        (out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    phases, trace = [], []
    error = None
    try:
        for _ in range(5):
            robot.step(np.zeros(3, np.float32))
        for label, command in (("zero", [0., 0., 0.]), ("forward", [.2, 0., 0.])):
            for values in samples.values():
                values.clear()
            poses.clear()
            wp.synchronize()
            sim_start = robot.physics_time()
            policy_start, motor_start = robot.policy_calls, robot.steps
            wall_start = time.perf_counter()
            target_rows = [row for row in source_trace if row["phase"] == label] if replay else None
            for index in range(100):
                if replay:
                    robot.target = np.asarray(target_rows[index]["target"], dtype=robot.target.dtype)
                    for _ in range(20):
                        robot._motor_substep()
                else:
                    robot.step(np.asarray(command, np.float32))
                assert robot.solver._step == robot.steps, "Capture advanced the host step counter"
                q, qd = robot.native_array("qpos"), robot.native_array("qvel")
                trace.append({"phase": label, "step": robot.steps, "physics_time_s": robot.physics_time(),
                    "command": command, "qpos": q.tolist(), "qvel": qd.tolist(),
                    "action": robot.last_action.tolist(), "target": robot.target.tolist(),
                    "torque": robot.torque.tolist(), "policy_input_sha256": hashlib.sha256(robot.policy_input.tobytes()).hexdigest()})
            wp.synchronize()
            elapsed = time.perf_counter() - wall_start
            sim_elapsed = robot.physics_time() - sim_start
            stats = {key: {"count": len(values), "total_wall_s": sum(values),
                          "median_s": float(np.median(values)), "p95_s": float(np.percentile(values, 95)), "max_s": max(values)}
                     for key, values in samples.items() if values}
            item = {"phase": label, "command": command, "actual_solver_elapsed_s": sim_elapsed,
                    "wall_elapsed_s": elapsed, "rtf": sim_elapsed / elapsed,
                    "policy_steps": robot.policy_calls - policy_start, "physics_steps": robot.steps - motor_start,
                    "actual_policy_wall_hz": (robot.policy_calls - policy_start) / elapsed,
                    "actual_physics_wall_hz": (robot.steps - motor_start) / elapsed,
                    "minimum_up_z": min(p["up_z"] for p in poses),
                    "maximum_applied_torque_error": robot.max_applied_torque_error, "method_wall_statistics": stats}
            phases.append(item)
            (out / (label + "_poses.json")).write_text(json.dumps(poses) + "\n")
            (out / (label + "_samples.json")).write_text(json.dumps(samples) + "\n")
            print(json.dumps(item), flush=True)
    except Exception as exception:
        error = repr(exception)
        raise
    finally:
        array_type.numpy = original_numpy
        (out / "trace.json").write_text(json.dumps(trace) + "\n")
        checks = {"complete_phases": len(phases) == 2,
                  "finite_recorded_states": bool(trace) and all(np.isfinite(row["qpos"] + row["qvel"] + row["action"]).all() for row in trace),
                  "upright": len(phases) == 2 and all(row["minimum_up_z"] >= .5 for row in phases),
                  "force_mapping": robot.max_applied_torque_error <= 1e-4,
                  "solver_counter_matches_physical_steps": robot.solver._step == robot.steps,
                  "graph_captured_and_launched": args.case != "v38_cuda_solver_graph" or (robot.solver_graph.graphs is not None and robot.solver_graph.launches == robot.steps - 1),
                  "fixed_step_counts": len(phases) == 2 and all(row["physics_steps"] == 2000 and row["policy_steps"] == (0 if replay else 100) for row in phases)}
        result = {**identity, "phases": phases, "checks": checks, "passed": error is None and all(checks.values()),
                  "error": error, "warmup_policy_steps": 5, "continuous_state": True,
                  "elapsed_including_initialization_s": time.monotonic() - started,
                  "target_replay": replay, "gpu_graph_capture": args.case.startswith("v38_"),
                  "graph_launches": getattr(getattr(robot, "solver_graph", None), "launches", 0), "paced": False, "navigation_run": False,
                  "sensing_transport_included": False,
                  "timing_boundary": "End-to-end phase wall time is synchronized. GPU method wall timings include submission latency, not isolated device kernel time. NumPy/readback timing overlaps other groups and must not be summed with them."}
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    if not result["passed"]:
        raise RuntimeError("Component checks did not pass")


if __name__ == "__main__":
    main()
