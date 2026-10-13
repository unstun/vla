"""Replay original physics frames with a fixed camera during each zero command."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
sys.path[:0] = [str(BASE / "versions/v182"), str(BASE / "versions/v51")]
import run_probe
import numpy as np
import warp as wp
import newton
from PIL import Image, ImageDraw, ImageFont
from render_episode_v51 import prepare_robot_appearance
from video_stream import VideoStream
from protocol import CONDITIONS
from timeline import frame_indices


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--archive-receipt", type=Path, required=True)
    args = p.parse_args()
    from freeze_display import verify
    verify()
    run_probe.verify()
    receipt = json.loads(args.archive_receipt.read_text())
    if not receipt.get("remote_verified") or receipt["run"] != args.run.name:
        raise ValueError("Missing returned remote raw verification")
    for name, value in receipt["files"].items():
        if digest(args.run / name) != value["sha256"]:
            raise ValueError("Recorded source differs from archived bytes")
    request = json.loads((args.run / "probe_request.json").read_text())
    result = json.loads((args.run / "result.json").read_text())
    rows = json.loads((args.run / "recorded_frames.json").read_text())
    telemetry = [json.loads(x) for x in (args.run / "telemetry.jsonl").read_text().splitlines()] if (args.run / "telemetry.jsonl").exists() else []
    times = np.array([r["physics_time_s"] for r in rows])
    measured_times = np.array([r["physics_time_s"] for r in telemetry])
    phase_first = {}
    for measured_row in telemetry:
        phase_first.setdefault(measured_row["phase"], measured_row)
    grid, indices = frame_indices(times)
    args.output.mkdir(parents=True, exist_ok=False)
    robot = run_probe.build_robot(request["terrain"])
    appearance = prepare_robot_appearance(robot)
    (args.output / "appearance.json").write_text(json.dumps(appearance, indent=2) + "\n")
    (args.output / "display_source.json").write_text(json.dumps(dict(run=str(args.run),
        physics_version="v182", display_version="v183", archive_receipt_sha256=digest(args.archive_receipt),
        source_frames_sha256=digest(args.run / "recorded_frames.json"), outcome=result["outcome"],
        physics_advanced=False, nominal_speed_mps=CONDITIONS[request["attempt"] - 1][0]), indent=2) + "\n")
    fonts = "/System/Library/Fonts/STHeiti Medium.ttc"
    font = ImageFont.truetype(fonts, 29)
    small = ImageFont.truetype(fonts, 23)
    viewer = newton.viewer.ViewerGL(width=640, height=360, vsync=False, headless=True)
    stream = VideoStream(args.output, 30, len(grid), max_bytes=50 * 1024**2)
    ok = False
    current_phase, fixed_center, stop_anchor, stop_start = None, None, None, None
    heading = 0. if request["terrain"] == "flat" else -math.pi / 2
    forward = np.array([math.cos(heading), math.sin(heading), 0.])
    right = np.array([math.sin(heading), -math.cos(heading), 0.])
    labels = dict(startup="初始化站立", walk1="走", stop1="停：模型独立控制", walk2="再走", stop2="再停：模型独立控制")
    try:
        viewer.set_model(robot.model)
        viewer.camera.fov = 55.
        viewer.renderer.sky_upper = viewer.renderer.sky_lower = (.9, .9, .9)
        viewer.renderer.ambient_sky = (.8, .8, .8)
        viewer.renderer.ambient_ground = (.3, .3, .3)
        viewer.renderer.spotlight_enabled = False
        for number, (display_time, index) in enumerate(zip(grid, indices)):
            row = rows[int(index)]
            body = np.asarray(row["body_q"], np.float32)
            q = np.asarray(row["joint_q"])
            robot.state.body_q.assign(body)
            phase = row["phase"]
            mindex = int(np.searchsorted(measured_times, row["physics_time_s"], side="right") - 1)
            measured = telemetry[mindex] if mindex >= 0 else None
            if phase != current_phase:
                current_phase = phase
                fixed_center = q[:3].copy()
                if phase.startswith("stop"):
                    stop_anchor = np.array(phase_first[phase]["command_start_base_xyz"])
                    stop_start = phase_first[phase]["command_applied_start_s"]
            center = fixed_center if phase.startswith("stop") else q[:3]
            # Recorded-state only: a stop camera never follows drift.
            position = center - 1.15 * forward - 1.15 * right + np.array([0., 0., .9])
            target = center + .2 * forward
            viewer.set_camera(tuple(position), pitch=-20., yaw=0.)
            viewer.camera.look_at(tuple(target))
            viewer.begin_frame(float(display_time))
            viewer.log_state(robot.state)
            if phase.startswith("stop"):
                radius = .08
                angles = np.linspace(0, 2 * math.pi, 49)
                ring = stop_anchor + np.c_[radius * np.cos(angles), radius * np.sin(angles), np.zeros(len(angles))]
                viewer.log_lines("stop_position", wp.array(ring[:-1].astype(np.float32), dtype=wp.vec3),
                                 wp.array(ring[1:].astype(np.float32), dtype=wp.vec3), colors=(1., .15, .1))
            else:
                viewer.log_lines("stop_position", None, None, None)
            viewer.end_frame()
            image = Image.fromarray(viewer.get_frame(render_ui=False).numpy()).resize((1280, 720), Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, 1280, 96), fill=(15, 20, 29))
            draw.rectangle((0, 618, 1280, 720), fill=(15, 20, 29))
            terrain = "平地" if request["terrain"] == "flat" else "原场景楼梯"
            title = f"{terrain}  第 {request['attempt']}/6 次  |  {labels[phase]}  |  {display_time:.1f} 秒"
            draw.text((24, 12), title, font=font, fill=(245, 247, 250))
            command = row["command"][0]
            speed = float(np.linalg.norm(measured["joint_qd"][:2])) if measured else None
            detail = f"前进指令 {command:.2f} m/s"
            if speed is not None:
                detail += f"   实际水平速度 {speed:.3f} m/s"
            draw.text((24, 55), detail, font=small, fill=(177, 219, 236))
            if phase.startswith("stop"):
                drift = float(np.linalg.norm(q[:2] - stop_anchor[:2]))
                footer = f"停车已 {row['physics_time_s'] - stop_start:.1f} 秒   离停车指令位置 {drift * 100:.1f} 厘米"
                note = "红圈是停车指令时的位置；停车期间镜头固定。包括减速距离。"
            else:
                footer = "最低巡航要求 0.6 m/s；当前原模型；未接导航"
                note = "原始物理记录，按仿真时间 1 倍速播放；保留完整走、停、再走过程。"
            draw.text((24, 633), footer, font=font, fill=(255, 220, 157))
            draw.text((24, 678), note, font=small, fill=(202, 211, 221))
            metadata = dict(run=args.run.name, source_index=int(index), recorded_time_s=float(times[index]),
                            display_time_s=float(display_time), phase=phase,
                            recorded_state_sha256=hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest())
            stream.add(image, metadata)
            if phase.startswith("stop") and abs(row["physics_time_s"] - stop_start - 5.) < .04:
                sample = args.output / f"{phase}_five_seconds.png"
                if not sample.exists():
                    image.save(sample)
        ok = True
    finally:
        stream.close(success=ok)
        viewer.close()


if __name__ == "__main__":
    main()
