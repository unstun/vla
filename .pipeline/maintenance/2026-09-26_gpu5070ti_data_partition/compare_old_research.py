#!/usr/bin/env python3
"""Compare old-volume hashes with actual Mac files and historical cloud manifests."""

import collections
import gzip
import hashlib
import json
import os
from pathlib import Path
import time


OUT = Path(__file__).parent / "data_audit"
ARCHIVE = Path("/Users/sun/tongbu/study/phdproject/machine-dog/artifacts/2026-09-12_dqn_google_drive_offload")
with gzip.open(OUT / "old_research_manifest.jsonl.gz", "rt") as stream:
    old = [json.loads(line) for line in stream]
regular = [row for row in old if row.get("type") == "file"]
by_key = collections.defaultdict(list)
for row in regular:
    by_key[(Path(row["path"]).name.casefold(), row["size"])].append(row)

historical = collections.defaultdict(set)
with (ARCHIVE / "dqn10-bulk-local.jsonl").open() as stream:
    for line in stream:
        item = json.loads(line)
        if item.get("sha256"):
            historical[item["sha256"]].add("DQN10:" + item["path"])
for path in (ARCHIVE / "dqn9_first_batch").rglob("source-manifest.json"):
    for item in json.loads(path.read_text()).get("files", []):
        if item.get("sha256"):
            historical[item["sha256"]].add("DQN9:" + item["path"])
snapshot = {}
for path in (ARCHIVE / "full_tree").glob("*/manifest.json"):
    for item in json.loads(path.read_text()).get("snapshot", []):
        if item[1] == "file":
            snapshot[item[0]] = item[4]

roots = [Path("/Users/sun/tongbu/study"), Path("/Users/sun/Documents"),
         Path("/Users/sun/Downloads"), Path("/Users/sun/Desktop")]
prune = {".git", "node_modules", ".venv", "venv", "miniconda3", "anaconda3",
         "__pycache__", ".cache", ".tox", ".mypy_cache", ".pytest_cache"}
actual = collections.defaultdict(list)
errors = []
candidates = scanned = hashed_bytes = 0
last = time.monotonic()
for root in roots:
    if not root.exists():
        continue
    for directory, dirs, files in os.walk(root, followlinks=False,
                                         onerror=lambda error: errors.append(str(error))):
        dirs[:] = [name for name in dirs if name not in prune]
        for name in files:
            path = Path(directory) / name
            try:
                if path.is_symlink():
                    continue
                before = path.stat()
                scanned += 1
                if (name.casefold(), before.st_size) not in by_key:
                    continue
                candidates += 1
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                        digest.update(chunk)
                after = path.stat()
                if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                    errors.append("Changed while reading: " + str(path))
                    continue
                actual[digest.hexdigest()].append(str(path))
                hashed_bytes += before.st_size
            except OSError as error:
                errors.append(str(error))
            if time.monotonic() - last > 25:
                print(json.dumps({"local_candidates_hashed": candidates,
                                  "GiB": round(hashed_bytes / 2**30, 2)}), flush=True)
                last = time.monotonic()

groups = collections.defaultdict(lambda: collections.defaultdict(lambda: {"files": 0, "bytes": 0}))
details = []
for row in regular:
    path = row["path"]
    key = "/".join(Path(path).parts[:2]) if path.startswith("dqn/") else Path(path).parts[0]
    digest = row["sha256"]
    local = actual.get(digest, [])
    previous = sorted(historical.get(digest, set()))
    archive_path = path.removeprefix("dqn/")
    path_size = snapshot.get(archive_path) == row["size"]
    status = ("local_sha256_match" if local else "historical_archive_sha256_match" if previous
              else "historical_path_size_only" if path_size else "no_match_found")
    groups[key][status]["files"] += 1
    groups[key][status]["bytes"] += row["size"]
    details.append({"old_path": path, "bytes": row["size"], "sha256": digest,
                    "status": status, "local_matches": local[:4],
                    "historical_hash_matches": previous[:4]})
with gzip.open(OUT / "comparison_details.jsonl.gz", "wt", encoding="utf-8") as stream:
    for row in details:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
summary = {"groups": groups, "old_regular_files": len(regular),
           "local_files_scanned": scanned, "local_candidates_hashed": candidates,
           "local_bytes_hashed": hashed_bytes, "local_search_roots": [str(p) for p in roots],
           "local_pruned_directories": sorted(prune), "errors": errors,
           "largest_unmatched": sorted([r for r in details if r["status"] == "no_match_found"],
                                        key=lambda r: r["bytes"], reverse=True)[:30],
           "claim_boundary": "Local matches have identical SHA-256. Historical archive matches do not verify current cloud availability. Path/size-only matches are not content equality. Local candidate selection used basename and size; renamed files, Git objects, compressed archives, and unscanned paths may contain additional copies."}
(OUT / "COMPARISON.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"groups": groups, "local_candidates_hashed": candidates,
                  "errors": len(errors)}, ensure_ascii=False, indent=2))
