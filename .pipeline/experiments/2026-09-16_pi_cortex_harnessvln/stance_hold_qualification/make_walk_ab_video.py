#!/usr/bin/env python3
"""Side-by-side review video of the scripted walk-stop-start-stop runs (task 09-17-isaac-runner-stance-hold, PRD D5).

Each panel is one recorded run's side follow camera (third_person_master.mp4, 25 fps). The label shows the run and
the stance-hold mode at that instant (walking = RL, settling, blend into hold, hold, blend back). A timeline at the
bottom shows the commanded and measured forward speed and the yaw rate for every run. The video has three parts:
the whole run in real time, then the first stop and the second start slowed down 4x. Everything drawn comes from
the recorded files.

    make_walk_ab_video.py --run LABEL=RUN_DIR [--run ...] --output OUT.mp4 [--work DIR]
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

COLORS = ["#6b6b6b", "#0072B2", "#009E73", "#CC79A7"]
MODE_TEXT = {
    None: "RL (V12 walking / standing)", "OFF": "RL only (hold off)", "RL": "RL (V12)",
    "STAND_SETTLING": "RL, waiting for a quiet stance", "STAND_TRANSITION": "blending into PD hold",
    "FIXED_STAND": "PD stance hold", "REJOIN": "blending back to RL",
}
MODE_COLOR = {"STAND_TRANSITION": "#E69F00", "FIXED_STAND": "#0072B2", "REJOIN": "#D55E00"}
PARTS = [("whole run, real time", 0.0, 21.0, 1), ("first stop (7.0 s), 4x slower", 6.8, 9.6, 4),
         ("second start (12.0 s), 4x slower", 11.6, 13.2, 4)]
FPS = 25


def load_run(run_dir):
    out = Path(run_dir) / "returned_artifacts/runner_output"
    rows = [json.loads(l) for l in (out / "metrics.jsonl").read_text().splitlines() if l.strip()]
    frames = [json.loads(l) for l in (out / "camera_frames.jsonl").read_text().splitlines() if l.strip()]
    return rows, frames, out / "third_person_master.mp4"


def forward_speed(row):
    v = row["base_linear_velocity_world"]
    return v[0]


def row_at(rows, t):
    lo, hi = 0, len(rows) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if rows[mid]["sim_time_s"] <= t + 1e-6:
            lo = mid
        else:
            hi = mid - 1
    return rows[lo]


def frame_at(frames, t):
    best = frames[0]
    for f in frames:
        if f["sim_time_s"] <= t + 1e-6:
            best = f
        else:
            break
    return best["frame_index"]


def extract(video, dest, width):
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vf", "scale=%d:-2" % width,
                    "-q:v", "4", "-start_number", "0", str(dest / "f%05d.jpg")], check=True)


def phase_text(cmd_vx, t):
    return ("command: walk forward %.1f m/s" % cmd_vx) if abs(cmd_vx) > 1e-3 else "command: stop (zero)"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True, help="LABEL=RUN_DIR (2-4 runs)")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work", type=Path, default=None)
    args = parser.parse_args()
    runs = []
    for item in args.run:
        label, path = item.split("=", 1)
        rows, frames, video = load_run(path)
        runs.append({"label": label, "rows": rows, "frames": frames, "video": video})
    work = Path(args.work or tempfile.mkdtemp(prefix="walk_ab_"))
    for i, run in enumerate(runs):
        run["dir"] = work / ("run%d" % i)
        if not (run["dir"] / "f00000.jpg").exists():
            extract(run["video"], run["dir"], 640)
    out_frames = work / "out"
    shutil.rmtree(out_frames, ignore_errors=True)
    out_frames.mkdir(parents=True)
    ncol = 2
    nrow = math.ceil(len(runs) / ncol)
    idx = 0
    for part_title, t0, t1, slow in PARTS:
        n = int(round((t1 - t0) * FPS * slow))
        for k in range(n):
            t = t0 + k / (FPS * slow)
            fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
            ref = row_at(runs[0]["rows"], t)
            cmd_vx = ref["admitted_command"][0]
            fig.text(0.012, 0.978, "Walk - stop - start - stop, side view  |  %s" % part_title, fontsize=13,
                     weight="bold", va="top")
            fig.text(0.988, 0.978, "sim %.2f s" % t, fontsize=13, va="top", ha="right")
            fig.text(0.012, 0.945, phase_text(cmd_vx, t), fontsize=11, va="top",
                     color=("#b3261e" if abs(cmd_vx) < 1e-3 else "#1b7a4a"), weight="bold")
            grid_h = 0.62
            for i, run in enumerate(runs):
                r, c = divmod(i, ncol)
                w = 0.49
                h = grid_h / nrow
                x0 = 0.008 + c * 0.497
                y0 = 0.30 + (nrow - 1 - r) * h
                ax = fig.add_axes([x0, y0, w, h - 0.035])
                fi = frame_at(run["frames"], t)
                img = run["dir"] / ("f%05d.jpg" % fi)
                if img.exists():
                    ax.imshow(mpimg.imread(img))
                ax.axis("off")
                row = row_at(run["rows"], t)
                mode = row.get("stance_mode")
                fig.text(x0, y0 + h - 0.033, run["label"], fontsize=10.5, weight="bold", color=COLORS[i], va="bottom")
                fig.text(x0 + w, y0 + h - 0.033, MODE_TEXT.get(mode, mode), fontsize=10, va="bottom", ha="right",
                         color=MODE_COLOR.get(mode, "#333"), weight=("bold" if mode in MODE_COLOR else "normal"))
                yr = row["yaw_rate_radps"]
                ax.text(8, 22, "fwd %.2f m/s   turn %+.2f rad/s   pitch %+.1f deg" % (
                    forward_speed(row), yr, math.degrees(row["base_rpy_rad"][1])), fontsize=8.5,
                    color=("#ffb4ab" if abs(yr) > 0.15 else "white"))
            tl = fig.add_axes([0.05, 0.155, 0.93, 0.115])
            tl2 = fig.add_axes([0.05, 0.035, 0.93, 0.105], sharex=tl)
            for i, run in enumerate(runs):
                ts = [x["sim_time_s"] for x in run["rows"]]
                tl.plot(ts, [forward_speed(x) for x in run["rows"]], color=COLORS[i], lw=1.1)
                tl2.plot(ts, [x["yaw_rate_radps"] for x in run["rows"]], color=COLORS[i], lw=1.1, label=run["label"])
            ts = [x["sim_time_s"] for x in runs[0]["rows"]]
            tl.plot(ts, [x["admitted_command"][0] for x in runs[0]["rows"]], color="black", lw=1.0, ls="--")
            tl.set_ylabel("fwd m/s", fontsize=8); tl2.set_ylabel("turn rad/s", fontsize=8)
            tl2.axhline(0.15, ls=":", color="#333", lw=0.8); tl2.axhline(-0.15, ls=":", color="#333", lw=0.8)
            for a in (tl, tl2):
                a.axvline(t, color="#b3261e", lw=1.4)
                a.set_xlim(0, 21); a.grid(alpha=0.25); a.tick_params(labelsize=7.5)
                a.spines[["top", "right"]].set_visible(False)
                if slow > 1:
                    a.axvspan(t0, t1, color="#E69F00", alpha=0.08)
            tl.tick_params(labelbottom=False)
            tl2.set_ylim(-0.6, 0.6)
            tl2.legend(loc="upper right", fontsize=7, ncol=len(runs), frameon=False)
            fig.text(0.05, 0.278, "forward speed (dashed = command)  and  turning rate (dotted = 0.15 limit); "
                     "red line = now", fontsize=8.5, color="#333")
            fig.savefig(out_frames / ("o%05d.png" % idx), dpi=100)
            plt.close(fig)
            idx += 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(FPS), "-i",
                    str(out_frames / "o%05d.png"), "-vf", "format=yuv420p", "-c:v", "libx264", "-crf", "30",
                    "-preset", "slow", "-movflags", "+faststart", str(args.output)], check=True)
    print(args.output, idx, "frames")


if __name__ == "__main__":
    main()
