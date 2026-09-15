"""Compose the v3 films locally from the returned raw evidence.

Panels use one presentation clock derived from recorded monotonic time. Panel B
shows the image belonging to the newest *arrived* result, never a newer camera
image, and never a result before its recorded arrival time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v3_render import body_local_to_world
from v3_timeline import build_timeline

W, H = 1920, 1200
BAR, FOOT = 60, 60
PW, PH = 960, 540
FPS = 20
CAM_W, CAM_H = 480, 270
CAM_HEIGHT_M = 0.198
CAM_FORWARD_M = 0.090
FOVY_DEG = 79.865

ASHCAN = (8.517243958826407, 9.358022131055993)
ASHCAN_2 = (14.476999260372253, 9.029992737543653)
DOG_BED = (9.82396, 10.4095)
SPAWN = (6.5, 13.8)

WHITE, CYAN, BLUE = (255, 255, 255), (0, 220, 255), (70, 130, 255)
GREEN, AMBER, MINT, MAGENTA = (0, 220, 120), (255, 176, 0), (140, 255, 210), (255, 60, 220)
GREY, BG = (170, 170, 170), (18, 20, 24)

FONT_DIR = "/System/Library/Fonts/Supplemental/"


def font(size, bold=False, mono=False):
    if mono:
        return ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", size)
    name = "Arial Bold.ttf" if bold else "Arial.ttf"
    return ImageFont.truetype(FONT_DIR + name, size)


F24, F26, F28, F32 = font(24), font(26), font(28, True), font(32, True)
M22, M24 = font(22, mono=True), font(24, mono=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def project_ground(forward, left):
    """Robot-local ground point -> front-camera pixel using compiled extrinsics."""
    z_cam = -(forward - CAM_FORWARD_M)
    if z_cam >= -1e-6:
        return None
    x_cam, y_cam = -left, -CAM_HEIGHT_M
    f_pix = (CAM_H / 2.0) / math.tan(math.radians(FOVY_DEG) / 2.0)
    u = CAM_W / 2.0 + x_cam / (-z_cam) * f_pix
    v = CAM_H / 2.0 - y_cam / (-z_cam) * f_pix
    return u, v


class Ffmpeg:
    def __init__(self, path: Path, width: int, height: int, fps: int = FPS, crf: int = 18,
                 extra=()):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.proc = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
             "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
             "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", *extra, str(path)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self.count = 0

    def write(self, image: Image.Image):
        self.proc.stdin.write(np.asarray(image.convert("RGB"), dtype=np.uint8).tobytes())
        self.count += 1

    def close(self):
        self.proc.stdin.close()
        err = self.proc.stderr.read().decode()[-400:]
        self.proc.wait()
        if self.proc.returncode:
            raise RuntimeError(f"ffmpeg failed for {self.path}: {err}")


def raw_reader(path: Path, width: int, height: int):
    proc = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    size = width * height * 3
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        yield Image.frombytes("RGB", (width, height), buf)
    proc.stdout.close()
    proc.wait()


def label(draw, xy, text, fnt=F24, fill=WHITE, bg=(0, 0, 0, 190), pad=6):
    x, y = xy
    box = draw.textbbox((x, y), text, font=fnt)
    draw.rectangle((box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad), fill=bg)
    draw.text((x, y), text, font=fnt, fill=fill)


class Overhead:
    def __init__(self, view):
        self.w, self.h = view["width"], view["height"]
        self.lookat = view["lookat"]
        self.span_y = view["vertical_span_m"]
        self.span_x = view["horizontal_span_m"]

    def px(self, x, y):
        u = (x - self.lookat[0]) / self.span_x * self.w + self.w / 2.0
        v = self.h / 2.0 - (y - self.lookat[1]) / self.span_y * self.h
        return u, v


def draw_overhead(base: Image.Image, over: Overhead, path_xy, pose, mpc_world, entry, rep,
                  state_stamp):
    img = base.copy()
    d = ImageDraw.Draw(img, "RGBA")
    for (name, xy, colour) in (("SPAWN", SPAWN, GREY), ("TRASHCAN (target)", ASHCAN, GREEN),
                               ("dog bed", DOG_BED, AMBER), ("trashcan #2", ASHCAN_2, (90, 190, 130))):
        u, v = over.px(*xy)
        if -40 < u < over.w + 40 and -40 < v < over.h + 40:
            r = 11 if colour is GREEN else 8
            d.ellipse((u - r, v - r, u + r, v + r), outline=colour, width=3)
            d.text((u + 13, v - 12), name, font=F24, fill=colour,
                   stroke_width=3, stroke_fill=(0, 0, 0))
    if len(path_xy) > 1:
        d.line([over.px(x, y) for x, y in path_xy], fill=CYAN, width=4)
    if mpc_world and len(mpc_world) > 1:
        d.line([over.px(x, y) for x, y in mpc_world], fill=BLUE, width=4)
        for x, y in mpc_world:
            u, v = over.px(x, y)
            d.ellipse((u - 3, v - 3, u + 3, v + 3), fill=BLUE)
    if pose:
        x, y, yaw = pose
        u, v = over.px(x, y)
        tipu, tipv = over.px(x + 0.55 * math.cos(yaw), y + 0.55 * math.sin(yaw))
        d.line((u, v, tipu, tipv), fill=WHITE, width=5)
        d.ellipse((u - 9, v - 9, u + 9, v + 9), fill=WHITE, outline=(0, 0, 0), width=2)
    # fixed scale bar
    u0, v0 = over.px(over.lookat[0] - over.span_x / 2 + 0.4, over.lookat[1] - over.span_y / 2 + 0.35)
    u1, _ = over.px(over.lookat[0] - over.span_x / 2 + 1.4, over.lookat[1] - over.span_y / 2 + 0.35)
    d.line((u0, v0, u1, v0), fill=WHITE, width=4)
    d.text((u0, v0 - 34), "1 m", font=F24, fill=WHITE, stroke_width=3, stroke_fill=(0, 0, 0))
    label(d, (14, 12), f"OFFLINE STATE REPLAY  {rep}  fixed orthographic view", F24)
    label(d, (14, 48), f"state t={state_stamp}", F24)
    return img


def behaviour_panel(series, cursor_index, rep):
    img = Image.new("RGB", (PW, PH), BG)
    d = ImageDraw.Draw(img)
    d.text((14, 8), "D: BEHAVIOR / TIMING", font=F28, fill=WHITE)
    rows = [
        ("distance to trashcan (m)", series["dist"], GREEN, None),
        ("observed fwd (m/s) / yaw (rad/s)", series["vel"], CYAN, series["yaw_rate"]),
        ("applied cmd fwd / yaw", series["cmd"], BLUE, series["cmd_yaw"]),
        ("inference round trip (ms) / MPC solve (ms)", series["rtt"], MAGENTA, series["solve"]),
    ]
    top, height, gap = 62, 96, 22
    n = len(series["t"])
    for i, (title, values, colour, second) in enumerate(rows):
        y0 = top + i * (height + gap)
        d.rectangle((60, y0, PW - 20, y0 + height), outline=(60, 66, 74))
        d.text((14, y0 - 26), title, font=F24, fill=GREY)
        finite = [v for v in values if v is not None] + [v for v in (second or []) if v is not None]
        lo, hi = (min(finite), max(finite)) if finite else (0.0, 1.0)
        if hi - lo < 1e-9:
            hi = lo + 1.0
        d.text((16, y0 + height - 26), f"{lo:.2f}", font=M22, fill=GREY)
        d.text((16, y0 + 4), f"{hi:.2f}", font=M22, fill=GREY)

        def plot(vals, col):
            pts = []
            for k, v in enumerate(vals):
                if v is None:
                    continue
                x = 60 + (PW - 80) * (k / max(1, n - 1))
                y = y0 + height - (v - lo) / (hi - lo) * height
                pts.append((x, y))
            if len(pts) > 1:
                d.line(pts, fill=col, width=3)
        plot(values, colour)
        if second:
            plot(second, AMBER)
        x = 60 + (PW - 80) * (cursor_index / max(1, n - 1))
        d.line((x, y0, x, y0 + height), fill=(255, 255, 255, 120), width=2)
        current = values[cursor_index] if cursor_index < len(values) else None
        text = "-" if current is None else f"{current:8.3f}"
        if second:
            other = second[cursor_index] if cursor_index < len(second) else None
            text += "   " + ("-" if other is None else f"{other:8.3f}")
        d.text((PW - 330, y0 - 26), text, font=M22, fill=WHITE)
    d.text((14, PH - 26), "observed velocity (cyan) vs applied command (blue/amber) are separate series",
           font=F24, fill=GREY)
    return img


def model_panel(jpeg_path, record, seq, capture_ns, result_ns, now_ns, applied, title="B: MODEL EVIDENCE"):
    img = Image.new("RGB", (PW, PH), BG)
    if jpeg_path is None:
        d = ImageDraw.Draw(img)
        d.text((30, PH // 2 - 20), "WAITING FOR RESULT", font=F32, fill=AMBER)
        d.text((30, PH // 2 + 24), "no completed model result has arrived yet", font=F24, fill=GREY)
        return img
    src = Image.open(jpeg_path).convert("RGB")
    scale, ox, oy = 1.6, 96, 34
    iw, ih = int(CAM_W * scale), int(CAM_H * scale)
    img.paste(src.resize((iw, ih), Image.LANCZOS), (ox, oy))
    d = ImageDraw.Draw(img, "RGBA")
    if record:
        pointing = record.get("pointing") or {}
        for key, colour, name in (("apos_px", MINT, "APOS"), ("opos_px", MAGENTA, "OPOS")):
            px = pointing.get(key)
            if px:
                u, v = px[0] * scale + ox, px[1] * scale + oy
                d.line((u - 16, v, u + 16, v), fill=colour, width=3)
                d.line((u, v - 16, u, v + 16), fill=colour, width=3)
                d.ellipse((u - 11, v - 11, u + 11, v + 11), outline=colour, width=3)
                d.text((u + 15, v + 8), name, font=F24, fill=colour,
                       stroke_width=3, stroke_fill=(0, 0, 0))
        pts = []
        for point in record.get("waypoints") or []:
            projected = project_ground(point[0], point[1])
            if projected:
                pts.append((projected[0] * scale + ox, projected[1] * scale + oy))
        if len(pts) > 1:
            d.line(pts, fill=BLUE, width=4)
        for u, v in pts:
            d.ellipse((u - 4, v - 4, u + 4, v + 4), fill=BLUE)
    age_ms = (now_ns - capture_ns) / 1e6 if capture_ns else 0.0
    label(d, (12, 4), f"{title}  seq {seq}  native 480x270 (letterboxed, no added detail)", F24)
    strip_y = oy + ih + 4
    d.rectangle((0, strip_y, PW, PH), fill=(10, 12, 15))
    d.text((12, strip_y + 8),
           f"capture {capture_ns/1e9:.3f}s   result {result_ns/1e9:.3f}s   INPUT AGE {age_ms:7.0f} ms",
           font=M24, fill=AMBER if age_ms > 400 else WHITE)
    raw = (record or {}).get("raw_text", "")
    d.text((12, strip_y + 42), raw[:74], font=M24, fill=WHITE)
    if not applied:
        label(d, (PW - 290, 4), "NOT APPLIED", F28, fill=(255, 90, 90))
    return img


def native_panel(jpeg_path, stamp_ns, now_ns, title):
    img = Image.new("RGB", (PW, PH), BG)
    d = ImageDraw.Draw(img, "RGBA")
    if jpeg_path is None:
        d.text((30, PH // 2), "WAITING FOR CAMERA", font=F32, fill=AMBER)
        return img
    src = Image.open(jpeg_path).convert("RGB")
    img.paste(src.resize((840, 472), Image.LANCZOS), (60, 56))
    age_ms = (now_ns - stamp_ns) / 1e6
    label(d, (12, 6), f"{title}  native 480x270 (letterboxed)  frame age {age_ms:.0f} ms", F24)
    return img


def compose(rep, cfg, out_dir, capture_root, analysis_dir, view, gpu_note):
    slice_data = json.loads((analysis_dir / f"{rep}_slice.json").read_text())
    episode = slice_data["episode"]
    frames = slice_data["frames"]
    joined = slice_data["joined"]
    controls = slice_data["consumptions"] + slice_data["controls"]
    t0, t1 = episode["instruction_send_mono_ns"], episode["end_mono_ns"]
    timeline = build_timeline(t0, t1, frames, joined, fps=FPS)

    frames_by_id = {f["frame_id"]: f for f in frames}
    applied_seqs = {c["seq"] for c in slice_data["consumptions"] if c.get("applied_to_mpc")}
    stop_seqs = {c["seq"] for c in slice_data["consumptions"] if c.get("native_stop_consumed")}
    discarded = {c["seq"] for c in slice_data["consumptions"]
                 if c.get("disposition") == "discarded_after_stop"}
    consumption_by_seq = {c["seq"]: c for c in slice_data["consumptions"]}

    # behaviour series sampled on the presentation clock
    ctrl = sorted(slice_data["controls"], key=lambda c: c["mono_ns"])
    series = {k: [] for k in ("t", "dist", "vel", "yaw_rate", "cmd", "cmd_yaw", "rtt", "solve")}
    for entry in timeline:
        frame = entry["frame"]
        series["t"].append(entry["elapsed_s"])
        if frame:
            series["dist"].append(math.dist((frame["pose_x"], frame["pose_y"]), ASHCAN))
            series["vel"].append(frame["velocity_linear"])
            series["yaw_rate"].append(frame["velocity_angular"])
            series["cmd"].append(frame["command_linear"])
            series["cmd_yaw"].append(frame["command_angular"])
        else:
            for key in ("dist", "vel", "yaw_rate", "cmd", "cmd_yaw"):
                series[key].append(None)
        prediction = entry["prediction"]
        if prediction:
            series["rtt"].append((prediction["receive_mono_ns"] - prediction["send_mono_ns"]) / 1e6)
        else:
            series["rtt"].append(None)
        recent = [c for c in ctrl if c["mono_ns"] <= entry["t_ns"]]
        series["solve"].append(recent[-1].get("mpc_solve_ms") if recent else None)

    over = Overhead(view)
    reader = raw_reader(analysis_dir / f"topdown_raw_{rep}.mp4", view["width"], view["height"])
    master = Ffmpeg(out_dir / "overview_wall.mp4", W, H, crf=18)
    topdown_out = Ffmpeg(out_dir / "topdown_state_replay_wall.mp4", view["width"], view["height"], crf=18)
    front_out = Ffmpeg(out_dir / "native_front_wall.mp4", CAM_W, CAM_H, crf=16)
    third_out = Ffmpeg(out_dir / "native_third_wall.mp4", CAM_W, CAM_H, crf=16)

    path_xy = []
    keyframes = {}
    first_turn_index = None
    for index, entry in enumerate(timeline):
        if first_turn_index is None and entry["frame"] and abs(entry["frame"]["velocity_angular"]) > 0.35:
            first_turn_index = index
    stop_index = None
    if episode.get("native_stop_mono_ns"):
        for index, entry in enumerate(timeline):
            if entry["t_ns"] >= episode["native_stop_mono_ns"]:
                stop_index = index
                break

    for index, entry in enumerate(timeline):
        try:
            top = next(reader)
        except StopIteration:
            top = Image.new("RGB", (view["width"], view["height"]), BG)
        frame = entry["frame"]
        if frame:
            path_xy.append((frame["pose_x"], frame["pose_y"]))
            pose = (frame["pose_x"], frame["pose_y"], frame["pose_yaw"])
            front_path = capture_root / frame["front_file"]
            third_path = capture_root / frame["third_file"]
            front_out.write(Image.open(front_path).convert("RGB"))
            third_out.write(Image.open(third_path).convert("RGB"))
        else:
            pose, front_path, third_path = None, None, None
            front_out.write(Image.new("RGB", (CAM_W, CAM_H), BG))
            third_out.write(Image.new("RGB", (CAM_W, CAM_H), BG))

        prediction = entry["prediction"]
        mpc_world = []
        if prediction and prediction["seq"] in applied_seqs:
            consumption = consumption_by_seq[prediction["seq"]]
            capture_pose = consumption.get("capture_pose")
            if capture_pose:
                mpc_world = [body_local_to_world(capture_pose, p[0], p[1])
                             for p in consumption.get("waypoints", [])]
        state_stamp = f"sim {frame['sim_time']:.2f}s / mono {(entry['t_ns']-t0)/1e9:.2f}s" if frame else "-"
        top_labelled = draw_overhead(top, over, path_xy, pose, mpc_world, entry, rep, state_stamp)
        topdown_out.write(top_labelled)

        canvas = Image.new("RGB", (W, H), (8, 9, 11))
        canvas.paste(native_panel(third_path, frame["capture_mono_ns"] if frame else entry["t_ns"],
                                  entry["t_ns"], "A: LIVE-CAPTURE CHASE"), (0, BAR))
        record = prediction.get("record") if prediction else None
        model_jpeg = None
        if prediction:
            source = frames_by_id.get(prediction["frame_id"])
            if source is not None:
                model_jpeg = capture_root / source["front_file"]
        canvas.paste(model_panel(
            model_jpeg, record, prediction["seq"] if prediction else None,
            prediction["capture_mono_ns"] if prediction else 0,
            prediction["receive_mono_ns"] if prediction else 0,
            entry["t_ns"],
            bool(prediction and prediction["seq"] not in discarded)), (PW, BAR))
        fit_h = PH
        fit_w = int(PH * view["width"] / view["height"])
        if fit_w > PW:
            fit_w, fit_h = PW, int(PW * view["height"] / view["width"])
        canvas.paste(top_labelled.resize((fit_w, fit_h), Image.LANCZOS),
                     ((PW - fit_w) // 2, BAR + PH + (PH - fit_h) // 2))
        canvas.paste(behaviour_panel(series, index, rep), (PW, BAR + PH))

        d = ImageDraw.Draw(canvas, "RGBA")
        d.rectangle((0, 0, W, BAR), fill=(24, 27, 32))
        d.text((14, 14), f'"{episode["instruction"]}"', font=F28, fill=WHITE)
        d.text((1080, 14), f'{rep} | {gpu_note} | t={entry["elapsed_s"]:6.2f}s wall',
               font=F26, fill=CYAN)
        d.rectangle((0, H - FOOT, W, H), fill=(24, 27, 32))
        loss = cfg["recording_losses"]
        state = "NATIVE STOP" if (stop_index is not None and index >= stop_index) else "VLN CONTROL"
        d.text((14, H - FOOT + 16),
               f'sim {frame["sim_time"]:.2f}s | frames {index+1}/{len(timeline)} | '
               f'captured {len(frames)} | predictions {len(joined)} | recording losses {loss} | {state}'
               if frame else f'frames {index+1}/{len(timeline)} | {state}',
               font=F24, fill=GREY)
        d.text((1500, H - FOOT + 16), f'termination: {episode["termination"]}', font=F24, fill=AMBER)
        master.write(canvas)

        if index == 0:
            keyframes["start"] = canvas.copy()
        if first_turn_index is not None and index == first_turn_index:
            keyframes["first_turn"] = canvas.copy()
        if stop_index is not None and index == stop_index:
            keyframes["native_stop"] = canvas.copy()
        keyframes["final"] = canvas

    for out in (master, topdown_out, front_out, third_out):
        out.close()
    for name, image in keyframes.items():
        image.save(out_dir / f"keyframe_{name}.png")

    # decision review: one decision per 0.5 s presentation unit, explicitly not wall time
    review = Ffmpeg(out_dir / "model_decisions.mp4", PW, PH + 46, crf=18)
    for prediction in joined:
        frame = frames_by_id.get(prediction["frame_id"])
        panel = model_panel(capture_root / frame["front_file"] if frame else None,
                            prediction.get("record"), prediction["seq"],
                            prediction["capture_mono_ns"], prediction["receive_mono_ns"],
                            prediction["receive_mono_ns"],
                            prediction["seq"] not in discarded,
                            title="DECISION REVIEW / NOT WALL TIME")
        canvas = Image.new("RGB", (PW, PH + 46), BG)
        canvas.paste(panel, (0, 46))
        d = ImageDraw.Draw(canvas)
        d.rectangle((0, 0, PW, 46), fill=(70, 40, 10))
        d.text((10, 10), f"DECISION REVIEW / NOT WALL TIME - {rep} seq {prediction['seq']}",
               font=F26, fill=AMBER)
        for _ in range(10):
            review.write(canvas)
    review.close()

    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out_dir / "overview_wall.mp4"),
                    "-vf", "scale=1280:800", "-c:v", "libx264", "-preset", "medium", "-crf", "26",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(out_dir / "overview_share.mp4")], check=True)
    return timeline, series, slice_data


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                          "-show_entries", "stream=codec_name,width,height,nb_read_frames,r_frame_rate,pix_fmt",
                          "-show_entries", "format=duration,size", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True)
    data = json.loads(out.stdout)
    stream = data["streams"][0]
    return {"codec": stream["codec_name"], "width": stream["width"], "height": stream["height"],
            "frames": int(stream["nb_read_frames"]), "frame_rate": stream["r_frame_rate"],
            "pix_fmt": stream["pix_fmt"], "pts_duration_s": float(data["format"]["duration"]),
            "bytes": int(data["format"]["size"]), "sha256": sha256_file(path)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", required=True)
    ap.add_argument("--capture", required=True)
    ap.add_argument("--reps", default="rep_04,rep_05,rep_06")
    args = ap.parse_args()
    pkg = Path(args.pkg)
    capture_root = Path(args.capture)
    analysis = pkg / "analysis"
    meta = json.loads((analysis / "replay_meta.json").read_text())
    view = meta["view"]
    status = json.loads((capture_root / "recorder_status.json").read_text())
    losses = (status["queue_drops"] + status["write_failures"]
              + status["duplicate_names"] + status["malformed_rows"])
    gpu_note = "RTX 4090 | vLLM BF16 (vllm_local) | greedy"
    all_meta = {}
    for rep in args.reps.split(","):
        out_dir = pkg / "media" / rep
        out_dir.mkdir(parents=True, exist_ok=True)
        timeline, series, slice_data = compose(
            rep, {"recording_losses": losses}, out_dir, capture_root, analysis, view, gpu_note)
        episode = slice_data["episode"]
        files = {}
        for name, kind in (("overview_wall.mp4", "live_capture+state_replay"),
                           ("overview_share.mp4", "live_capture+state_replay"),
                           ("native_front_wall.mp4", "live_capture"),
                           ("native_third_wall.mp4", "live_capture"),
                           ("topdown_state_replay_wall.mp4", "state_replay"),
                           ("model_decisions.mp4", "decision_review")):
            path = out_dir / name
            info = probe(path)
            info["label"] = kind
            info["wall_time_preserved"] = kind != "decision_review"
            files[name] = info
        source_span = (episode["end_mono_ns"] - episode["instruction_send_mono_ns"]) / 1e9
        unique_sources = len({e["frame_id"] for e in timeline if e["frame_id"] is not None})
        all_meta[rep] = {
            "source_time_basis": "recorded CLOCK_MONOTONIC in the demo process; presentation clock = 20 fps sampling of that span",
            "measured_source_span_s": source_span,
            "presentation_frames": len(timeline),
            "unique_source_frames": unique_sources,
            "output_repetitions": len(timeline) - unique_sources,
            "gaps_over_150ms": sum(1 for e in timeline if e["frame_age_ns"] and e["frame_age_ns"] > 150_000_000),
            "max_frame_age_ms": max((e["frame_age_ns"] or 0) for e in timeline) / 1e6,
            "captured_frames_in_run": len(slice_data["frames"]),
            "predictions_joined": len(slice_data["joined"]),
            "join_problems": slice_data["join_problems"],
            "recording_losses": losses,
            "files": files,
            "keyframes": {p.name: sha256_file(p) for p in sorted(out_dir.glob("keyframe_*.png"))},
        }
        (out_dir / "video_metadata.json").write_text(json.dumps(all_meta[rep], indent=2) + "\n")
        print(rep, json.dumps({k: all_meta[rep][k] for k in
                               ("presentation_frames", "unique_source_frames", "output_repetitions",
                                "measured_source_span_s", "predictions_joined")}), flush=True)
    (pkg / "media" / "video_metadata_all.json").write_text(json.dumps(all_meta, indent=2) + "\n")


if __name__ == "__main__":
    main()
