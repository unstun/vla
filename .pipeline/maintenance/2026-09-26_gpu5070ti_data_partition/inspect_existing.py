#!/usr/bin/env python3
"""Inspect the unexpected filesystem through a read-only offset loop device."""

import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


spec = importlib.util.spec_from_file_location("create_data", Path(__file__).with_name("create_data_partition.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.require(os.geteuid() == 0, "sudo required")
module.preflight()
module.validate_table(module.load_table())
mountpoint = Path(f"/mnt/gpu5070ti-data-inspect-{os.getpid()}")
loop = None
mounted = False
report = {"read_only": True, "journal_replay_disabled": True,
          "partition_table_unchanged": True}
inventory_only = "--inventory-only" in sys.argv
try:
    loop = module.command("losetup", "--find", "--show", "--read-only", "--offset",
                          str(module.START * 512), "--sizelimit",
                          str((module.END - module.START + 1) * 512), module.DISK).stdout.strip()
    module.require(loop.startswith("/dev/loop"), "Unexpected loop device")
    if not inventory_only:
        report["superblock"] = module.command("dumpe2fs", "-h", loop).stdout
    mountpoint.mkdir(mode=0o700)
    module.command("mount", "-t", "ext4", "-o", "ro,noload,nodev,nosuid,noexec",
                   loop, str(mountpoint))
    mounted = True
    entries = []
    for p in sorted(mountpoint.iterdir()):
        s = p.lstat()
        entries.append({"name": p.name, "mode": stat.filemode(s.st_mode),
                        "uid": s.st_uid, "gid": s.st_gid, "bytes": s.st_size})
    report["root_entries"] = entries
    fs = os.statvfs(mountpoint)
    report["filesystem_bytes"] = fs.f_blocks * fs.f_frsize
    report["available_bytes"] = fs.f_bavail * fs.f_frsize
    report["allocated_bytes"] = (fs.f_blocks - fs.f_bfree) * fs.f_frsize
    if inventory_only:
        home = mountpoint / "home"
        report["home_names"] = sorted(p.name for p in home.iterdir())
        try:
            result = subprocess.run(["du", "-x", "-B1", "--max-depth=2", str(home)],
                                    capture_output=True, text=True, timeout=45, env=module.ENV)
            output = result.stdout
            report["du_completed"] = result.returncode == 0
        except subprocess.TimeoutExpired as error:
            output = error.stdout or b""
            if isinstance(output, bytes):
                output = output.decode(errors="replace")
            report["du_completed"] = False
        sizes = []
        for line in output.splitlines():
            if "\t" in line:
                size, name = line.split("\t", 1)
                sizes.append({"bytes": int(size), "path": name.removeprefix(str(mountpoint))})
        report["largest_home_directories"] = sorted(sizes, key=lambda item: item["bytes"], reverse=True)[:20]
    module.command("umount", str(mountpoint))
    mounted = False
    if not inventory_only:
        check = module.command("e2fsck", "-f", "-n", loop, check=False)
        report["fsck_readonly_returncode"] = check.returncode
        report["fsck_readonly_stdout"] = check.stdout
        report["fsck_readonly_stderr"] = check.stderr
finally:
    if mounted:
        module.command("umount", str(mountpoint))
    if loop:
        module.command("losetup", "--detach", loop)
    if mountpoint.exists():
        mountpoint.rmdir()
print(json.dumps(report, indent=2))
