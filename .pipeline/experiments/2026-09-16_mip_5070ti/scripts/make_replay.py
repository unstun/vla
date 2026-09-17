"""Encode original observe frames at 2 FPS, explicitly not real-time playback."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    summary = json.loads((run / "summary.json").read_text())
    if len(summary["episodes"]) != 1:
        raise ValueError("This replay entry expects exactly one completed episode record")
    frames = sorted((run / "live_0").glob("obs_*.png"))
    if not frames:
        raise ValueError("No original observe frames")
    output = run / "replay_2fps.mp4"
    subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
        "-framerate", "2", "-pattern_type", "glob", "-i", str(run / "live_0/obs_*.png"),
        "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-metadata", "comment=One original observe frame per 0.5s; not wall-clock or simulation time",
        str(output),
    ], check=True)
    probe = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,nb_read_frames,r_frame_rate,duration",
        "-of", "json", str(output),
    ]))
    stream = probe["streams"][0]
    if int(stream["nb_read_frames"]) != len(frames):
        raise ValueError("Encoded frame count differs from original observation count")
    report = {"time_basis": "2 FPS per observe call; not real-time", "frames": len(frames),
              "video": output.name, "video_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
              "ffprobe": probe, "episode_wall_seconds": summary["episodes"][0]["wall_sec"]}
    (run / "replay_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
