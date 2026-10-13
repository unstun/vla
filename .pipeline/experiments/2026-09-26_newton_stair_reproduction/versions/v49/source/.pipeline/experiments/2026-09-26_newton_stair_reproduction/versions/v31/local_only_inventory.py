"""Write versions/v31/LOCAL_ONLY_BYTES.json after the trial (v29/v30 convention).

Usage: python3 local_only_inventory.py <raw capture path relative to the experiment> ...
The tracked MP4 path is read from the V31_TRACKED_MP4 environment variable.
"""
from pathlib import Path
import hashlib, json, os, sys

E = Path(__file__).resolve().parents[2]
ROOT = E.parents[2]
STATES = ["stairs_replan", "stairs_hold", "corridor_entry_replan", "upper_corridor_hold"]
CACHES = (["versions/v31/input_refresh_contract/red_v30/probe_build", "versions/v31/input_refresh_contract/green_v31/probe_build",
           "versions/v31/attempt01/input_refresh_contract/red_v30/probe_build",
           "versions/v31/attempt01/input_refresh_contract/green_v31/probe_build"] +
          [f"versions/v31/input_refresh_contract/pending/{state}" for state in STATES] +
          ["runs/v31_saved_states01/probe_build", "runs/v31_saved_states01/breakdown_build",
           "runs/v31_saved_states02/probe_build", "runs/v31_saved_states02/breakdown_build",
           "runs/v31_native_regression01/probe_build", "runs/v31_native_regression02/probe_build",
           "runs/v31_native_regression02_attempt01_domain233/probe_build", "runs/v31_native_regression03/probe_build",
           "runs/v31_historical_full01_video01/frames", "runs/v31_historical_full01_video01/newton_stair_recorded.mp4"])
RAW = sys.argv[1:]  # physical-run raw capture paths relative to E, given after the trial
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


missing = [c for c in CACHES + RAW if not (E / c).exists()]
caches = [entry(c) for c in CACHES if (E / c).exists()]
raw = [entry(r) for r in RAW if (E / r).exists()]
count = lambda g: sum(len(e["files"]) for e in g)
size = lambda g: sum(f["bytes"] for e in g for f in e["files"])
record = {"storage_root": str(ROOT), "deletion_performed": False,
          "scope": "v31 local-only bytes, following the v29/v30 convention: regenerable contract, probe and regression "
                   "CMake builds (both candidates), the contract's pending inputs (the v30 run's own later scans and poses), "
                   "replay frames, the in-run MP4 duplicate of the tracked output copy, and the physical run's raw captures. "
                   "Sources, scripts, logs (including scan.log), receipts, reviews and results are tracked.",
          "regeneration": {
              "caches": "Each enclosing run keeps request.json, inside.sh and its source (probe_source, breakdown_source, or "
                        "refresh_probe_source with make_refresh_probe.py). Rerun it into a new directory against the named "
                        "native tree in the pinned image sha256:f7363cc3deadc2419f3527a7b9ec7bdabaa3031fd8e1b9c6cc46666ae1301bbb; "
                        "the versions/v31 manifest and runtime/scan64_input_refresh_v31/source_sha256.json fix the sources.",
              "pending": "python3 versions/v31/input_refresh_contract/prepare_pending.py <experiment root> "
                         "audits/2026-09-28_v30_stop_classes <new output dir> regenerates them from runs/v30_historical_full01 "
                         "(sensor_manifest.json and artifacts/reactive_observations.jsonl, themselves local-only raw captures "
                         "listed in versions/v30/LOCAL_ONLY_BYTES.json); pending_manifest.json (tracked) holds every file's SHA-256.",
              "frames": "Rerun scripts/render_episode.py --source-run v31_historical_full01 through scripts/run_bounded.py. "
                        "frames.json keeps per-frame hashes; the tracked MP4 is " + os.environ.get("V31_TRACKED_MP4", "(set after the render)") + ".",
              "raw": "Not regenerable. These are the recorded physical-run captures; preserve at the exact project paths."},
          "regenerable_caches": caches, "raw_artifacts": raw, "symlinks_skipped": symlinks, "missing_entries": missing,
          "raw_count": count(raw), "raw_bytes": size(raw), "cache_count": count(caches), "cache_bytes": size(caches)}
(E / "versions/v31/LOCAL_ONLY_BYTES.json").write_text(json.dumps(record, indent=2) + "\n")
print({k: record[k] for k in ("raw_count", "raw_bytes", "cache_count", "cache_bytes")}, "symlinks", len(symlinks), "missing", missing)
