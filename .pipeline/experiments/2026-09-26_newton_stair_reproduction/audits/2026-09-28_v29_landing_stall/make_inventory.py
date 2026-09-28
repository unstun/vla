"""Write LOCAL_ONLY_BYTES.json for the bytes this audit keeps out of Git."""
from pathlib import Path
import hashlib, json, os

here = Path(__file__).resolve().parent
root = here.parents[4]
RAW = ["landing/inputs", "onset/inputs"]
CACHE = ["probe_build", "oracle_probe_build", "support_map/support_map", "support_map/all_cells.csv"]
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
    "scope": "Frozen replay inputs (copies of v29_historical_full01's original scans, paired poses, spline, route and ground), the two probe CMake builds, the support-map binary and its full-map dump. Scripts, requests, logs, results, breakdowns, the figure and its data are tracked.",
    "regeneration": {
        "inputs": "inside.sh runs prepare_inputs.py <experiment> <audit> in the pinned image when landing/inputs is missing. Sources: runs/v29_historical_full01/{clouds/ (local-only, versions/v29/LOCAL_ONLY_BYTES.json), sensor_manifest.json, artifacts/reactive_observations.jsonl, planner.yaml, scan.log} and audits/2026-09-27_pct_precision/ground_precise.f32.",
        "probe_builds": "The cmake steps in inside.sh and oracle_inside.sh against runtime/scan61_sensor_column_v29 in image sha256:f7363cc3…",
        "support_map": "clang++ -std=c++17 -O2 -I runtime/scan61_sensor_column_v29/src/plan_env/include support_map.cpp -o support_map; ./support_map <ground_precise.f32> all_cells.csv -1000 1000 -1000 1000",
    },
    "raw_artifacts": raw,
    "regenerable_caches": cache,
    "raw_count": count(raw), "raw_bytes": size(raw),
    "cache_count": count(cache), "cache_bytes": size(cache),
    "symlinks_skipped": symlinks,
}
(here / "LOCAL_ONLY_BYTES.json").write_text(json.dumps(record, indent=2) + "\n")
print({k: record[k] for k in ("raw_count", "raw_bytes", "cache_count", "cache_bytes")}, "symlinks", len(symlinks))
