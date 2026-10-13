"""Write LOCAL_ONLY_BYTES.json for the bytes this audit keeps out of Git.

Adapted from audits/2026-09-28_v30_stop_classes/make_inventory.py (entries, scope and regeneration text).
"""
from pathlib import Path
import hashlib, json, os

here = Path(__file__).resolve().parent
root = here.parents[4]
RAW = ["v33_stand/inputs", "v32_stand/inputs", "attempt03_v32_freeze_late/v32_stand/inputs",
       "attempt05_partial_inputs/v32_stand/inputs"]
CACHE = ["probe_build", "grounds/cells_fixed.f32", "grounds/entry_filled.f32", "grounds/both.f32"]
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
    "scope": "Frozen replay inputs (copies of v32_historical_full01's and v33_historical_full01's original scans, paired poses, executing spline, route, last committed window, navigation ground and planner YAML) at their corridor-entry stands, including the superseded v32 states (the 5 ms late freeze in attempt03_v32_freeze_late/ and the partial freeze Docker left in attempt05_partial_inputs/), the probe CMake build and the three counterfactual navigation grounds. Scripts, requests, logs, results, grounds.json and summaries are tracked.",
    "regeneration": {
        "inputs": "inside.sh (v33) and inside_v32.sh (v32, after review round 1) run prepare_inputs.py <experiment> <audit> [state] in the pinned image when the state's inputs are missing; the superseded v32 states came from the first version of the freezer (attempt 3) and from the interrupted re-freeze (attempt 4). Sources: runs/v32_historical_full01 and runs/v33_historical_full01 {clouds/ (local-only, versions/v32/LOCAL_ONLY_BYTES.json and versions/v33/LOCAL_ONLY_BYTES.json), sensor_manifest.json, artifacts/reactive_observations.jsonl, planner.yaml, scan.log, pct_support.log, pct_surface_ground.log}, audits/2026-09-27_pct_precision/ground_precise.f32 and audits/2026-09-27_dense_static_sampling/raw_ground.f32.",
        "probe_build": "The cmake steps in inside.sh against runtime/scan64_input_refresh_v31 in image sha256:f7363cc3… (probe source from make_probe.py).",
        "grounds": "python3 make_grounds.py (hashes in grounds/grounds.json).",
    },
    "raw_artifacts": raw,
    "regenerable_caches": cache,
    "raw_count": count(raw), "raw_bytes": size(raw),
    "cache_count": count(cache), "cache_bytes": size(cache),
    "symlinks_skipped": symlinks,
}
(here / "LOCAL_ONLY_BYTES.json").write_text(json.dumps(record, indent=2) + "\n")
print({k: record[k] for k in ("raw_count", "raw_bytes", "cache_count", "cache_bytes")}, "symlinks", len(symlinks))
