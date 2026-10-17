#!/usr/bin/env python3
"""Exercise GPT operations on a disposable sparse image, never a block device."""

import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile


spec = importlib.util.spec_from_file_location("create_data", Path(__file__).with_name("create_data_partition.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def rejected(table):
    try:
        module.validate_table(table)
    except RuntimeError:
        return
    raise AssertionError("Unsafe partition layout was accepted")


with tempfile.TemporaryDirectory(prefix="partition-prepare-test-") as directory:
    image = Path(directory) / "disk.img"
    with image.open("xb") as stream:
        stream.truncate(module.DISK_SECTORS * 512)
    assert image.is_file() and not image.is_block_device()
    args = ["sgdisk", "--clear", "--set-alignment=1"]
    for number, (start, size) in module.EXPECTED.items():
        args.append(f"--new={number}:{start}:{start + size - 1}")
    module.command(*args, str(image))
    before = module.load_table(str(image))
    old_parts = module.validate_table(before)
    assert "No problems found" in module.command("sgdisk", "--verify", str(image)).stdout
    probe = module.command("blkid", "-p", "-O", str(module.START * 512), "-S",
                           str((module.END - module.START + 1) * 512),
                           "-o", "export", str(image), check=False)
    assert probe.returncode == 2 and not probe.stdout.strip() and not probe.stderr.strip(), probe
    negative_cases = []
    changed = copy.deepcopy(before)
    changed["partitions"][-1]["start"] += 1
    rejected(changed)
    negative_cases.append("changed_root_start")
    changed = copy.deepcopy(before)
    changed["sectorsize"] = 4096
    rejected(changed)
    negative_cases.append("wrong_sector_size")
    changed = copy.deepcopy(before)
    changed["label"] = "dos"
    rejected(changed)
    negative_cases.append("non_gpt")
    module.command("sgdisk", f"--backup={directory}/before.gpt", str(image))
    assert (Path(directory) / "before.gpt").stat().st_size > 0
    module.command("sgdisk", f"--new=5:{module.START}:{module.END}",
                   "--typecode=5:8300", "--change-name=5:VLA_DATA", str(image))
    after = module.load_table(str(image))
    new_parts = module.validate_table(after, after=True)
    assert all(old_parts[n] == new_parts[n] for n in module.EXPECTED)
    assert before["id"] == after["id"]
    rejected(after)
    negative_cases.append("existing_partition_5_retry")
    # A filesystem signature must be noticed by the range probe before real GPT writes.
    filesystem = Path(directory) / "filesystem.img"
    with filesystem.open("xb") as stream:
        stream.truncate(64 * 1024 * 1024)
    module.command("mkfs.ext4", "-q", str(filesystem))
    with filesystem.open("rb") as stream:
        prefix = stream.read(65536)
    with image.open("r+b") as stream:
        stream.seek(module.START * 512)
        stream.write(prefix)
    probe = module.command("blkid", "-p", "-O", str(module.START * 512), "-S",
                           str((module.END - module.START + 1) * 512),
                           "-o", "export", str(image), check=False)
    assert probe.returncode == 0 and "TYPE=ext4" in probe.stdout
    print(json.dumps({"status": "passed", "negative_cases": negative_cases,
                      "sparse_image_gpt_creation_and_existing_partition_preservation": True,
                      "empty_range_probe": True, "existing_filesystem_signature_detection": True,
                      "real_block_devices_modified": False,
                      "root_execution_and_mount_not_tested": True}, indent=2))
