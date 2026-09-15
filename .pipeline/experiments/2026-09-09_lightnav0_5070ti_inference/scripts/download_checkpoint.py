"""Acquire the pinned LightNav-0 checkpoint with resumable curl and full verification.

Every sibling listed in setup/model_source.json (pinned HF revision) is downloaded to
<out_dir>/<rfilename>. LFS files are checked against the upstream LFS SHA-256; plain files
are checked against the upstream git blob id (SHA-1 over "blob <size>\\0" + bytes). A
manifest with bytes and SHA-256 for every file is written to <manifest_path>.

Usage: download_checkpoint.py <model_source.json> <out_dir> <manifest_path> [--verify-only]
"""
import concurrent.futures
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

VERIFY_ONLY = "--verify-only" in sys.argv
argv = [a for a in sys.argv[1:] if not a.startswith("--")]
source = json.loads(Path(argv[0]).read_text())
out_dir = Path(argv[1]).resolve()
manifest_path = Path(argv[2]).resolve()
repo, revision = source["id"], source["sha"]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def git_blob_sha1(path: Path, size: int) -> str:
    h = hashlib.sha1()
    h.update(f"blob {size}\0".encode())
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def acquire(item: dict) -> dict:
    rel, size = item["rfilename"], int(item["size"])
    target = out_dir / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    expected_lfs = (item.get("lfs") or {}).get("sha256")
    started = time.time()
    if not target.exists() or target.stat().st_size != size:
        if VERIFY_ONLY:
            raise RuntimeError(f"missing or wrong size in verify-only mode: {rel}")
        part = target.with_name(target.name + ".part")
        url = f"https://huggingface.co/{repo}/resolve/{revision}/{quote(rel)}"
        print(json.dumps({"event": "download_start", "file": rel, "bytes": size}), flush=True)
        for attempt in range(6):
            result = subprocess.run(
                ["curl", "--fail", "--location", "--silent", "--show-error",
                 "--connect-timeout", "20", "--max-time", "3000", "--speed-time", "60",
                 "--speed-limit", "20000", "--continue-at", "-", "--output", str(part), url],
                capture_output=True, text=True, timeout=3030)
            if result.returncode == 0 and part.exists() and part.stat().st_size == size:
                part.replace(target)
                break
            print(json.dumps({"event": "retry", "file": rel, "attempt": attempt + 1,
                              "rc": result.returncode, "stderr": result.stderr[-500:],
                              "have": part.stat().st_size if part.exists() else 0}), flush=True)
            time.sleep(5)
        else:
            raise RuntimeError(f"download retries exhausted: {rel}")
    actual_size = target.stat().st_size
    if actual_size != size:
        raise RuntimeError(f"size mismatch {rel}: {actual_size} != {size}")
    digest = sha256_of(target)
    row = {"path": rel, "bytes": actual_size, "sha256": digest, "repo": repo, "revision": revision,
           "upstream_lfs_sha256": expected_lfs, "upstream_blob_id": item.get("blobId")}
    if expected_lfs:
        if digest != expected_lfs:
            raise RuntimeError(f"LFS sha256 mismatch {rel}: {digest} != {expected_lfs}")
        row["verified_by"] = "lfs_sha256"
    else:
        blob = git_blob_sha1(target, actual_size)
        if blob != item.get("blobId"):
            raise RuntimeError(f"git blob mismatch {rel}: {blob} != {item.get('blobId')}")
        row["verified_by"] = "git_blob_sha1"
    print(json.dumps({"event": "verified", "file": rel, "bytes": actual_size,
                      "seconds": round(time.time() - started, 1)}), flush=True)
    return row


t0 = time.time()
items = sorted(source["siblings"], key=lambda s: -int(s["size"]))
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    rows = list(pool.map(acquire, items))
manifest = {"repo": repo, "revision": revision, "out_dir": str(out_dir),
            "file_count": len(rows), "total_bytes": sum(r["bytes"] for r in rows),
            "wall_seconds": round(time.time() - t0, 1),
            "verify_only": VERIFY_ONLY, "files": sorted(rows, key=lambda r: r["path"])}
manifest_path.parent.mkdir(parents=True, exist_ok=True)
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"event": "CHECKPOINT_COMPLETE", "files": len(rows),
                  "total_bytes": manifest["total_bytes"], "wall_seconds": manifest["wall_seconds"]}), flush=True)
