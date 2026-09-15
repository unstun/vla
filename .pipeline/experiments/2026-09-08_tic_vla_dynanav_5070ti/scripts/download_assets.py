"""Download the previously reviewed pinned assets and verify every byte hash."""

import hashlib
import json
import os
import shutil
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

DOWNLOAD_CHUNK_BYTES = 32 * 1024 * 1024


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_range(item, position, end):
    request = urllib.request.Request(item["url"], headers={
        "User-Agent": "TIC-VLA-pinned-smoke/1.0",
        "Range": f"bytes={position}-{end}",
    })
    with urllib.request.urlopen(request, timeout=45) as response:
        expected_range = f"bytes {position}-{end}/{item['bytes']}"
        if response.status != 206 or response.headers.get("Content-Range") != expected_range:
            raise RuntimeError(f"Unexpected range response: status={response.status}, range={response.headers.get('Content-Range')}")
        block = response.read(end - position + 2)
    if len(block) != end - position + 1:
        raise RuntimeError(f"Truncated range: received {len(block)} bytes, expected {end-position+1}")
    return block


def download_in_ranges(item, partial, workers=1):
    """Resume verified ranges; optionally fetch disjoint pieces concurrently."""
    position = partial.stat().st_size if partial.exists() else 0
    if position > item["bytes"]:
        raise RuntimeError("Existing partial file is larger than the declared asset")
    if not 1 <= workers <= 4:
        raise ValueError("Download workers must be between 1 and 4")
    if workers > 1 and position < item["bytes"]:
        pieces = partial.with_name(partial.name + ".chunks")
        pieces.mkdir(exist_ok=True)
        jobs = [(start, min(start + DOWNLOAD_CHUNK_BYTES, item["bytes"]) - 1)
                for start in range(position, item["bytes"], DOWNLOAD_CHUNK_BYTES)]

        def fetch(job):
            start, end = job
            path = pieces / f"{start}-{end}.bin"
            if path.is_file() and path.stat().st_size == end - start + 1:
                return path
            block = read_range(item, start, end)
            temporary = path.with_suffix(".writing")
            temporary.write_bytes(block)
            os.replace(temporary, path)
            return path

        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(fetch, job): job for job in jobs}
            errors = []
            for future in as_completed(futures):
                try:
                    path = future.result()
                    print("RANGE_VERIFIED", item["destination"], path.name, flush=True)
                except Exception as error:
                    errors.append(error)
            if errors:
                raise RuntimeError(f"{len(errors)} ranges failed; completed pieces retained: {errors[0]}")
        for start, end in jobs:
            current_size = partial.stat().st_size if partial.exists() else 0
            if current_size != start:
                raise RuntimeError("Partial file changed during parallel acquisition")
            with partial.open("ab") as output, (pieces / f"{start}-{end}.bin").open("rb") as source:
                shutil.copyfileobj(source, output, length=8 * 1024 * 1024)
        # The assembled partial retains all bytes until the caller verifies SHA-256.
        shutil.rmtree(pieces)
        return
    while position < item["bytes"]:
        end = min(position + DOWNLOAD_CHUNK_BYTES, item["bytes"]) - 1
        block = read_range(item, position, end)
        with partial.open("ab") as output:
            output.write(block)
        position = end + 1
        print("RANGE_PROGRESS", item["destination"], position, "/", item["bytes"], flush=True)


def main():
    root = Path(sys.argv[1]).resolve()
    manifest = json.loads((root / "manifests/official_assets.json").read_text())
    base = manifest["base_model"]
    entries = []
    for item in base["files"]:
        entries.append({**item, "destination": "models/InternVL3-1B/" + item["path"],
                        "url": f"https://huggingface.co/{base['repo_id']}/resolve/{base['revision']}/{item['path']}"})
    ckpt = manifest["checkpoint"]
    entries.append({**ckpt, "destination": "checkpoints/" + ckpt["filename"]})
    records = []
    for item in entries:
        target = root / item["destination"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.is_file() and target.stat().st_size == item["bytes"] and sha256(target) == item["sha256"]:
            print("VERIFIED_EXISTING", item["destination"], flush=True)
        else:
            if shutil.disk_usage(root).free < item["bytes"] + 10 * 1024**3:
                raise RuntimeError("Download would violate the 10 GiB free-disk reserve")
            partial = target.with_name(target.name + ".partial")
            error = None
            for attempt in range(1, 4):
                started = time.monotonic()
                try:
                    print("DOWNLOADING", item["destination"], item["bytes"], "attempt", attempt, flush=True)
                    if item["bytes"] >= 64 * 1024 * 1024:
                        download_in_ranges(item, partial, workers=int(os.environ.get("TICVLA_DOWNLOAD_WORKERS", "1")))
                    else:
                        request = urllib.request.Request(item["url"], headers={"User-Agent": "TIC-VLA-pinned-smoke/1.0"})
                        with urllib.request.urlopen(request, timeout=45) as response, partial.open("wb") as output:
                            shutil.copyfileobj(response, output, length=8 * 1024 * 1024)
                    observed_bytes = partial.stat().st_size
                    observed_sha256 = sha256(partial)
                    if observed_bytes != item["bytes"] or observed_sha256 != item["sha256"]:
                        raise RuntimeError(f"Asset mismatch: bytes={observed_bytes}, sha256={observed_sha256}; expected bytes={item['bytes']}, sha256={item['sha256']}")
                    os.replace(partial, target)
                    print("VERIFIED_DOWNLOAD", item["destination"], "seconds", round(time.monotonic() - started, 3), flush=True)
                    error = None
                    break
                except Exception as exc:
                    error = exc
                    print("DOWNLOAD_FAILED", item["destination"], repr(exc), flush=True)
            if error is not None:
                raise error
        records.append({"path": item["destination"], "bytes": item["bytes"],
                        "sha256": item["sha256"], "url": item["url"]})
        (root / "manifests/download_verified.json").write_text(json.dumps(records, indent=2) + "\n")
    print("ALL_ASSETS_VERIFIED", len(records), flush=True)


if __name__ == "__main__":
    main()
