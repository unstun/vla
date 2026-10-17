#!/usr/bin/env python3
"""Download checksummed rescue chunks, then assemble the exact original archive."""

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


base = Path(__file__).resolve().parent
manifest = json.loads((base / "RESCUE_PARTS.json").read_text())
source = json.loads((base / "RESCUE_REMOTE.json").read_text())
remote_dir = "/home/sun/storage_maintenance/2026-09-26_data_partition/rescue_transfer_parts"
assert manifest["parts_directory"] == remote_dir
assert manifest["total_bytes"] == source["archive_bytes"]
assert len({r["name"] for r in manifest["parts"]}) == len(manifest["parts"])
folder = base / "rescue_backup/chunks"
folder.mkdir(parents=True, exist_ok=True)


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def transfer(row):
    assert re.fullmatch(r"part-[0-9]{3}", row["name"])
    path = folder / row["name"]
    if path.exists() and path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]:
        return row
    last_error = ""
    for attempt in range(3):
        result = subprocess.run(["rsync", "-t", "--partial", "--ignore-times",
                                 f"gpu5070ti:{remote_dir}/{row['name']}", str(path)],
                                capture_output=True, text=True)
        if result.returncode == 0 and path.stat().st_size == row["bytes"] and sha(path) == row["sha256"]:
            return row
        last_error = result.stderr
    raise RuntimeError(f"Chunk transfer failed: {row['name']}: {last_error}")


completed = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    pending = {pool.submit(transfer, row) for row in manifest["parts"]}
    while pending:
        done, pending = concurrent.futures.wait(pending, timeout=25,
                                                return_when=concurrent.futures.FIRST_COMPLETED)
        for future in done:
            future.result()
            completed += 1
        received = sum(p.stat().st_size for p in folder.iterdir() if p.is_file())
        print(json.dumps({"complete_chunks": completed, "total_chunks": len(manifest["parts"]),
                          "received_GiB": round(received / 2**30, 3)}), flush=True)
assembly = base / "rescue_backup/old-research-selective.tar.zst.assembling"
with assembly.open("xb") as target:
    for row in manifest["parts"]:
        with (folder / row["name"]).open("rb") as stream:
            for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                target.write(chunk)
    target.flush()
    os.fsync(target.fileno())
assert assembly.stat().st_size == source["archive_bytes"]
assert sha(assembly) == source["archive_sha256"]
archive = base / "rescue_backup/old-research-selective.tar.zst"
assert not archive.is_symlink()
assembly.replace(archive)
print(json.dumps({"status": "transferred_and_archive_hash_matched", "archive": str(archive),
                  "bytes": archive.stat().st_size, "sha256": source["archive_sha256"]}), flush=True)
