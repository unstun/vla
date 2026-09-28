"""Record the pinned upstream Go2 policy, physics clock and real GL frames.

Local changes are limited to deterministic keyboard input, evidence collection,
and camera/video timing. The upstream model, policy and dynamics are unchanged.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
from types import SimpleNamespace

import numpy as np
from PIL import Image
import warp as wp

wp.config.kernel_cache_dir = os.environ["WARP_CACHE_PATH"]
wp.init()
wp.set_device("cpu")

import newton
from newton.examples.robot.example_robot_policy import Example


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=8.0)
    args = parser.parse_args()
    if not 0 < args.seconds <= 15:
        parser.error("duration must be positive and at most 15 simulation seconds")
    out = Path(os.environ["NEWTON_RUN_DIR"])
    frames = out / "frames"
    frames.mkdir()
    shutil.copyfile(__file__, out / "executed_record_go2.py")
    identity = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "device": "cpu", "robot": "official Go2", "seconds_requested": args.seconds,
        "newton_commit": "c2ca70bec5998062b0b2d35869865cbe3a49feee",
        "assets_commit": "f8fb7abcbeba2318814a74f3eeb02780ad7925d6",
        "wrapper_sha256": digest(__file__),
        "versions": {p: importlib.metadata.version(p) for p in
                     ("newton", "warp-lang", "mujoco", "mujoco-warp", "warp-nn", "numpy")},
        "command_schedule": "zero before 2s; original i key (forward 1m/s) from 2s to 6s; zero after 6s",
        "camera": {"position": [4, 2, 2.7], "target": [0, 2, .3]},
        "changes": ["scripted upstream keyboard input", "state/clock recording",
                    "fixed camera", "25fps framebuffer capture timed by actual physics"],
        "claim_boundary": "Flat-floor policy/physics only; not Lite3, stairs, navigation or RTX sensors.",
    }
    (out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    asset_identity = json.loads((out.parent / "go2_assets_v1/result.json").read_text())
    for name, expected in asset_identity["files"].items():
        if digest(Path(asset_identity["directory"]) / name) != expected["sha256"]:
            raise ValueError(f"Pinned Go2 asset mismatch: {name}")
    (out / "assets.json").write_text(json.dumps(asset_identity, indent=2) + "\n")
    viewer = newton.viewer.ViewerGL(width=1280, height=720, vsync=False, headless=True)
    rows = []
    frame_manifest = []
    try:
        example = Example(viewer, SimpleNamespace(robot="go2", physx=False))
        viewer.vsync = False
        viewer.set_camera(pos=(4, 2, 2.7), pitch=-31, yaw=-180)
        viewer.camera.look_at((0, 2, .3))
        initial_time = float(example.solver.mjw_data.time.numpy()[0])
        policy_dt = example.sim_dt * example.sim_substeps * example.decimation
        assert math.isclose(policy_dt, .02, abs_tol=1e-8)
        steps = round(args.seconds / policy_dt)
        assert math.isclose(steps * policy_dt, args.seconds, abs_tol=1e-8)
        initial_q = example.state_0.joint_q.numpy().copy()
        elapsed = 0.0
        viewer.is_key_down = lambda key: key == "i" and 2.0 - 1e-6 <= elapsed < 6.0 - 1e-6
        started = time.monotonic()
        with (out / "telemetry.jsonl").open("w") as log:
            for index in range(steps):
                previous_time = float(example.solver.mjw_data.time.numpy()[0])
                example.step()
                wp.synchronize()
                clock = float(example.solver.mjw_data.time.numpy()[0])
                elapsed = clock - initial_time
                q = example.state_0.joint_q.numpy()
                qd = example.state_0.joint_qd.numpy()
                obs = example._obs_wp.numpy()
                action = example._prev_act_wp.numpy()
                control = example.control.joint_target_q.numpy()
                applied_force = example.solver.mjw_data.qfrc_actuator.numpy()
                body = example.state_0.body_q.numpy()
                finite = all(np.isfinite(a).all() for a in (q, qd, obs, action, control, applied_force, body))
                if not finite or not math.isclose(clock - previous_time, policy_dt, abs_tol=2e-5):
                    raise ValueError(f"Non-finite state or incorrect physics clock at policy step {index}")
                assert obs.shape == (1, 48) and action.shape == (1, 12)
                quat = q[3:7] / np.linalg.norm(q[3:7])
                row = {
                    "policy_step": index + 1, "physics_time_s": clock,
                    "elapsed_physics_s": elapsed, "source_display_time_s": example.sim_time,
                    "wall_elapsed_s": time.monotonic() - started,
                    "command": list(example._command), "joint_q": q.tolist(), "joint_qd": qd.tolist(),
                    "observation": obs[0].tolist(), "action": action[0].tolist(),
                    "joint_target_q": control.tolist(), "applied_joint_force": applied_force.tolist(),
                    "base_up_z": float(1 - 2 * (quat[0] ** 2 + quat[1] ** 2)),
                    "minimum_body_center_z": float(body[:, 2].min()),
                    "contact_count": int(example.contacts.rigid_contact_count.numpy()[0]),
                    "finite": bool(finite),
                }
                log.write(json.dumps(row) + "\n")
                log.flush()
                rows.append(row)
                if (index + 1) % 2 == 0:
                    viewer.begin_frame(elapsed)
                    viewer.log_state(example.state_0)
                    viewer.end_frame()
                    rgb = viewer.get_frame(render_ui=False).numpy()
                    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
                        raise ValueError("Invalid framebuffer")
                    path = frames / f"{len(frame_manifest):06d}.png"
                    Image.fromarray(rgb).save(path)
                    frame_manifest.append({"file": str(path.relative_to(out)), "sha256": digest(path),
                                           "physics_time_s": clock, "elapsed_physics_s": elapsed,
                                           "policy_step": index + 1, "shape": list(rgb.shape)})
                if (index + 1) % 50 == 0:
                    print(f"physics={elapsed:.3f}s policy_steps={index + 1} base={q[:3].tolist()}", flush=True)
        loop_wall = time.monotonic() - started
        example.test_final()
        (out / "frames.json").write_text(json.dumps(frame_manifest, indent=2) + "\n")
        video = out / "go2_newton_macos_raw.mp4"
        command = ["/opt/homebrew/bin/ffmpeg", "-nostdin", "-v", "error", "-framerate", "25",
                   "-i", str(frames / "%06d.png"), "-c:v", "libx264", "-crf", "18",
                   "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)]
        encoded = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (out / "encode.json").write_text(json.dumps({"command": command, "returncode": encoded.returncode,
                                                    "stderr": encoded.stderr}, indent=2) + "\n")
        encoded.check_returncode()
        displacement = np.array(rows[-1]["joint_q"][:3]) - initial_q[:3]
        settled = [r for r in rows if r["elapsed_physics_s"] >= 1.0]
        force_nonzero = sum(int(np.max(np.abs(r["applied_joint_force"])) > 1e-6) for r in rows)
        upright = all(r["joint_q"][2] > .15 and r["base_up_z"] > .5 for r in settled)
        result = {
            "physics_and_policy_finite": True, "upstream_final_above_ground_test": "passed",
            "policy_steps": len(rows), "physics_substeps": len(rows) * example.decimation * example.sim_substeps,
            "physics_initial_time_s": initial_time, "physics_duration_s": elapsed,
            "source_display_duration_s": example.sim_time, "loop_wall_s": loop_wall,
            "loop_simulation_seconds_per_wall_second": elapsed / loop_wall,
            "video": str(video), "video_sha256": digest(video), "video_frames": len(frame_manifest),
            "video_fps": 25, "video_duration_s": len(frame_manifest) / 25,
            "base_displacement_xyz_m": displacement.tolist(), "applied_force_nonzero_steps": force_nonzero,
            "settled_min_base_z_m": min(r["joint_q"][2] for r in settled),
            "settled_min_base_up_z": min(r["base_up_z"] for r in settled),
            "upright_after_1s": upright,
            "acceptance": bool(upright and np.linalg.norm(displacement[:2]) > .2 and force_nonzero > 0),
            "clock_note": "Upstream display clock advances .005s per policy call; measured physics advances .02s. Video uses measured physics at 25fps.",
        }
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2), flush=True)
        if not result["acceptance"]:
            raise RuntimeError("Policy/physics qualification acceptance failed; inspect telemetry and frames")
    finally:
        viewer.close()


if __name__ == "__main__":
    main()
