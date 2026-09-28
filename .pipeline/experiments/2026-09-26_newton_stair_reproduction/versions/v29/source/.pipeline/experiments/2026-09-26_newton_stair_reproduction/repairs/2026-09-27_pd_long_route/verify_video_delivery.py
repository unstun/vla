"""Verify the recorded-state replay and deliver an ordinary local MP4."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

REPAIR = Path(__file__).resolve().parent
BASE = REPAIR.parents[1]
ROOT = BASE.parents[2]
RENDER = BASE / "runs/empty_long_video10"
SOURCE = BASE / "runs/empty_long_root_live08"
DELIVERY = ROOT / "output/2026-09-27_lite3_pd_long_route/lite3_pct_scan_12m_pd.mp4"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    result = json.loads((RENDER / "result.json").read_text())
    frames = json.loads((RENDER / "frames.json").read_text())
    states = json.loads((SOURCE / "video_states.json").read_text())
    video = RENDER / "newton_stair_recorded.mp4"
    checks = {
        "source_states_unchanged": sha(SOURCE / "video_states.json") == result["source_states_sha256"],
        "video_hash": sha(video) == result["video_sha256"],
        "all_frame_hashes": all(sha(RENDER / row["file"]) == row["sha256"] for row in frames),
        "frame_count": len(frames) == len(states) == result["frames"] == 522,
        "original_frame_times": [r["physics_time_s"] for r in frames] == [r["physics_time_s"] for r in states],
        "physical_time_spacing": all(abs(b["physics_time_s"] - a["physics_time_s"] - .08) < 1e-6 for a, b in zip(frames, frames[1:])),
        "zero_render_physics_steps": result["render_only_no_physics_steps"] is True,
        "final_arrival_visible": frames[-1]["navigation_status"] == "arrived (arrived_after_quiescence)",
        "final_pd_visible": states[-1]["stance_mode"] == "FIXED_STAND",
    }
    probe = subprocess.run(["/opt/homebrew/bin/ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video)], check=True, capture_output=True, text=True)
    metadata = json.loads(probe.stdout)
    stream = metadata["streams"][0]
    checks["encoded_shape_count_duration"] = (stream["width"] == 1280 and stream["height"] == 720 and int(stream["nb_frames"]) == 522 and abs(float(metadata["format"]["duration"]) - 41.76) < .001)
    decoded = subprocess.run(["/opt/homebrew/bin/ffmpeg", "-nostdin", "-v", "error", "-i", str(video), "-f", "null", "-"], capture_output=True, text=True, timeout=60)
    checks["full_video_decode"] = decoded.returncode == 0 and not decoded.stderr.strip()
    if not all(checks.values()):
        raise RuntimeError(json.dumps(checks))
    DELIVERY.parent.mkdir(parents=True, exist_ok=True)
    if DELIVERY.exists():
        if DELIVERY.is_symlink() or sha(DELIVERY) != sha(video):
            raise ValueError("Refuse to replace an existing delivery")
    else:
        shutil.copyfile(video, DELIVERY)
    checks["regular_byte_exact_delivery"] = DELIVERY.is_file() and not DELIVERY.is_symlink() and sha(DELIVERY) == sha(video)
    review = {"checks": checks, "passed": all(checks.values()), "video": str(DELIVERY.relative_to(ROOT)), "video_sha256": sha(DELIVERY), "bytes": DELIVERY.stat().st_size, "source_run": SOURCE.name, "render_run": RENDER.name, "source_states_sha256": sha(SOURCE / "video_states.json"), "frames_verified": len(frames), "ffprobe": metadata, "full_video_decode_exit_code": decoded.returncode, "render_result": result, "visual_review": "Recorded separately after viewing beginning, travel and final-stop frames", "regenerate": "Use scripts/run_bounded.py with a new run ID and scripts/render_episode.py --source-run empty_long_root_live08. Source states must retain the recorded SHA-256; use the executed render source in empty_long_video10 for this exact camera/overlay condition."}
    (REPAIR / "video_delivery.json").write_text(json.dumps(review, indent=2) + "\n")
    print(json.dumps({"passed": review["passed"], "video": str(DELIVERY), "frames": len(frames), "bytes": review["bytes"]}))


if __name__ == "__main__":
    main()
