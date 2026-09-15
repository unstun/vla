"""Package a trajectory-overlay video using actual wall-time frame timestamps."""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    run = root / "runs" / sys.argv[1]
    states = [json.loads(line) for line in (run / "telemetry.jsonl").read_text().splitlines()]
    moving = [s for s in states if not s["held"] and s["planned_world"]]
    if not moving:
        raise RuntimeError("No live model trajectory available; cannot deliver a navigation video")
    # Trim only initial stationary setup/waiting; no internal splice or speedup.
    begin = moving[0]["time_unix"] - 1
    video_states = [s for s in states if s["time_unix"] >= begin]
    concat = []
    for index, state in enumerate(video_states):
        frame = run / "frames" / f"{state['sequence']:06d}.jpg"
        if not frame.is_file():
            raise RuntimeError(f"Missing rendered frame: {frame}")
        concat.append(f"file 'frames/{frame.name}'")
        if index + 1 < len(video_states):
            duration = video_states[index+1]["time_unix"] - state["time_unix"]
            if duration <= 0:
                raise RuntimeError("Non-increasing video wall clock")
            concat.append(f"duration {duration:.6f}")
    concat.append(concat[-1])
    (run / "video_frames.txt").write_text("\n".join(concat) + "\n")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(run / "video_frames.txt"), "-fps_mode", "vfr", "-c:v", "libx264",
                    "-preset", "fast", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(run / "navigation_with_trajectory.mp4")], check=True, timeout=120)
    for label, state in [("start", moving[0]), ("middle", moving[len(moving)//2]), ("end", moving[-1])]:
        shutil.copy2(run / "frames" / f"{state['sequence']:06d}.jpg", run / f"trajectory_{label}.jpg")
    observations = root / "work/DynaNav/logs" / run.name / "carter_ticvla_data"
    (run / "observations").mkdir(exist_ok=True)
    for name in ["inference_audit.jsonl", "control_audit.jsonl"]:
        if (observations / name).is_file():
            shutil.copy2(observations / name, run / "observations" / name)
    result_dir = root / "work/DynaNav/benchmark_results" / run.name
    shutil.copytree(result_dir, run / "benchmark_results", dirs_exist_ok=True)
    inference = [json.loads(line) for line in (run / "observations/inference_audit.jsonl").read_text().splitlines()]
    original = json.loads((run / "benchmark_results/hospital_demo_results_latest.json").read_text())
    resources = [json.loads(line) for line in (run / "resources.jsonl").read_text().splitlines()]
    gpu = [float(r["gpu_csv"].split(",")[0]) for r in resources if r["gpu_csv"]]
    meta = json.loads((run / "meta.json").read_text())
    observed_instructions = sorted(set(r.get("instruction", "") for r in inference))
    if meta.get("instruction_mode") == "verbatim" and observed_instructions != [meta["instruction"]]:
        raise RuntimeError("Model-instruction audit does not match the verbatim request")
    summary = {"run_id": run.name, "episode": original["episodes"][0],
               "model_instructions": observed_instructions,
               "instruction_mode": meta.get("instruction_mode", "legacy"),
               "inference_seed": meta.get("inference_seed"),
               "camera_view": moving[0].get("camera_view", "third_person"),
               "model_calls": len(inference), "finite_30x2": all(r["finite"] and r["shape"] == [1,30,2] for r in inference),
               "gpu_peak_sampled_mib": max(gpu), "video_frames": len(video_states),
               "video_wall_span_seconds": video_states[-1]["time_unix"]-video_states[0]["time_unix"],
               "trimmed_initial_wait_seconds": video_states[0]["time_unix"]-states[0]["time_unix"],
               "video_time_basis": "actual wall timestamps; only initial stationary wait trimmed; no internal cuts",
               "overlay": "camera projection of FLU model output in cyan, driven path in orange; no depth occlusion",
               "input_camera": "unmodified RGB; overlay applied only to output copy"}
    (run / "analysis.json").write_text(json.dumps(summary, indent=2) + "\n")
    shutil.make_archive(str(run / "raw_overlay_frames"), "gztar", root_dir=run, base_dir="frames")
    records = [{"path": str(p.relative_to(run)), "bytes": p.stat().st_size, "sha256": sha256(p)}
               for p in sorted(run.rglob("*")) if p.is_file() and p.name != "artifact_sha256.json"]
    (run / "artifact_sha256.json").write_text(json.dumps(records, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
