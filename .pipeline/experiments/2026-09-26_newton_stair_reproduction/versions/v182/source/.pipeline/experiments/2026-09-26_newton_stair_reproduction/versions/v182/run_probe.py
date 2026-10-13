"""Current frozen locomotion on fixed commands; no navigation imports/services."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
PROJECT = BASE.parents[2]
QUALIFIED = BASE.parent / "2026-09-26_newton_macos_policy"
sys.path[:0] = [str(HERE), str(BASE / "versions/v40/physics"), str(BASE / "scripts"),
                str(QUALIFIED / "scripts"), str(BASE / "runtime_sources/bridge")]

import numpy as np
import warp as wp
wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
import newton
import psutil
from scipy.spatial.transform import Rotation
from robot_scene_v40 import StairRobot, Lite3Newton
from protocol import STAIR_SCENARIO, schedule
from freeze import verify


def build_robot(terrain):
    if terrain == "stairs":
        return StairRobot(startup_mode="factory_pd", stance_hold=True,
                          scenario=STAIR_SCENARIO, automatic_contact_capacity=True,
                          model_device="cpu", use_solver_graph=True)
    if terrain != "flat":
        raise ValueError("Unknown terrain")
    def floor(builder):
        vertices = np.array([[-8., -8., 0.], [8., -8., 0.], [8., 8., 0.], [-8., 8., 0.]], np.float32)
        mesh = newton.Mesh(vertices, np.array([0, 1, 2, 0, 2, 3], np.int32), compute_inertia=False)
        builder.add_shape_mesh(-1, mesh=mesh, cfg=newton.ModelBuilder.ShapeConfig(mu=1.0),
                               label="flat_probe_floor", color=(0.58, 0.62, 0.67))
    return Lite3Newton(robot_source=BASE / "inputs/sensor_rig/lite3_pro_sensor_rig_real_with_interface.urdf",
                        scene_builder=floor, spawn_xyz=(0., 0., 0.14), newton_contacts=True,
                        automatic_contact_capacity=True, startup_mode="factory_pd", stance_hold=True,
                        model_device="cpu", use_solver_graph=True)


def foot_shapes(robot):
    bodies = robot.model.shape_body.numpy()
    kinds = robot.model.shape_type.numpy()
    scales = robot.model.shape_scale.numpy()
    flags = robot.model.shape_flags.numpy()
    result = []
    for leg in ("FL", "FR", "HL", "HR"):
        found = [i for i in range(robot.model.shape_count) if bodies[i] >= 0
                 and robot.model.body_label[bodies[i]].rsplit("/", 1)[-1] == leg + "_SHANK"
                 and kinds[i] == int(newton.GeoType.SPHERE) and np.isclose(scales[i, 0], .022)
                 and flags[i] & int(newton.ShapeFlags.COLLIDE_SHAPES)]
        if len(found) != 1:
            raise ValueError(f"Ambiguous foot sphere {leg}: {found}")
        result.append(found[0])
    return result


def foot_positions(robot, shapes):
    body = robot.state.body_q.numpy()
    ids = robot.model.shape_body.numpy()[shapes]
    local = robot.model.shape_transform.numpy()[shapes, :3]
    return body[ids, :3] + Rotation.from_quat(body[ids, 3:7]).apply(local)


def frame(robot, phase, command):
    return dict(physics_time_s=robot.physics_time(), physics_steps=robot.steps,
                body_q=robot.state.body_q.numpy().tolist(), joint_q=robot.state.joint_q.numpy().tolist(),
                command=command, phase=phase)


def resources(out, admission=False):
    available = psutil.virtual_memory().available
    free = shutil.disk_usage(out).free
    rss = psutil.Process().memory_info().rss
    if free < 10 * 1024**3 or rss > 12 * 1024**3 or (admission and available < 8 * 1024**3):
        raise RuntimeError(f"Local resource gate held: available={available}, free={free}, rss={rss}")
    return dict(available_bytes=available, disk_free_bytes=free, rss_bytes=rss)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--terrain", choices=("flat", "stairs"), required=True)
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    verify()
    out = Path(os.environ["NEWTON_RUN_DIR"])
    if not out.is_dir() or (out / "probe_request.json").exists():
        raise ValueError("Expected fresh supervised run directory")
    admission = resources(out, admission=True)
    steps = list(schedule(args.attempt))
    request = dict(version=HERE.name, terrain=args.terrain, attempt=args.attempt, host=os.uname().nodename,
                   navigation=False, automatic_hold_during_stops=False, phases=list(dict.fromkeys(x["phase"] for x in steps)),
                   source_manifest_sha256=hashlib.sha256((HERE / "manifest.json").read_bytes()).hexdigest(),
                   conditions="factory startup then original smooth REJOIN; policy-only thereafter",
                   admission=admission,
                   physical_backend="Newton1.6 / Warp1.17 CPU graph; original triangle contacts")
    (out / "probe_request.json").write_text(json.dumps(request, indent=2) + "\n")
    rows, frames = [], []
    result = dict(execution_completed=False, outcome="not_started", navigation_connected=False)
    started = time.monotonic()
    try:
        robot = build_robot(args.terrain)
        resources(out)
        shapes = foot_shapes(robot)
        observer = robot.stance
        frames.append(frame(robot, "startup", [0., 0., 0.]))
        from factory_navigation_startup import initialize
        startup = initialize(robot, out)
        frames.extend(dict(x, phase="startup") for x in startup)
        release = None
        with (out / "telemetry.jsonl").open("w") as stream:
            for item in steps:
                before = robot.physics_time()
                anchor = robot.state.joint_q.numpy()[:3].tolist()
                robot.step(item["command"])
                if robot.stance is not None and robot.stance.row["stance_mode"] == "RL":
                    if not np.any(item["command"]):
                        raise RuntimeError("Release must occur during initial nonzero command")
                    release = dict(physics_time_s=robot.physics_time(), phase=item["phase"],
                                   q=robot.state.joint_q.numpy().tolist(), kp=np.asarray(robot.motor_kp).tolist(),
                                   kd=np.asarray(robot.motor_kd).tolist())
                    robot.stance = None  # Observer retained; no further hold.update calls.
                row = robot.telemetry()
                row.update(item, command_applied_start_s=before, command_start_base_xyz=anchor,
                           foot_positions_world=foot_positions(robot, shapes).tolist(),
                           foot_forces_n=observer.measure().tolist(),
                           stance_mode="POLICY_ONLY" if robot.stance is None else robot.stance.row["stance_mode"],
                           policy_owns_joints=robot.stance is None)
                if robot.stance is None:
                    if not (np.all(np.asarray(robot.motor_kp) == 20.) and np.all(np.asarray(robot.motor_kd) == .5)):
                        raise RuntimeError("Policy-only gain mismatch")
                    if not np.allclose(robot.target, robot.policy_target, rtol=0, atol=1e-7):
                        raise RuntimeError("Nonpolicy action during policy-only phase")
                if item["phase"].startswith("stop") and robot.stance is not None:
                    raise RuntimeError("Stop was contaminated by automatic stance control")
                if not np.array_equal(np.asarray(row["effective_command"], np.float32), np.asarray(item["command"], np.float32)):
                    raise RuntimeError("Actual command differs from schedule")
                stream.write(json.dumps(row) + "\n")
                rows.append(row)
                frames.append(frame(robot, item["phase"], item["command"]))
                if item["index"] % 100 == 0:
                    resources(out)
                    stream.flush()
                    print(json.dumps(dict(t=row["physics_time_s"], phase=item["phase"], xy=row["joint_q"][:2])), flush=True)
                if row["base_up_z"] < .5:
                    result.update(outcome="fall", fall_at_s=row["physics_time_s"])
                    break
            else:
                result.update(execution_completed=True, outcome="schedule_completed")
        result.update(policy_release=release, physics_s=robot.physics_time(), physics_steps=robot.steps,
                      observation_mapping_max_abs=robot.max_observation_mapping_error,
                      applied_torque_max_abs=robot.max_applied_torque_error, samples=len(rows))
    except BaseException as error:
        result.update(outcome="execution_error", error=repr(error))
        raise
    finally:
        if len(frames) == 1 and (out / "factory_video_states.json").exists():
            frames.extend(dict(x, phase="startup") for x in json.loads((out / "factory_video_states.json").read_text()))
        if frames:
            (out / "recorded_frames.json").write_text(json.dumps(frames) + "\n")
        result["wall_s"] = time.monotonic() - started
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
