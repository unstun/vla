#!/usr/bin/env python3
"""Build the approved selective rescue; independently verify every archive member."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import socket
import stat
import subprocess
import sys
import tarfile
import time


BASE = Path(__file__).resolve().parent
OLD_UUID = "89dc617c-0cf0-4757-a997-8e3c15e79b5a"


def require(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_selection():
    plan = json.loads((BASE / "RESCUE_PLAN.json").read_text())
    source = BASE / "RESCUE_SELECTION.jsonl"
    require(digest(source) == plan["selection_sha256"], "Selection manifest changed")
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    require(len(rows) == plan["selected_entries"], "Selection count mismatch")
    for row in rows:
        p = PurePosixPath(row["path"])
        require(not p.is_absolute() and ".." not in p.parts, "Unsafe archive path")
        require(row["type"] in {"file", "symlink"}, "Unexpected entry type")
    require(len({r["path"] for r in rows}) == len(rows), "Duplicate selection paths")
    return plan, rows


class CheckedReader:
    def __init__(self, stream):
        self.stream = stream
        self.hash = hashlib.sha256()

    def read(self, count=-1):
        data = self.stream.read(count)
        self.hash.update(data)
        return data


def pack(root, rows, archive):
    partial = archive.with_suffix(archive.suffix + ".partial")
    require(not archive.exists() and not partial.exists(), "Backup already exists")
    count = total = 0
    last = time.monotonic()
    with partial.open("xb") as destination:
        compressor = subprocess.Popen(["zstd", "-T2", "-3", "-c"], stdin=subprocess.PIPE,
                                      stdout=destination, stderr=subprocess.PIPE)
        try:
            with tarfile.open(fileobj=compressor.stdin, mode="w|", format=tarfile.PAX_FORMAT) as target:
                for row in rows:
                    source = root / row["path"]
                    s = source.lstat()
                    info = tarfile.TarInfo(row["path"])
                    info.mode, info.uid, info.gid, info.mtime = stat.S_IMODE(s.st_mode), s.st_uid, s.st_gid, s.st_mtime
                    if row["type"] == "symlink":
                        require(stat.S_ISLNK(s.st_mode) and os.readlink(source) == row["target"], "Link changed")
                        info.type, info.linkname = tarfile.SYMTYPE, row["target"]
                        target.addfile(info)
                    else:
                        require(stat.S_ISREG(s.st_mode) and s.st_size == row["size"], "Source changed: " + row["path"])
                        info.type, info.size = tarfile.REGTYPE, row["size"]
                        with source.open("rb") as stream:
                            checked = CheckedReader(stream)
                            target.addfile(info, checked)
                            require(checked.hash.hexdigest() == row["sha256"], "Source hash mismatch: " + row["path"])
                        total += row["size"]
                    count += 1
                    if time.monotonic() - last > 25:
                        print(json.dumps({"packed_entries": count, "GiB": round(total / 2**30, 3)}), flush=True)
                        last = time.monotonic()
            compressor.stdin.close()
            error = compressor.stderr.read().decode(errors="replace")
            require(compressor.wait() == 0, "Compression failed: " + error)
        finally:
            if compressor.poll() is None:
                compressor.kill()
                compressor.wait()
        destination.flush()
        os.fsync(destination.fileno())
    partial.replace(archive)
    archive.chmod(0o644)


def verify(archive, rows):
    expected = {r["path"]: r for r in rows}
    seen = set()
    regular = links = total = 0
    decoder = subprocess.Popen(["zstd", "-dc", str(archive)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with tarfile.open(fileobj=decoder.stdout, mode="r|") as source:
            for member in source:
                require(member.name in expected and member.name not in seen, "Unexpected/repeated archive member")
                row = expected[member.name]
                if row["type"] == "symlink":
                    require(member.issym() and member.linkname == row["target"], "Archived symlink mismatch")
                    links += 1
                else:
                    require(member.isfile() and member.size == row["size"], "Archived file size/type mismatch")
                    h = hashlib.sha256()
                    stream = source.extractfile(member)
                    for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                        h.update(chunk)
                    require(h.hexdigest() == row["sha256"], "Archived content mismatch: " + member.name)
                    regular += 1
                    total += member.size
                seen.add(member.name)
        while decoder.stdout.read(1024 * 1024):
            pass
        error = decoder.stderr.read().decode(errors="replace")
        require(decoder.wait() == 0, "Archive decompression failed: " + error)
    finally:
        if decoder.poll() is None:
            decoder.kill()
            decoder.wait()
    require(seen == set(expected), "Missing archive members")
    return {"verified_regular_files": regular, "verified_symlinks": links,
            "verified_uncompressed_bytes": total, "all_selected_members_verified": True}


def create():
    require(os.geteuid() == 0, "sudo required for read-only old-volume access")
    plan, rows = load_selection()
    spec = importlib.util.spec_from_file_location("partition", BASE / "create_data_partition.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.preflight()
    module.validate_table(module.load_table())
    folder = BASE / "rescue_backup"
    folder.mkdir(exist_ok=True, mode=0o755)
    archive = folder / "old-research-selective.tar.zst"
    mountpoint = Path(f"/mnt/old-research-rescue-{os.getpid()}")
    loop = None
    mounted = False
    try:
        loop = module.command("losetup", "--find", "--show", "--read-only", "--offset", str(module.START * 512),
                              "--sizelimit", str((module.END - module.START + 1) * 512), module.DISK).stdout.strip()
        require(module.command("blkid", "-s", "UUID", "-o", "value", loop).stdout.strip() == OLD_UUID, "Wrong volume")
        mountpoint.mkdir(mode=0o700)
        module.command("mount", "-t", "ext4", "-o", "ro,noload,nodev,nosuid,noexec", loop, str(mountpoint))
        mounted = True
        pack(mountpoint / "home/sun/phdproject", rows, archive)
    finally:
        if mounted:
            module.command("umount", str(mountpoint))
        if loop:
            module.command("losetup", "--detach", loop)
        if mountpoint.exists():
            mountpoint.rmdir()
    result = {"status": "remote_archive_created", "old_filesystem_uuid": OLD_UUID,
              "selection_sha256": plan["selection_sha256"], "archive": str(archive),
              "archive_bytes": archive.stat().st_size, "archive_sha256": digest(archive),
              "selected_regular_files": plan["selected_regular_files"],
              "selected_symlinks": plan["selected_symlinks"], "source_files_verified_during_pack": True}
    (BASE / "RESCUE_REMOTE.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true")
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.create:
        create()
    elif args.verify:
        plan, rows = load_selection()
        remote = json.loads((BASE / "RESCUE_REMOTE.json").read_text())
        archive = args.verify.resolve()
        archive_sha = digest(archive)
        require(archive_sha == remote["archive_sha256"] and archive.stat().st_size == remote["archive_bytes"], "Transfer mismatch")
        result = verify(archive, rows)
        with archive.open("rb") as stream:
            os.fsync(stream.fileno())
        result.update(status="verified_on_mac" if sys.platform == "darwin" else "verified_on_other_host",
                      platform=sys.platform, host=socket.gethostname(), local_archive=str(archive),
                      archive_sha256=archive_sha, archive_bytes=archive.stat().st_size,
                      old_filesystem_uuid=OLD_UUID, selection_sha256=plan["selection_sha256"],
                      timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        (BASE / "RESCUE_LOCAL_VERIFIED.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
    else:
        parser.error("Choose --create or --verify ARCHIVE")
