#!/usr/bin/env python3
"""Explainer video of the stance-hold entry (task 09-17-isaac-runner-stance-hold).

Three recorded 60 s stand_probe runs on gpu5070ti are shown side by side, slowed down 4x around the moment the hold
switches on: hold off, hold on with an immediate gain jump (C1), and hold on with a 0.5 s gain ramp (C1b). Each
column shows the runner's own camera (zoomed crop, 12.5 fps) and two drawings made from metrics.jsonl (50 Hz). The
drawings exaggerate the motion so that millimetres and degrees become visible: twist x15 (top view) and height
x20 (side view). A bar under each foot shows its measured ground force. Everything drawn comes from the recorded
files; nothing is simulated here.

    make_entry_demo.py --frames-dir DIR --output OUT.mp4
DIR holds <key>/fNNN.png camera crops (frame index NNN of third_person_master.mp4), made with ffmpeg beforehand.
"""
import argparse
import json
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

HERE = Path(__file__).resolve().parent
RUNS = HERE.parent / "isaac_runner/runs"
COLUMNS = [
    ("off", "stand_20260917T125239Z_hold_off", "Hold OFF", "V12 policy keeps running on a zero command", "#6b6b6b"),
    ("step", "stand_20260917T125239Z_hold_auto", "Hold ON, version 1", "stiffness jumps 20 -> 60 in one step", "#C75200"),
    ("ramp", None, "Hold ON, version 2", "stiffness ramps 20 -> 60 over 0.5 s", "#0072B2"),
]
ENTRY_S = 0.40
T_START, T_END = 0.20, 2.00
TWIST_GAIN = 10.0
HEIGHT_GAIN = 20.0
YAW_LIMIT = 0.15
FOOT_LOW_N = 5.0
LEG_ORDER = ["FL", "FR", "HL", "HR"]


def yaw_of(quat):
    w, x, y, z = quat
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def load(run_id):
    base = RUNS / run_id / "returned_artifacts/runner_output"
    rows = [json.loads(line) for line in (base / "metrics.jsonl").read_text().splitlines() if line.strip()]
    frames = [json.loads(line) for line in (base / "camera_frames.jsonl").read_text().splitlines() if line.strip()]
    return rows, frames


def caption(t):
    if t < ENTRY_S - 1e-6:
        return "Before 0.40 s: all three runs are identical. V12 is still settling after the robot was placed."
    if t < ENTRY_S + 0.13:
        return ("0.40 s: the hold switches on in both 'Hold ON' runs. Version 1 hops at once: the front feet lose "
                "almost all load.")
    if t < 1.30:
        return ("Version 2 does not hop (feet stay loaded), but the soft legs let the body twist left and right. "
                "Version 1 also twisted, but settled sooner.")
    return "By about 1.3 s both hold versions stand still; Hold OFF keeps making small corrections (see the trace)."


def draw_top(ax, yaw_rel, yaw_rate, color):
    alarm = abs(yaw_rate) > YAW_LIMIT
    ax.set_xlim(-0.55, 0.55); ax.set_ylim(-0.42, 0.42); ax.set_aspect("equal"); ax.axis("off")
    angle = TWIST_GAIN * yaw_rel
    ca, sa = math.cos(angle), math.sin(angle)
    body = [(-0.33, -0.12), (0.33, -0.12), (0.33, 0.12), (-0.33, 0.12)]
    ax.add_patch(Polygon(body, closed=True, fill=False, ls=":", ec="#aaaaaa", lw=1))
    pts = [(x * ca - y * sa, x * sa + y * ca) for x, y in body]
    ax.add_patch(Polygon(pts, closed=True, fc=("#f3c2bd" if alarm else "#e6eef3"), ec=("#b3261e" if alarm else color),
                         lw=2))
    ax.annotate("", xy=(0.42 * ca, 0.42 * sa), xytext=(0, 0), arrowprops=dict(arrowstyle="->", color=color, lw=1.8))
    ax.text(-0.55, 0.42, "TOP VIEW (twist x%d)" % TWIST_GAIN, fontsize=7.5, color="#444", va="top")
    ax.text(-0.55, -0.42, "turning %+.2f rad/s" % yaw_rate, fontsize=9, va="bottom",
            color=("#b3261e" if alarm else "#222"), weight=("bold" if alarm else "normal"))


def draw_side(ax, dz, vz, color):
    alarm = abs(vz) > 0.05
    ax.set_xlim(-0.55, 0.55); ax.set_ylim(-0.08, 0.5); ax.axis("off")
    ax.plot([-0.5, 0.5], [0, 0], color="#555", lw=1.5)
    y_body = 0.22 + HEIGHT_GAIN * dz
    ax.plot([-0.33, 0.33], [0.22, 0.22], ls=":", color="#aaaaaa", lw=1)
    for x in (-0.28, 0.28):
        ax.plot([x, x], [y_body, 0], color="#999", lw=1.5)
    ax.add_patch(Rectangle((-0.33, y_body), 0.66, 0.08, fc=("#f3c2bd" if alarm else "#e6eef3"),
                           ec=("#b3261e" if alarm else color), lw=2))
    ax.text(-0.55, 0.5, "SIDE VIEW (height x%d)" % HEIGHT_GAIN, fontsize=7.5, color="#444", va="top")
    ax.text(-0.55, -0.08, "up/down %+.2f m/s" % vz, fontsize=9, va="bottom",
            color=("#b3261e" if alarm else "#222"), weight=("bold" if alarm else "normal"))


