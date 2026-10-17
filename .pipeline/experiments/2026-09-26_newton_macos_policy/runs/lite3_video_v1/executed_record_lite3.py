"""One continuous 12-second Lite3 trial with real Newton-rendered video."""
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
from PIL import Image
import warp as wp

wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")
import mujoco
import newton
from lite3_newton import BASE, Lite3Newton


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    out = Path(os.environ["NEWTON_RUN_DIR"])
    frames = out / "frames"
    frames.mkdir()
    for name in ("record_lite3.py", "lite3_newton.py"):
        shutil.copyfile(Path(__file__).with_name(name), out / ("executed_" + name))
    robot = Lite3Newton()
    identity = {
        "robot": "Lite3", "policy": "model_149999 V12 FP32 ONNX",
        "inputs": robot.input_identity, "newton_commit": "c2ca70bec5998062b0b2d35869865cbe3a49feee",
        "versions": {p: importlib.metadata.version(p) for p in
                     ("newton", "warp-lang", "mujoco", "numpy", "onnxruntime", "pillow")},
        "solver": "Newton SolverMuJoCo(use_mujoco_cpu=True)", "device": "cpu",
        "update_data_interval": 0,
        "policy_dt_s": .02, "physics_dt_s": .001, "policy_provider": robot.session.get_providers(),
        "command_schedule": [[0, 2, 0, 0, 0], [2, 6, .5, 0, 0], [6, 9, .35, 0, .4], [9, 12, 0, 0, 0]],
        "joint_labels": robot.model.joint_label, "joint_indices": robot.joints,
        "joint_q_indices": robot.q_indices.tolist(), "joint_qd_indices": robot.qd_indices.tolist(),
        "native_joint_indices": robot.mj_joints.tolist(), "actuator_indices": robot.actuators.tolist(),
        "camera": {"position": [2.5, -3, 2.2], "target": [1.2, 0, .3]},
        "claim_boundary": "Scripted flat-ground velocity control, no navigation, stairs, person or RTX sensor.",
    }
    (out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    mujoco.mj_saveLastXML(str(out / "newton_solver_model.xml"), robot.solver.mj_model)
    viewer = newton.viewer.ViewerGL(width=1280, height=720, vsync=False, headless=True)
    rows, manifest = [], []
    try:
        viewer.set_model(robot.model)
        viewer.set_camera(pos=(2.5, -3, 2.2), pitch=-30, yaw=110)
        viewer.camera.look_at((1.2, 0, .3))
        initial = robot.state.joint_q.numpy()[:3].copy()
        started = time.monotonic()
        with (out / "telemetry.jsonl").open("w") as f:
            for step in range(600):
                # Policy step numbers avoid ambiguous floating-point boundary comparisons.
                command = (0., 0., 0.) if step < 100 or step >= 450 else (
                    (.5, 0., 0.) if step < 300 else (.35, 0., .4))
                previous_clock = float(robot.solver.mj_data.time)
                robot.step(command)
                row = robot.telemetry()
                if not math.isclose(row["physics_time_s"] - previous_clock, .02, abs_tol=1e-6):
                    raise ValueError("Actual physics clock did not advance by the declared policy period")
                row.update(policy_step=step + 1, command=list(command), wall_s=time.monotonic() - started)
                f.write(json.dumps(row) + "\n")
                f.flush()
                rows.append(row)
                if (step + 1) % 2 == 0:
                    viewer.begin_frame(row["physics_time_s"])
                    viewer.log_state(robot.state)
                    viewer.end_frame()
                    rgb = viewer.get_frame(render_ui=False).numpy()
                    path = frames / f"{len(manifest):06d}.png"
                    Image.fromarray(rgb).save(path)
                    manifest.append({"file": str(path.relative_to(out)), "sha256": digest(path),
                                     "physics_time_s": row["physics_time_s"], "policy_step": step + 1,
                                     "shape": list(rgb.shape)})
                if (step + 1) % 50 == 0:
                    print("physics", row["physics_time_s"], "base", row["joint_q"][:3],
                          "up", row["base_up_z"], flush=True)
        loop_wall = time.monotonic() - started
        (out / "frames.json").write_text(json.dumps(manifest, indent=2) + "\n")
        video = out / "lite3_newton_macos_raw.mp4"
        command = ["/opt/homebrew/bin/ffmpeg", "-nostdin", "-v", "error", "-framerate", "25",
                   "-i", str(frames / "%06d.png"), "-c:v", "libx264", "-crf", "18",
                   "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)]
        encoded = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (out / "encode.json").write_text(json.dumps({"command": command, "returncode": encoded.returncode,
                                                    "stderr": encoded.stderr}, indent=2) + "\n")
        encoded.check_returncode()
        settled = [r for r in rows if r["physics_time_s"] >= 1.0]
        upright = all(r["joint_q"][2] > .20 and r["base_up_z"] > math.cos(math.pi / 6) for r in settled)
        displacement = np.array(rows[-1]["joint_q"][:3]) - initial
        forces = sum(int(np.max(np.abs(r["applied_torque"])) > 1e-6) for r in rows)
        result = {"acceptance": bool(upright and np.linalg.norm(displacement[:2]) > .2 and forces > 0),
                  "physics_duration_s": rows[-1]["physics_time_s"], "physics_steps": robot.steps,
                  "policy_steps": len(rows), "all_logged_values_finite": True,
                  "base_displacement_xyz_m": displacement.tolist(), "upright_after_1s": upright,
                  "settled_min_base_z_m": min(r["joint_q"][2] for r in settled),
                  "settled_max_tilt_deg": math.degrees(math.acos(min(r["base_up_z"] for r in settled))),
                  "last_second_mean_planar_speed_m_s": float(np.mean([
                      np.linalg.norm(r["joint_qd"][:2]) for r in rows if r["physics_time_s"] >= 11])),
                  "observation_mapping_max_abs": robot.max_observation_mapping_error,
                  "applied_torque_max_abs": robot.max_applied_torque_error,
                  "applied_force_nonzero_policy_steps": forces,
                  "loop_wall_s": loop_wall, "loop_simulation_seconds_per_wall_second": 12 / loop_wall,
                  "video": str(video), "video_sha256": digest(video), "video_frames": len(manifest),
                  "video_fps": 25, "video_duration_s": len(manifest) / 25,
                  "claim": "Local Lite3 flat-ground policy/physics integration only"}
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)
        if not result["acceptance"]:
            raise RuntimeError("Lite3 trial failed acceptance; preserve and inspect telemetry/video")
    finally:
        viewer.close()


if __name__ == "__main__":
    main()
