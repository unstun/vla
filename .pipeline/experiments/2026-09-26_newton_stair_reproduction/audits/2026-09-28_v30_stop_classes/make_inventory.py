"""Write LOCAL_ONLY_BYTES.json for the bytes this audit keeps out of Git.

Adapted from audits/2026-09-28_v29_landing_stall/make_inventory.py (entries, scope and regeneration text).
"""
from pathlib import Path
import hashlib, json, os

here = Path(__file__).resolve().parent
root = here.parents[4]
RAW = ["stairs_replan/inputs", "stairs_hold/inputs", "corridor_entry_replan/inputs", "upper_corridor_hold/inputs"]
CACHE = ["probe_build", "candidate_probe_build"]
symlinks = []


def entry(relative):
    base = here / relative
    paths = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file() or p.is_symlink())
    files = []
    for p in paths:
        if p.is_symlink():
            symlinks.append({"path": str(p.relative_to(root)), "target": os.readlink(p)})
            continue
        files.append({"path": str(p.relative_to(root)), "bytes": p.stat().st_size,
                      "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    return {"entry": str(base.relative_to(root)), "files": files}


raw = [entry(r) for r in RAW]
cache = [entry(c) for c in CACHE]
count = lambda group: sum(len(e["files"]) for e in group)
size = lambda group: sum(f["bytes"] for e in group for f in e["files"])
record = {
    "storage_root": str(root),
    "deletion_performed": False,
    "scope": "Frozen replay inputs (copies of v30_historical_full01's original scans, paired poses, executing spline, route, last committed window, grounds and planner YAML) for four emergency stops, and the two probe CMake builds. Scripts, requests, timeline, logs, results, candidate lists and summaries are tracked.",
    "regeneration": {
        "inputs": "inside.sh runs prepare_inputs.py <experiment> <audit> in the pinned image when upper_corridor_hold/inputs is missing (needs timeline.json from timeline.py). Sources: runs/v30_historical_full01/{clouds/ (local-only, versions/v30/LOCAL_ONLY_BYTES.json), sensor_manifest.json, artifacts/reactive_observations.jsonl, planner.yaml, scan.log, pct_support.log, pct_surface_ground.log}, audits/2026-09-27_pct_precision/ground_precise.f32 and audits/2026-09-27_dense_static_sampling/raw_ground.f32.",
        "probe_builds": "The cmake steps in inside.sh and inside_candidates.sh against runtime/scan62_support_evidence_v30 in image sha256:f7363cc3\u2026 (probe sources from make_probe.py and make_candidate_probe.py).",
    },
    "raw_artifacts": raw,
    "regenerable_caches": cache,
    "raw_count": count(raw), "raw_bytes": size(raw),
    "cache_count": count(cache), "cache_bytes": size(cache),
    "symlinks_skipped": symlinks,
}
(here / "LOCAL_ONLY_BYTES.json").write_text(json.dumps(record, indent=2) + "\n")
print({k: record[k] for k in ("raw_count", "raw_bytes", "cache_count", "cache_bytes")}, "symlinks", len(symlinks))
