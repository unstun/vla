"""Write audits/2026-09-29_wall_clock_chain/LOCAL_ONLY_BYTES.json (the v29-v31 convention).

Local-only: the diagnostic runs' raw captures (the same kinds of files the trials keep local-only) and the
benchmark's per-run outputs (clouds, step rows). Everything else in the audit and the runs (scripts, logs
under 2 MB, reviews, summaries, analysis JSON, diagnostics/*.npy summaries named below) stays tracked.
Usage: python3 local_only_inventory.py <entry relative to the experiment> ...
"""
from pathlib import Path
import hashlib, json, os, sys

H = Path(__file__).resolve().parent
E = H.parents[1]
ROOT = E.parents[2]
symlinks = []


def entry(relative):
    base = E / relative
    paths = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file() or p.is_symlink())
    files = []
    for p in paths:
        if p.is_symlink():
            symlinks.append({"path": str(p.relative_to(ROOT)), "target": os.readlink(p)})
            continue
        files.append({"path": str(p.relative_to(ROOT)), "bytes": p.stat().st_size,
                      "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
    return {"entry": str(base.relative_to(ROOT)), "files": files}


entries = sys.argv[1:]
missing = [e for e in entries if not (E / e).exists()]
recorded = [entry(e) for e in entries if (E / e).exists()]
record = {"storage_root": str(ROOT), "deletion_performed": False,
          "scope": "Raw captures of the diagnostic runs diag_v31_clock01-04 and diag_v32_* (telemetry, sensor, clock, "
                   "applied-channel and backend-state streams, clouds, video states, factory arrays, per-substep and GC "
                   "arrays, container-side binary records) and the replay benchmark's per-run clouds and rows.",
          "regeneration": "Not regenerable byte for byte: live runs depend on host timing. The benchmark outputs are "
                          "regenerable with run_bench.py (deterministic physics; timings differ). Preserve at the exact "
                          "project paths.",
          "entries": recorded, "symlinks_skipped": symlinks, "missing_entries": missing,
          "file_count": sum(len(e["files"]) for e in recorded),
          "bytes": sum(f["bytes"] for e in recorded for f in e["files"])}
(H / "LOCAL_ONLY_BYTES.json").write_text(json.dumps(record, indent=2) + "\n")
print({k: record[k] for k in ("file_count", "bytes")}, "symlinks", len(symlinks), "missing", missing)
