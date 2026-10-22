"""Display-only second view of a recorded run: the unchanged render_episode.py with a heading-follow camera.

render_episode.py's full-building camera sits 2 m behind the robot along the *spawn* heading. In
corridors that turn away from that heading it ends up behind a wall (v30's last 18 s were wall only).
This wrapper runs the unchanged renderer (scripts/render_episode.py, imported, its main() called) and
replaces only the display camera from 1.6 s on, after the renderer's building overview: 1.4 m behind the
robot along its own yaw, smoothed with a 0.5 s time constant, 1.0 m above the base, looking 0.6 m ahead
and 0.1 m down. Recorded states, overlays, PCT route and native curves are drawn by the renderer as
usual; nothing is simulated. frames.json's camera fields still describe the renderer's own camera, so
every camera actually used is written to heading_camera.json.

Usage (through scripts/run_bounded.py): <newton venv python> render_heading_view.py --source-run <run id>
"""
import argparse
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

EXPERIMENT = Path('/home/ubuntu/sun/vla_v288_20261020/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction')
SCRIPTS = EXPERIMENT / "scripts"
OVERVIEW_S = 0.0
TRAIL_M, HEIGHT_M, AHEAD_M, DOWN_M, TAU_S = 0.35, 0.50, 0.0, 0.05, 0.2

parser = argparse.ArgumentParser()
parser.add_argument("--source-run", required=True)
args, remaining = parser.parse_known_args()
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_episode_v51 as render_episode
rows = render_episode.load_recorded_rows(Path('/home/ubuntu/sun/vla_v288_20261020/physical_runs/v288_CS03_attempt01/runs/v288_CS03_attempt01'))

# Newton free joint: joint_q = [x, y, z, qx, qy, qz, qw, ...].
cameras, smoothed, last_t = [], None, None
for row in rows:
    q = row["joint_q"]
    x, y, z, qx, qy, qz, qw = q[:7]
    yaw = math.atan2(2.0 * (qw * qz + qx * qy), 1.0 - 2.0 * (qy * qy + qz * qz))
    t = row["physics_time_s"]
    if smoothed is None:
        smoothed = yaw
    else:
        alpha = 1.0 - math.exp(-max(t - last_t, 0.0) / TAU_S)
        smoothed += alpha * math.atan2(math.sin(yaw - smoothed), math.cos(yaw - smoothed))
    last_t = t
    if t < OVERVIEW_S:
        cameras.append(None)
        continue
    base = np.array([x, y, z])
    heading = np.array([math.cos(smoothed), math.sin(smoothed), 0.0])
    position = base - TRAIL_M * heading + np.array([0.0, 0.0, HEIGHT_M])
    target = base + AHEAD_M * heading - np.array([0.0, 0.0, DOWN_M])
    cameras.append({"physics_time_s": t, "yaw_rad": yaw, "smoothed_yaw_rad": smoothed,
                    "position_m": position.tolist(), "target_m": target.tolist()})

sys.path.insert(0, str(SCRIPTS))
# Renderer is the version-owned 30 FPS wall-time causal replay imported above.
Base = render_episode.newton.viewer.ViewerGL


class HeadingViewer(Base):
    """ViewerGL whose per-frame camera is the precomputed heading-follow camera."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.frame_index = -1
        original_look_at = self.camera.look_at

        def look_at(target):
            camera = cameras[self.frame_index]
            original_look_at(target if camera is None else tuple(camera["target_m"]))

        self.camera.look_at = look_at

    def set_camera(self, position, pitch=-20, yaw=0):
        self.frame_index += 1
        camera = cameras[self.frame_index]
        super().set_camera(position if camera is None else tuple(camera["position_m"]), pitch=pitch, yaw=yaw)


render_episode.newton.viewer.ViewerGL = HeadingViewer
sys.argv = [str(Path(__file__).with_name("render_episode_v51.py")), "--source-run", args.source_run, *remaining]
render_episode.main()
out = Path(os.environ["NEWTON_RUN_DIR"])
cameras = cameras[:json.loads((out / "result.json").read_text())["frames"]]
(out / "executed_render_heading_v51.py").write_bytes(Path(__file__).read_bytes())
(out / "heading_camera.json").write_text(json.dumps({
    "wrapper": "render_heading_view.py", "renderer": "versions/v51/render_episode_v51.py (30 FPS wall-time causal replay)",
    "overview_until_s": OVERVIEW_S, "trail_m": TRAIL_M, "height_m": HEIGHT_M, "ahead_m": AHEAD_M, "down_m": DOWN_M,
    "yaw_time_constant_s": TAU_S, "frames": len(cameras), "cameras": cameras}, indent=1) + "\n")
print(json.dumps({"heading_view": str(out), "frames": len(cameras)}))
