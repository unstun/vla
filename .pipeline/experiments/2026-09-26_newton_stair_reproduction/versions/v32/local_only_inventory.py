"""Write versions/v32/LOCAL_ONLY_BYTES.json and runs/v32_historical_full01_video02/LOCAL_ONLY_BYTES.json after the trial
(the v29-v31 convention).

- v32 record: K3's replay caches (per-mode clouds, rows, writer sink and factory arrays of both K3 runs), the standard
  render's frames and in-run MP4 duplicate, and the trial's raw captures (the same thirteen kinds as v31's).
- Heading-view record: that render's frames and in-run MP4 duplicate.
Everything else (sources, scripts, logs including scan.log and sensor_manifest.json, receipts, reviews, results,
K3 summaries and GC event arrays) is tracked. The diagnostic runs and the audit's benchmark are inventoried by
audits/2026-09-29_wall_clock_chain/local_only_inventory.py.
Usage: python3 local_only_inventory.py
"""
from pathlib import Path
import hashlib, json, os

E = Path(__file__).resolve().parents[2]
ROOT = E.parents[2]
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"
K3 = [f"versions/v32/gc_schedule_check/{run}{mode}/{name}"
      for run in ("", "run01/") for mode in ("none", "freeze", "collect_freeze")
      for name in ("clouds", "rows.jsonl", "writer_sink.jsonl", "factory_full_rate.npz")]
RENDER = ["runs/v32_historical_full01_video01/frames", "runs/v32_historical_full01_video01/newton_stair_recorded.mp4"]
HEADING = ["runs/v32_historical_full01_video02/frames", "runs/v32_historical_full01_video02/newton_stair_recorded.mp4"]
RAW = [f"runs/v32_historical_full01/{name}" for name in
       ("applied_channel.jsonl", "applied_sent.jsonl", "artifacts", "backend_body_callbacks.jsonl", "backend_states.jsonl",
        "clock_samples.jsonl", "clouds", "factory_full_rate.npz", "inputs", "linux_external_episode.tar", "sensor.jsonl",
        "telemetry.jsonl", "video_states.json")]
symlinks = []


def entry(relative):
    base = E / relative
    paths = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file() or p.is_symlink())
    files = []
    for p in paths:
        if p.is_symlink():
            symlinks.append({"path": str(p.relative_to(ROOT)), "target": os.readlink(p)})
            continue
        files.append({"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    return {"entry": str(base.relative_to(ROOT)), "files": files}


count = lambda g: sum(len(e["files"]) for e in g)
size = lambda g: sum(f["bytes"] for e in g for f in e["files"])
missing = [c for c in K3 + RENDER + HEADING + RAW if not (E / c).exists()]
caches = [entry(c) for c in K3 + RENDER if (E / c).exists()]
raw = [entry(r) for r in RAW if (E / r).exists()]
record = {"storage_root": str(ROOT), "deletion_performed": False,
          "scope": "v32 local-only bytes, following the v29-v31 convention: K3's replay caches (per-mode clouds, rows, "
                   "writer sink and factory arrays of K3 runs 01 and 02), the standard render's frames and in-run MP4 "
                   "duplicate, and the trial v32_historical_full01's raw captures (v31's thirteen kinds). Sources, scripts, "
                   "logs (including scan.log and sensor_manifest.json), receipts, reviews, results, K3 summaries and GC event "
                   "arrays are tracked.",
          "regeneration": {
              "k3": "Copy versions/v32/gc_schedule_check/ to a new directory inside versions/v32/ (so that the pinned "
                    "outputs are not overwritten) and run its run_gc_check.py on a quiet host (it refuses to start while "
                    "containers run). It replays v31_historical_full01's recorded commands through the same physics: the "
                    "joint states are deterministic, timings are not. summary.json and gc_events.npy of each mode are "
                    "tracked.",
              "frames": "Rerun scripts/render_episode.py --source-run v32_historical_full01 through scripts/run_bounded.py; "
                        "frames.json keeps per-frame hashes; the tracked MP4 is "
                        "output/2026-09-27_lite3_versions/v32_historical_full_odom_stale.mp4.",
              "raw": "Not regenerable. These are the recorded physical-run captures; preserve at the exact project paths. "
                     "The run used the pinned image " + IMAGE + " and the v32 manifest's sources."},
          "regenerable_caches": caches, "raw_artifacts": raw, "symlinks_skipped": symlinks,
          "missing_entries": [m for m in missing if m not in HEADING],
          "raw_count": count(raw), "raw_bytes": size(raw), "cache_count": count(caches), "cache_bytes": size(caches)}
(E / "versions/v32/LOCAL_ONLY_BYTES.json").write_text(json.dumps(record, indent=2) + "\n")
heading = [entry(c) for c in HEADING if (E / c).exists()]
heading_record = {"storage_root": str(ROOT), "deletion_performed": False,
                  "scope": "Local-only bytes of the display-only heading-view render of v32_historical_full01: rendered "
                           "frames and the in-run MP4 duplicate of the tracked output copy. frames.json (per-frame hashes), "
                           "heading_camera.json, result.json, process.json, request.json, run.log, video_receipt.json and the "
                           "executed scripts are tracked.",
                  "regeneration": "python3 scripts/run_bounded.py --run-id <new id> --deadline 1800 -- <newton venv python> "
                                  "<experiment>/scripts/render_heading_view.py --source-run v32_historical_full01; the tracked "
                                  "MP4 is output/2026-09-27_lite3_versions/v32_historical_full_odom_stale_heading_view.mp4.",
                  "regenerable_caches": heading, "cache_count": count(heading), "cache_bytes": size(heading)}
(E / "runs/v32_historical_full01_video02/LOCAL_ONLY_BYTES.json").write_text(json.dumps(heading_record, indent=2) + "\n")
print({k: record[k] for k in ("raw_count", "raw_bytes", "cache_count", "cache_bytes")}, "heading",
      {k: heading_record[k] for k in ("cache_count", "cache_bytes")}, "symlinks", len(symlinks), "missing", missing)