def draw_feet(ax, forces, color):
    ax.set_xlim(-0.6, 3.6); ax.set_ylim(0, 62)
    for i, (leg, force) in enumerate(zip(LEG_ORDER, forces)):
        low = force < FOOT_LOW_N
        ax.bar(i, min(force, 60.0), width=0.6, color=("#b3261e" if low else color))
        ax.text(i, min(force, 60.0) + 1.5, "%.0f" % force, ha="center", fontsize=7, color=("#b3261e" if low else "#333"))
    ax.set_xticks(range(4)); ax.set_xticklabels(LEG_ORDER, fontsize=7.5)
    ax.set_yticks([]); ax.spines[["top", "right", "left"]].set_visible(False)
    ax.set_title("foot load (N), red < %d" % FOOT_LOW_N, fontsize=7.5, color="#444", loc="left", pad=2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames-dir", type=Path, required=True)
    parser.add_argument("--ramp-run", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    columns = [(k, r or args.ramp_run, title, sub, color) for k, r, title, sub, color in COLUMNS]
    data = {}
    for key, run_id, *_ in columns:
        rows, frames = load(run_id)
        ref = next(r for r in rows if r["sim_time_s"] >= ENTRY_S - 0.03)
        data[key] = {"rows": rows, "frames": frames, "yaw0": yaw_of(ref["base_quat_wxyz"]), "z0": ref["base_xyz"][2]}
    steps = [r for r in data["off"]["rows"] if T_START <= r["sim_time_s"] <= T_END + 1e-6]
    with tempfile.TemporaryDirectory() as tmp:
        idx = 0
        for anchor in steps:
            t = anchor["sim_time_s"]
            fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
            fig.patch.set_facecolor("white")
            fig.text(0.012, 0.975, "What happens when the stance hold switches on  (recorded Isaac runs, slowed down 4x)",
                     fontsize=14, weight="bold", va="top")
            fig.text(0.988, 0.975, "sim time %.2f s" % t, fontsize=14, va="top", ha="right",
                     color=("#b3261e" if t >= ENTRY_S - 1e-6 else "#222"))
            fig.text(0.012, 0.935, caption(t), fontsize=10.5, va="top", color="#14201c")
            trace = fig.add_axes([0.05, 0.06, 0.92, 0.16])
            for c, (key, run_id, title, sub, color) in enumerate(columns):
                rows = data[key]["rows"]
                row = next(r for r in rows if abs(r["sim_time_s"] - t) < 1e-4)
                x0 = 0.012 + c * 0.33
                fig.text(x0, 0.895, title, fontsize=12, weight="bold", color=color, va="top")
                fig.text(x0, 0.868, sub, fontsize=9, color="#333", va="top")
                mode = row.get("stance_mode") or "OFF"
                fig.text(x0 + 0.315, 0.895, mode.replace("_", " ").lower(), fontsize=8.5, ha="right", va="top",
                         color="#555")
                frame = max((f for f in data[key]["frames"] if f["sim_time_s"] <= t + 1e-6), key=lambda f: f["frame_index"])
                img_path = args.frames_dir / key / ("f%03d.png" % frame["frame_index"])
                cam = fig.add_axes([x0, 0.33, 0.19, 0.51])
                cam.imshow(mpimg.imread(img_path)); cam.axis("off")
                cam.text(4, 14, "camera (12.5 fps)", fontsize=7, color="white")
                top = fig.add_axes([x0 + 0.195, 0.63, 0.125, 0.21])
                draw_top(top, yaw_of(row["base_quat_wxyz"]) - data[key]["yaw0"], row["yaw_rate_radps"], color)
                side = fig.add_axes([x0 + 0.195, 0.45, 0.125, 0.17])
                draw_side(side, row["base_xyz"][2] - data[key]["z0"], row["base_linear_velocity_world"][2], color)
                feet = fig.add_axes([x0 + 0.205, 0.33, 0.11, 0.09])
                draw_feet(feet, row["foot_force_norms"], color)
                sel = [r for r in rows if T_START <= r["sim_time_s"] <= T_END + 1e-6]
                trace.plot([r["sim_time_s"] for r in sel], [r["yaw_rate_radps"] for r in sel], color=color,
                           lw=(1.0 if key == "off" else 1.8), label=title)
            fig.text(0.05, 0.245, "turning rate of each run (rad/s); dashed = 0.15 stillness limit; "
                     "vertical line = hold switches on", fontsize=9, color="#333")
            trace.axhline(YAW_LIMIT, ls="--", color="#333", lw=0.8); trace.axhline(-YAW_LIMIT, ls="--", color="#333", lw=0.8)
            trace.axvline(ENTRY_S, color="#333", lw=0.8)
            trace.axvline(t, color="#b3261e", lw=1.5)
            trace.set_xlim(T_START, T_END); trace.set_ylim(-0.42, 0.42)
            trace.set_xlabel("simulation time (s)", fontsize=9)
            trace.spines[["top", "right"]].set_visible(False); trace.grid(alpha=0.25)
            trace.legend(loc="lower right", fontsize=8, frameon=False, ncol=3)
            path = Path(tmp) / ("frame%04d.png" % idx)
            fig.savefig(path, dpi=100)
            plt.close(fig)
            idx += 1
            # Pause on the entry step and the step after it (1 s of video each) so the hop is not missed.
            if abs(t - ENTRY_S) < 1e-4 or abs(t - (ENTRY_S + 0.02)) < 1e-4:
                for _ in range(12):
                    shutil.copy(path, Path(tmp) / ("frame%04d.png" % idx))
                    idx += 1
        subprocess.run([
            "ffmpeg", "-loglevel", "error", "-y", "-framerate", "12.5", "-i", str(Path(tmp) / "frame%04d.png"),
            "-vf", "format=yuv420p", "-c:v", "libx264", "-crf", "28", "-preset", "slow", "-movflags", "+faststart",
            str(args.output)], check=True)
    print(args.output)


if __name__ == "__main__":
    main()
