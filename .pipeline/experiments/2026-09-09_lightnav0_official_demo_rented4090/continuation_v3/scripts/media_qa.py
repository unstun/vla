"""Full-decode media QA: every MP4 must decode end to end, and the primary film's
measured segment must match the recorded monotonic span within one 20 fps frame."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

PKG = Path(sys.argv[1]).resolve()
results = {}
failures = []
for path in sorted(PKG.glob("media/**/*.mp4")):
    rel = str(path.relative_to(PKG))
    decode = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"],
                            capture_output=True, text=True)
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                            "-show_entries", "stream=codec_name,width,height,nb_read_frames,pix_fmt,r_frame_rate",
                            "-show_entries", "format=duration,size", "-of", "json", str(path)],
                           capture_output=True, text=True, check=True)
    data = json.loads(probe.stdout)
    stream, fmt = data["streams"][0], data["format"]
    entry = {"full_decode_ok": decode.returncode == 0 and not decode.stderr.strip(),
             "decode_stderr": decode.stderr.strip()[:300],
             "codec": stream["codec_name"], "width": stream["width"], "height": stream["height"],
             "pix_fmt": stream["pix_fmt"], "frames_decoded": int(stream["nb_read_frames"]),
             "frame_rate": stream["r_frame_rate"],
             "pts_duration_s": float(fmt["duration"]), "bytes": int(fmt["size"])}
    results[rel] = entry
    if not entry["full_decode_ok"]:
        failures.append(rel)

for rep in ("rep_04", "rep_05", "rep_06"):
    meta = json.loads((PKG / "media" / rep / "video_metadata.json").read_text())
    span = meta["measured_source_span_s"]
    for name in ("overview_wall.mp4", "topdown_state_replay_wall.mp4",
                 "native_front_wall.mp4", "native_third_wall.mp4"):
        entry = results[f"media/{rep}/{name}"]
        delta = abs(entry["pts_duration_s"] - span)
        entry["source_monotonic_span_s"] = span
        entry["pts_minus_source_s"] = entry["pts_duration_s"] - span
        entry["within_one_frame_of_source"] = delta <= 1.0 / 20 + 1e-6
        entry["editorial_holds_s"] = 0.0
        if not entry["within_one_frame_of_source"]:
            failures.append(f"{rep}/{name} timing {delta:.4f}s")
    results[f"media/{rep}/model_decisions.mp4"]["wall_time_claim"] = \
        "DECISION REVIEW / NOT WALL TIME - intentionally not a wall-clock film"
    results[f"media/{rep}/overview_share.mp4"]["note"] = "compact share copy of the master"

out = {"failures": failures, "passed": not failures, "files": results}
(PKG / "media" / "media_qa.json").write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"passed": out["passed"], "failures": failures,
                  "checked": len(results)}, indent=2))
for rep in ("rep_04", "rep_05", "rep_06"):
    e = results[f"media/{rep}/overview_wall.mp4"]
    print(rep, "master", e["width"], "x", e["height"], e["frames_decoded"], "frames",
          f'{e["pts_duration_s"]:.3f}s vs source {e["source_monotonic_span_s"]:.3f}s',
          f'delta {e["pts_minus_source_s"]:+.4f}s')
