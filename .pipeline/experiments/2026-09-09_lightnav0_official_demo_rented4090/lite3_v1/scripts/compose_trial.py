"""Local camera/route film and measured outcome from the saved Lite3 run."""
import argparse
import hashlib
import json
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TARGET = (8.517243958826407, 9.358022131055993)
BED = (9.82396, 10.4095)


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    run, out = args.run, args.out
    out.mkdir(parents=True, exist_ok=False)
    episode = json.loads((run / "episode/episode.json").read_text())
    capture = run / "capture"
    frames = rows(capture / "frames_index.jsonl")
    traces = rows(capture / "traces.jsonl")
    t0, t1 = episode["instruction_send_mono_ns"], episode["end_mono_ns"]
    samples = [f for f in frames if t0 <= f["capture_mono_ns"] <= t1]
    stop = next((t for t in traces if t.get("native_stop_consumed")), None)
    final = samples[-1]
    def dist(frame):
        return math.dist((frame["pose_x"], frame["pose_y"]), TARGET)
    status = json.loads((capture / "recorder_status.json").read_text())
    bad = []
    for f in frames:
        for key in ("front", "third"):
            if hashlib.sha256((capture / f[key+"_file"]).read_bytes()).hexdigest() != f[key+"_sha256"]:
                bad.append([f["frame_id"], key])
    after = [f for f in samples if stop and f["capture_mono_ns"] >= stop["mono_ns"]]
    still = None
    if len(after) > 1:
        still = {"seconds": (after[-1]["capture_mono_ns"]-after[0]["capture_mono_ns"])/1e9,
                 "max_abs_forward_mps": max(abs(f["velocity_linear"]) for f in after),
                 "max_abs_yaw_rps": max(abs(f["velocity_angular"]) for f in after),
                 "xy_drift_m": max(math.dist((f["pose_x"], f["pose_y"]),
                                              (after[0]["pose_x"], after[0]["pose_y"])) for f in after)}
    result = {"robot": "Lite3", "walking_policy": "model_149999 FP32 ONNX",
              "navigation_model": "LightNav-0 BF16 vLLM 0.19.1",
              "instruction": episode["instruction"], "termination": episode["termination"],
              "decisions": episode["decisions"], "consumed_stop_seq": stop["seq"] if stop else None,
              "source_wall_seconds": (t1-t0)/1e9,
              "terminal_xy": [final["pose_x"], final["pose_y"]],
              "terminal_target_distance_m": dist(final), "minimum_target_distance_m": min(map(dist, samples)),
              "terminal_bed_distance_m": math.dist((final["pose_x"], final["pose_y"]), BED),
              "minimum_base_height_m": min(f["pose_z"] for f in samples),
              "post_stop_motion": still, "jpeg_hash_mismatches": bad, "recorder": status}
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 24)
    small = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 21)
    video = out / "lite3_navigation.mp4"
    process = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                "-s", "1280x800", "-r", "20", "-i", "-", "-an", "-c:v", "libx264",
                                "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                                "-movflags", "+faststart", str(video)], stdin=subprocess.PIPE)
    xs = [f["pose_x"] for f in samples]+[TARGET[0], BED[0]]
    ys = [f["pose_y"] for f in samples]+[TARGET[1], BED[1]]
    xmin, xmax, ymin, ymax = min(xs)-0.5, max(xs)+0.5, min(ys)-0.5, max(ys)+0.5
    scale = min(570/(xmax-xmin), 230/(ymax-ymin))
    def project(x, y):
        return 30+(x-xmin)*scale, 755-(y-ymin)*scale
    index, count = 0, 0
    path = []
    for t in range(t0, t1+1, 50_000_000):
        while index+1 < len(frames) and frames[index+1]["capture_mono_ns"] <= t:
            index += 1
        f = frames[index]
        canvas = Image.new("RGB", (1280, 800), (16, 19, 25))
        for offset, key in ((0, "front"), (640, "third")):
            image = Image.open(capture / f[key+"_file"]).convert("RGB").resize((640, 360))
            canvas.paste(image, (offset, 115))
        draw = ImageDraw.Draw(canvas)
        draw.text((18, 13), 'Lite3 + LightNav-0 BF16 | walking policy: model_149999', font=font, fill="white")
        draw.text((18, 48), episode["instruction"], font=font, fill=(190, 220, 255))
        draw.text((18, 85), "ROBOT CAMERA | native 480x270", font=small, fill="white")
        draw.text((658, 85), "CHASE CAMERA | native 480x270", font=small, fill="white")
        draw.text((18, 485), "RECORDED XY ROUTE (metres)", font=small, fill="white")
        path.append(project(f["pose_x"], f["pose_y"]))
        if len(path)>1:
            draw.line(path, fill=(50, 220, 255), width=3)
        for label, xy, color in (("trashcan", TARGET, (40, 230, 130)), ("dog bed", BED, (255, 180, 60))):
            x, y = project(*xy)
            draw.ellipse((x-5, y-5, x+5, y+5), fill=color)
            draw.text((x+8, y-12), label, font=small, fill=color)
        x, y = path[-1]
        draw.ellipse((x-5, y-5, x+5, y+5), fill="white")
        stopped = stop is not None and t >= stop["mono_ns"]
        lines = [f"Wall time: {(t-t0)/1e9:.2f} s | simulation: {f['sim_time']:.2f} s",
                 f"Distance to trashcan: {dist(f):.3f} m",
                 f"Observed forward/yaw: {f['velocity_linear']:.3f} / {f['velocity_angular']:.3f}",
                 f"Requested forward/yaw: {f['command_linear']:.3f} / {f['command_angular']:.3f}",
                 f"Base height: {f['pose_z']:.3f} m",
                 f"State: {'MODEL STOP -> ZERO WALKING COMMAND' if stopped else 'NAVIGATING'}",
                 f"Camera age: {(t-f['capture_mono_ns'])/1e6:.0f} ms"]
        for line_no, text in enumerate(lines):
            draw.text((658, 488+line_no*36), text, font=small, fill="white")
        process.stdin.write(canvas.tobytes())
        count += 1
        if count == 1:
            canvas.save(out / "start.png")
        if stopped and not (out / "native_stop.png").exists():
            canvas.save(out / "native_stop.png")
    canvas.save(out / "final.png")
    process.stdin.close()
    if process.wait():
        raise RuntimeError("ffmpeg encoding failed")
    subprocess.run(["ffmpeg", "-v", "error", "-xerror", "-i", str(video), "-f", "null", "-"], check=True)
    result.update(video_sha256=hashlib.sha256(video.read_bytes()).hexdigest(),
                  video_frames=count, presentation_seconds=count/20, video_full_decode_passed=True)
    (out / "result.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!='recorder'}, indent=2))


if __name__ == "__main__":
    main()
