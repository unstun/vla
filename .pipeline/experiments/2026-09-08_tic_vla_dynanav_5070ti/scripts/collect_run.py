"""Collect original benchmark evidence and encode the retained camera frames."""

import hashlib
import json
import shutil
import statistics
import subprocess
import sys
from pathlib import Path


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    root = Path(sys.argv[1]).resolve()
    run_id = sys.argv[2]
    run = root / "runs" / run_id
    observations = root / "work/DynaNav/logs" / run_id / "carter_ticvla_data"
    target = run / "observations"
    target.mkdir(exist_ok=True)
    for name in ["inference_audit.jsonl", "control_audit.jsonl"]:
        shutil.copy2(observations / name, target / name)
    results = root / "work/DynaNav/benchmark_results" / run_id
    shutil.copytree(results, run / "benchmark_results", dirs_exist_ok=True)
    recordings = []
    for label, pattern in [("third_person", str(observations / "tp_frame_*.jpg")),
                           ("front_camera", str(observations / "retained_front_frames/front_frame_*.jpg"))]:
        frames = sorted(Path(pattern).parent.glob(Path(pattern).name))
        indices = [int(path.stem.rsplit("_", 1)[1]) for path in frames]
        if len(indices) < 2 or any(b - a != 3 for a, b in zip(indices, indices[1:])):
            raise RuntimeError("Camera frames are not a continuous three-frame cadence")
        output = run / f"{label}.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-framerate", "10",
                        "-pattern_type", "glob", "-i", pattern, "-c:v", "libx264", "-preset", "fast",
                        "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-y", str(output)],
                       check=True, timeout=120)
        for suffix, frame in [("start", frames[0]), ("middle", frames[len(frames) // 2]), ("end", frames[-1])]:
            shutil.copy2(frame, run / f"{label}_{suffix}.jpg")
        recordings.append({"file": output.name, "frame_count": len(frames), "first_frame": indices[0],
                           "last_frame": indices[-1], "playback_fps": 10,
                           "time_basis": "upstream benchmark frame counter divided by 30; not wall-clock video"})
    # Original camera bytes remain local evidence, separate from the rebuildable work copy.
    shutil.make_archive(str(run / "original_camera_frames"), "gztar", root_dir=observations)
    inference = read_jsonl(target / "inference_audit.jsonl")
    control = read_jsonl(target / "control_audit.jsonl")
    resources = read_jsonl(run / "resources.jsonl")
    fast = [r["seconds"] * 1000 for r in inference[1:]]
    gpu = [float(r["gpu_csv"].split(",")[0]) for r in resources if "gpu_csv" in r]
    original = json.loads((run / "benchmark_results/hospital_single_results_latest.json").read_text())
    summary = {
        "run_id": run_id, "model_calls": len(inference),
        "all_shapes_correct": all(r["shape"] == [1, 30, 2] for r in inference),
        "all_outputs_finite": all(r["finite"] for r in inference),
        "first_call_seconds": inference[0]["seconds"],
        "later_call_mean_ms": statistics.mean(fast), "later_call_p50_ms": statistics.median(fast),
        "later_call_p95_ms": statistics.quantiles(fast, n=100, method="inclusive")[94],
        "control_records": len(control),
        "nonzero_model_control_records": sum(r["first_inference_complete"] and not r["backing_up"]
                                               and not r["waiting_after_backup"] and (abs(r["v"]) > 1e-5 or abs(r["w"]) > 1e-5)
                                               for r in control),
        "backup_records": sum(r["backing_up"] for r in control),
        "control_wall_span_seconds": control[-1]["wall_monotonic"] - control[0]["wall_monotonic"],
        "gpu_peak_sampled_mib": max(gpu), "gpu_samples": len(gpu),
        "benchmark_episode": original["episodes"][0], "videos": recordings,
        "claim_boundary": "One Nova Carter hospital compatibility trial on Isaac Sim 5.1; not paper reproduction or Lite3 validation. Upstream crowd-path and texture errors remain."
    }
    (run / "analysis.json").write_text(json.dumps(summary, indent=2) + "\n")
    records = []
    for path in sorted(run.rglob("*")):
        if not path.is_file() or path.name == "artifact_sha256.json":
            continue
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                digest.update(block)
        records.append({"path": str(path.relative_to(run)), "bytes": path.stat().st_size, "sha256": digest.hexdigest()})
    (run / "artifact_sha256.json").write_text(json.dumps(records, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
