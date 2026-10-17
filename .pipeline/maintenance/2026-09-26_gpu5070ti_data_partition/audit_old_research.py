#!/usr/bin/env python3
"""Hash old research files read-only; write only to the current OS audit directory."""

import collections
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import time
import zipfile


spec = importlib.util.spec_from_file_location("create_data", Path(__file__).with_name("create_data_partition.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.require(os.geteuid() == 0, "sudo required")
module.preflight()
module.validate_table(module.load_table())
output = Path(__file__).parent / "data_audit"
output.mkdir(exist_ok=True)
output.chmod(0o755)
mountpoint = Path(f"/mnt/gpu5070ti-research-audit-{os.getpid()}")
loop = None
mounted = False
counts = collections.Counter()
sizes = collections.Counter()
suffixes = collections.Counter()
largest = []
errors = []
total = 0
last_report = time.monotonic()
try:
    loop = module.command("losetup", "--find", "--show", "--read-only", "--offset",
                          str(module.START * 512), "--sizelimit",
                          str((module.END - module.START + 1) * 512), module.DISK).stdout.strip()
    module.require(module.command("blkid", "-s", "UUID", "-o", "value", loop).stdout.strip()
                   == "89dc617c-0cf0-4757-a997-8e3c15e79b5a", "Wrong old volume")
    mountpoint.mkdir(mode=0o700)
    module.command("mount", "-t", "ext4", "-o", "ro,noload,nodev,nosuid,noexec",
                   loop, str(mountpoint))
    mounted = True
    root = mountpoint / "home/sun/phdproject"
    with gzip.open(output / "old_research_manifest.jsonl.gz", "wt", encoding="utf-8") as manifest:
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in sorted(files + [d for d in dirs if (Path(directory) / d).is_symlink()]):
                path = Path(directory) / name
                relative = str(path.relative_to(root))
                info = path.lstat()
                record = {"path": relative, "size": info.st_size,
                          "allocated_bytes": info.st_blocks * 512, "mtime_ns": info.st_mtime_ns}
                if stat.S_ISLNK(info.st_mode):
                    record.update(type="symlink", target=os.readlink(path))
                elif stat.S_ISREG(info.st_mode):
                    md5 = hashlib.md5()
                    sha = hashlib.sha256()
                    try:
                        with path.open("rb") as stream:
                            for data in iter(lambda: stream.read(8 * 1024 * 1024), b""):
                                md5.update(data)
                                sha.update(data)
                        record.update(type="file", md5=md5.hexdigest(), sha256=sha.hexdigest())
                    except OSError as error:
                        errors.append({"path": relative, "error": str(error)})
                        record.update(type="unreadable")
                    group = "/".join(path.relative_to(root).parts[:2])
                    counts[group] += 1
                    sizes[group] += info.st_size
                    suffixes[path.suffix or "(none)"] += info.st_size
                    largest.append((info.st_size, relative))
                    total += info.st_size
                else:
                    record.update(type="special")
                manifest.write(json.dumps(record, ensure_ascii=False) + "\n")
                if time.monotonic() - last_report > 25:
                    print(json.dumps({"hashed_files": sum(counts.values()), "GiB": round(total / 2**30, 2)}), flush=True)
                    last_report = time.monotonic()
    archive = mountpoint / "home/sun/phdproject.zip"
    archive_summary = {"bytes": archive.stat().st_size, "mtime_ns": archive.stat().st_mtime_ns}
    with zipfile.ZipFile(archive) as source, gzip.open(output / "old_archive_entries.jsonl.gz", "wt", encoding="utf-8") as target:
        records = source.infolist()
        archive_summary["entry_count"] = len(records)
        archive_summary["uncompressed_bytes"] = sum(p.file_size for p in records)
        for p in records:
            target.write(json.dumps({"path": p.filename, "size": p.file_size,
                                     "crc32": p.CRC, "zip_datetime": p.date_time}, ensure_ascii=False) + "\n")
    report = {
        "read_only_old_volume": True, "regular_file_count": sum(counts.values()),
        "logical_bytes_hashed": total, "errors": errors,
        "groups": [{"path": name, "bytes": amount, "files": counts[name]} for name, amount in sizes.most_common()],
        "extensions": suffixes.most_common(20),
        "largest_files": [{"path": name, "bytes": amount} for amount, name in sorted(largest, reverse=True)[:30]],
        "old_phdproject_zip": archive_summary,
    }
finally:
    if mounted:
        module.command("umount", str(mountpoint))
    if loop:
        module.command("losetup", "--detach", loop)
    if mountpoint.exists():
        mountpoint.rmdir()
report["read_only_mount_removed"] = True
(output / "SUMMARY.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
for path in output.iterdir():
    path.chmod(0o644)
print(json.dumps({"status": "complete", "files": sum(counts.values()),
                  "GiB": round(total / 2**30, 2), "errors": errors, "output": str(output)}), flush=True)
