"""Write versions/v33/LOCAL_ONLY_BYTES.json and runs/v33_historical_full01_video02/LOCAL_ONLY_BYTES.json after the
trial (the v29-v32 convention).

- v33 record: the standard render's frames and in-run MP4 duplicate, and the trial's raw captures (the same thirteen
  kinds as v31's and v32's). The trial ran on gpu5070ti; these are the copies on this MacBook, verified against the
  run's own manifest (versions/v33/host/v33_historical_full01_SHA256SUMS.txt).
- Heading-view record: that render's frames and in-run MP4 duplicate.
Everything else (sources, scripts, logs including scan.log and sensor_manifest.json, the host files, receipts, reviews,
analysis outputs and results) is tracked. The port's own runs are inventoried by
hosts/2026-09-29_gpu5070ti/local_only_inventory.py.
Usage: python3 local_only_inventory.py
"""
from pathlib import Path
import hashlib, json, os

E = Path(__file__).resolve().parents[2]
ROOT = E.parents[2]
IMAGE = "sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb"
RENDER = ["runs/v33_historical_full01_video01/frames", "runs/v33_historical_full01_video01/newton_stair_recorded.mp4"]
HEADING = ["runs/v33_historical_full01_video02/frames", "runs/v33_historical_full01_video02/newton_stair_recorded.mp4"]
RAW = [f"runs/v33_historical_full01/{name}" for name in
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
missing = [c for c in RENDER + HEADING + RAW if not (E / c).exists()]
caches = [entry(c) for c in RENDER if (E / c).exists()]
raw = [entry(r) for r in RAW if (E / r).exists()]
record = {"storage_root": str(ROOT), "deletion_performed": False,
          "scope": "v33 local-only bytes, following the v29-v32 convention: the standard render's frames and in-run MP4 "
                   "duplicate, and the trial v33_historical_full01's raw captures (v31's thirteen kinds), copied from "
                   "gpu5070ti and verified against the run's own manifest. Sources, scripts, logs (including scan.log and "
                   "sensor_manifest.json), the host files, receipts, reviews, analysis outputs and results are tracked.",
          "regeneration": {
              "frames": "Rerun scripts/render_episode.py --source-run v33_historical_full01 through scripts/run_bounded.py; "
                        "frames.json keeps per-frame hashes; the tracked MP4 is in output/2026-09-27_lite3_versions/ "
                        "(versions/v33/video_receipt.json).",
              "raw": "Not regenerable. These are the recorded physical-run captures of the trial on gpu5070ti; preserve at "
                     "the exact project paths. The execution copy ~/vla_exec/vla on gpu5070ti holds the originals until "
                     "Dr Sun decides otherwise. The run used the pinned image " + IMAGE + " and the v33 manifest's "
                     "sources."},
          "regenerable_caches": caches, "raw_artifacts": raw, "symlinks_skipped": symlinks,
          "missing_entries": [m for m in missing if m not in HEADING],
          "raw_count": count(raw), "raw_bytes": size(raw), "cache_count": count(caches), "cache_bytes": size(caches)}
(E / "versions/v33/LOCAL_ONLY_BYTES.json").write_text(json.dumps(record, indent=2) + "\n")
heading = [entry(c) for c in HEADING if (E / c).exists()]
heading_record = {"storage_root": str(ROOT), "deletion_performed": False,
                  "scope": "Local-only bytes of the display-only heading-view render of v33_historical_full01: rendered "
                           "frames and the in-run MP4 duplicate of the tracked output copy. frames.json (per-frame hashes), "
                           "heading_camera.json, result.json, process.json, request.json, run.log, video_receipt.json and the "
                           "executed scripts are tracked.",
                  "regeneration": "python3 scripts/run_bounded.py --run-id <new id> --deadline 1800 -- <newton venv python> "
                                  "<experiment>/scripts/render_heading_view.py --source-run v33_historical_full01; the tracked "
                                  "MP4 is in output/2026-09-27_lite3_versions/ (that run's video_receipt.json).",
                  "regenerable_caches": heading, "cache_count": count(heading), "cache_bytes": size(heading)}
(E / "runs/v33_historical_full01_video02/LOCAL_ONLY_BYTES.json").write_text(json.dumps(heading_record, indent=2) + "\n")
print({k: record[k] for k in ("raw_count", "raw_bytes", "cache_count", "cache_bytes")}, "heading",
      {k: heading_record[k] for k in ("cache_count", "cache_bytes")}, "symlinks", len(symlinks), "missing", missing)
