"""Extract only frozen-MIP scenes from the authorized official ZIP using ranges.

Reuse the project's previously tested strict HTTP range reader; ZIP CRC verifies
decompressed bytes and the output manifest records SHA-256 for subsequent reuse.
"""
import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
import shutil
import time
import zipfile
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath

URL = "https://kaldir.vc.in.tum.de/matterport/v1/tasks/mp3d_habitat.zip"
ARCHIVE_BYTES = 16085306031  # live Content-Range preflight, 2026-09-16


class RangeFile(io.RawIOBase):
    def __init__(self, size, read_range):
        self.size = size
        self.position = 0
        self.read_range = read_range

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        bases = {0: 0, 1: self.position, 2: self.size}
        if whence not in bases:
            raise ValueError("Invalid seek origin")
        position = bases[whence] + offset
        if not 0 <= position <= self.size:
            raise ValueError("Seek outside archive")
        self.position = position
        return position

    def read(self, size=-1):
        size = self.size - self.position if size < 0 else size
        size = min(size, self.size - self.position)
        if size == 0:
            return b""
        block = self.read_range(self.position, self.position + size - 1)
        if len(block) != size:
            raise RuntimeError("Incomplete archive range")
        self.position += size
        return block


def selected_members(infos, scenes):
    result = []
    for info in infos:
        path = PurePosixPath(info.filename)
        if info.is_dir():
            continue
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe archive path: " + info.filename)
        if len(path.parts) >= 3 and path.parts[0] == "mp3d" and path.parts[1] in scenes:
            result.append(info)
    found = {PurePosixPath(i.filename).parts[1] for i in result if i.filename.endswith(".glb")}
    if found != scenes:
        raise ValueError("Required scene missing from archive: " + str(sorted(scenes - found)))
    return result


def file_checks(path):
    digest, crc, size = hashlib.sha256(), 0, 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
            crc = zlib.crc32(block, crc)
            size += len(block)
    return size, crc, digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--range-helper", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.workers <= 10:
        parser.error("workers must be 1..10")
    root = args.root.resolve()
    if not (root / "configs/MP3D_AUTHORIZED.txt").is_file():
        raise RuntimeError("Dataset authorization record missing")
    spec = importlib.util.spec_from_file_location("range_reference", args.range_helper)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    archive_item = {"url": URL, "bytes": ARCHIVE_BYTES}

    def read_range(start, end):
        for attempt in range(3):
            try:
                return helper.read_range(archive_item, start, end)
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)

    source = root / "source/AgentCanvas"
    split = source / "coding-agent/bridges/splits/r2r_rand100/rand100.json.gz"
    episodes = json.loads(gzip.decompress(split.read_bytes()))["episodes"]
    scenes = {PurePosixPath(e["scene_id"]).parts[1] for e in episodes}
    with zipfile.ZipFile(RangeFile(ARCHIVE_BYTES, read_range)) as archive:
        members = selected_members(archive.infolist(), scenes)
    plan = {"url": URL, "archive_bytes": ARCHIVE_BYTES,
            "split_sha256": hashlib.sha256(split.read_bytes()).hexdigest(),
            "episode_count": len(episodes), "scenes": sorted(scenes),
            "compressed_bytes": sum(i.compress_size for i in members),
            "extracted_bytes": sum(i.file_size for i in members),
            "members": [{"path": i.filename, "bytes": i.file_size,
                         "compressed_bytes": i.compress_size, "crc32": i.CRC} for i in members]}
    setup = root / "setup"
    setup.mkdir(exist_ok=True)
    (setup / "mp3d_subset_plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps({k: v for k, v in plan.items() if k != "members"}), flush=True)
    if args.plan_only:
        return
    if shutil.disk_usage(root).free < plan["extracted_bytes"] + 10 * 1024**3:
        raise RuntimeError("Insufficient disk for selected scenes and 10 GiB reserve")
    destination = source / "data/habitat/scene_datasets"
    destination.mkdir(parents=True, exist_ok=True)

    def fetch(info):
        target = destination / info.filename
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            size, crc, digest = file_checks(target)
            if size != info.file_size or crc != info.CRC:
                raise RuntimeError("Existing scene file failed integrity check: " + info.filename)
        else:
            temporary = target.with_name(target.name + ".part")
            with zipfile.ZipFile(RangeFile(ARCHIVE_BYTES, read_range)) as archive:
                with archive.open(info.filename) as stream, temporary.open("wb") as output:
                    shutil.copyfileobj(stream, output, 4 * 1024 * 1024)
            size, crc, digest = file_checks(temporary)
            if size != info.file_size or crc != info.CRC:
                raise RuntimeError("Extracted scene failed ZIP integrity: " + info.filename)
            os.replace(temporary, target)
        return {"path": info.filename, "bytes": size, "crc32": crc, "sha256": digest}

    records = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(fetch, i) for i in members]):
            record = future.result()
            records.append(record)
            (setup / "mp3d_subset_verified.json").write_text(json.dumps(records, indent=2) + "\n")
            print("VERIFIED", record["path"], record["bytes"], flush=True)
    compatibility = source / "data/scene_datasets/mp3d"
    compatibility.parent.mkdir(parents=True, exist_ok=True)
    if not compatibility.exists() and not compatibility.is_symlink():
        compatibility.symlink_to("../habitat/scene_datasets/mp3d")
    (setup / "mp3d_subset_complete.json").write_text(json.dumps({
        "files": len(records), "scenes": len(scenes), "episode_count": len(episodes),
        "status": "all_selected_files_crc_and_sha256_verified"}, indent=2) + "\n")
    print("ALL_SELECTED_SCENES_VERIFIED", len(records), flush=True)


if __name__ == "__main__":
    main()
