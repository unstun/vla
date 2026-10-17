#!/usr/bin/env python3
"""One-time, fail-closed creation of the approved gpu5070ti /data partition."""

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile
import time


DISK = "/dev/nvme0n1"
PARTITION = DISK + "p5"
ROOT_UUID = "6961a116-7df0-4282-9220-a46dbf555ea0"
OLD_UUID = "89dc617c-0cf0-4757-a997-8e3c15e79b5a"
SERIAL = "YFAKS06KZ3TE"
DISK_SECTORS = 1953525168
START = 32768
END = 586334207
EXPECTED = {
    1: (34, 32734),
    2: (586334208, 2201600),
    3: (588535808, 142331904),
    4: (730867712, 1222653952),
}
ENV = {**os.environ, "LC_ALL": "C", "PATH": "/usr/sbin:/usr/bin:/sbin:/bin"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def command(*args, check=True):
    result = subprocess.run(args, capture_output=True, text=True, env=ENV)
    if check and result.returncode:
        raise RuntimeError(f"Command failed: {args!r}\n{result.stdout}\n{result.stderr}")
    return result


def partition_map(table):
    disk = table["device"]
    return {
        int(p["node"][len(disk):].removeprefix("p")): p
        for p in table["partitions"]
    }


def validate_table(table, after=False):
    require(table["label"] == "gpt", "Expected GPT; refusing conversion")
    require(table["sectorsize"] == 512, "Unexpected logical sector size")
    parts = partition_map(table)
    expected = {**EXPECTED, **({5: (START, END - START + 1)} if after else {})}
    actual = {n: (p["start"], p["size"]) for n, p in parts.items()}
    require(actual == expected, f"Partition layout changed: {actual}")
    require(table["firstlba"] <= START <= END <= table["lastlba"], "Invalid range")
    if not after:
        for p in parts.values():
            require(END < p["start"] or START >= p["start"] + p["size"], "Overlap")
    return parts


def load_table(disk=DISK):
    return json.loads(command("sfdisk", "--json", disk).stdout)["partitiontable"]


def preflight():
    require(command("findmnt", "-n", "-o", "UUID", "/").stdout.strip() == ROOT_UUID,
            "Wrong root filesystem UUID")
    require(command("findmnt", "-n", "-o", "SOURCE", "/").stdout.strip() == DISK + "p4",
            "Wrong root block device")
    require(command("lsblk", "-dn", "-o", "SERIAL", DISK).stdout.strip() == SERIAL,
            "Wrong physical SSD serial number")
    base = Path("/sys/class/block/nvme0n1")
    require(int((base / "size").read_text()) == DISK_SECTORS, "Wrong SSD capacity")
    found = {}
    for p in Path("/sys/class/block").glob("nvme0n1p*"):
        found[int(p.name.split("p")[-1])] = (
            int((p / "start").read_text()), int((p / "size").read_text())
        )
    require(found == EXPECTED, f"Kernel partition layout changed: {found}")
    require(not Path(PARTITION).exists(), "Partition 5 exists; never reformat on retry")
    require(not os.path.lexists("/data"), "/data already exists; stop for review")
    fstab = Path("/etc/fstab").read_bytes()
    for line in fstab.decode().splitlines():
        fields = line.split()
        if fields and not fields[0].startswith("#"):
            require(len(fields) < 2 or fields[1] != "/data", "/data already in fstab")
    for tool in ["sgdisk", "sfdisk", "blkid", "partx", "udevadm", "mkfs.ext4",
                 "mount", "umount", "findmnt", "runuser", "systemctl"]:
        require(shutil.which(tool, path=ENV["PATH"]) is not None, f"Missing tool: {tool}")
    return fstab


def save(path, data):
    payload = data if isinstance(data, bytes) else data.encode()
    with path.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o644)


def file_sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def backup_gate(erase_old_uuid, receipt_path):
    require(erase_old_uuid == OLD_UUID, "Explicit authorization must name the known old filesystem")
    require(receipt_path is not None, "Verified off-host rescue receipt is required")
    base = Path(__file__).resolve().parent
    plan = json.loads((base / "RESCUE_PLAN.json").read_text())
    receipt = json.loads(Path(receipt_path).read_text())
    remote = json.loads((base / "RESCUE_REMOTE.json").read_text())
    require(file_sha256(base / "RESCUE_SELECTION.jsonl") == plan["selection_sha256"], "Selection changed")
    require(receipt["status"] == "verified_on_mac" and receipt.get("platform") == "darwin" and
            receipt["all_selected_members_verified"] is True,
            "Mac member verification did not pass")
    require(receipt["old_filesystem_uuid"] == OLD_UUID == remote["old_filesystem_uuid"], "Wrong backup source UUID")
    require(receipt["selection_sha256"] == plan["selection_sha256"] == remote["selection_sha256"], "Wrong backup selection")
    require(receipt["verified_regular_files"] == plan["selected_regular_files"] and
            receipt["verified_symlinks"] == plan["selected_symlinks"] and
            receipt["verified_uncompressed_bytes"] == plan["selected_bytes"], "Incomplete Mac rescue")
    archive = base / "rescue_backup/old-research-selective.tar.zst"
    require(archive.is_file() and not archive.is_symlink(), "Remote rescue payload missing")
    require(archive.stat().st_size == receipt["archive_bytes"] == remote["archive_bytes"], "Backup size mismatch")
    require(file_sha256(archive) == receipt["archive_sha256"] == remote["archive_sha256"], "Backup checksum mismatch")
    return receipt


def probe_fields(result):
    require(result.returncode == 0, "Expected the known old filesystem signature")
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def apply(erase_old_uuid=None, receipt_path=None):
    require(os.geteuid() == 0, "Administrator authentication required: run with sudo")
    lock = os.open("/run/lock/gpu5070ti-data-partition.lock",
                   os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    fstab_before = preflight()
    receipt = backup_gate(erase_old_uuid, receipt_path)
    before = load_table()
    require(before["device"] == DISK, "Unexpected disk in on-disk partition table")
    old_parts = validate_table(before)
    verification = command("sgdisk", "--verify", DISK).stdout
    require("No problems found" in verification, f"GPT needs review: {verification}")

    # Dr Sun explicitly approved erasing this old filesystem after the selective
    # rescue is verified on the Mac. A different signature must still stop us.
    probe = command("blkid", "-p", "-O", str(START * 512), "-S",
                    str((END - START + 1) * 512), "-o", "export", DISK, check=False)
    signature = probe_fields(probe)
    require(signature.get("UUID") == OLD_UUID and signature.get("TYPE") == "ext4" and
            int(signature.get("FSSIZE", "0")) == (END - START + 1) * 512,
            "Old filesystem identity or extent changed; no disk changes made")
    require(not command("losetup", "--associated", DISK).stdout.strip(), "An offset loop still uses the SSD")

    backup = Path("/var/backups/gpu5070ti-data-partition") / time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    backup.mkdir(parents=True, mode=0o755, exist_ok=False)
    save(backup / "fstab.before", fstab_before)
    save(backup / "partition.before.json", json.dumps(before, indent=2))
    save(backup / "rescue.mac-verified.json", json.dumps(receipt, indent=2))
    save(backup / "partition.before.sfdisk", command("sfdisk", "--dump", DISK).stdout)
    command("sgdisk", f"--backup={backup / 'gpt.before.bin'}", DISK)
    require((backup / "gpt.before.bin").stat().st_size > 0, "GPT backup missing")
    command("sync", "-f", str(backup))
    print(f"BACKUP={backup}", flush=True)

    command("sgdisk", f"--new=5:{START}:{END}", "--typecode=5:8300",
            "--change-name=5:VLA_DATA", DISK)
    after = load_table()
    new_parts = validate_table(after, after=True)
    require(before["id"] == after["id"], "Disk GUID changed unexpectedly")
    require(all(old_parts[n] == new_parts[n] for n in EXPECTED),
            "An existing partition changed; STOP before formatting")
    save(backup / "partition.after.json", json.dumps(after, indent=2))
    if not Path("/sys/class/block/nvme0n1p5").exists():
        command("partx", "--add", "--nr", "5", DISK)
    command("udevadm", "settle", "--timeout=30")
    node = Path("/sys/class/block/nvme0n1p5")
    require(node.exists() and Path(PARTITION).is_block_device(),
            "Partition created but not visible to kernel; STOP before formatting")
    require(int((node / "start").read_text()) == START and
            int((node / "size").read_text()) == END - START + 1, "Kernel range mismatch")
    signature = probe_fields(command("blkid", "-p", "-o", "export", PARTITION, check=False))
    require(signature.get("UUID") == OLD_UUID and signature.get("TYPE") == "ext4",
            "Partition does not expose the explicitly approved old filesystem")
    require(command("findmnt", "-n", "-S", PARTITION, check=False).returncode == 1,
            "Old filesystem became mounted; STOP before formatting")
    print("BACKUP_VERIFIED; formatting only the approved old-volume partition", flush=True)
    command("mkfs.ext4", "-F", "-L", "VLA_DATA", "-m", "0", PARTITION)
    uuid = command("blkid", "-s", "UUID", "-o", "value", PARTITION).stdout.strip()
    require(bool(uuid) and uuid not in {OLD_UUID, ROOT_UUID}, "New filesystem UUID missing or reused")
    Path("/data").mkdir(mode=0o755)
    command("mount", "-t", "ext4", PARTITION, "/data")
    account = pwd.getpwnam("sun")
    os.chown("/data", account.pw_uid, account.pw_gid)
    os.chmod("/data", 0o755)

    new_fstab = fstab_before.rstrip(b"\n") + (
        f"\n# Approved gpu5070ti data partition, 2026-09-26\n"
        f"UUID={uuid} /data ext4 defaults,nofail 0 2\n"
    ).encode()
    require(Path("/etc/fstab").read_bytes() == fstab_before, "fstab changed concurrently")
    fd, name = tempfile.mkstemp(prefix="fstab.data-", dir="/etc")
    candidate = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(new_fstab)
            stream.flush()
            os.fsync(stream.fileno())
        shutil.copystat("/etc/fstab", candidate)
        command("findmnt", "--verify", "--tab-file", str(candidate))
        os.replace(candidate, "/etc/fstab")
    finally:
        candidate.unlink(missing_ok=True)
    command("systemctl", "daemon-reload")
    command("umount", "/data")
    command("mount", "/data")  # Exercise the saved UUID-based fstab entry.
    require(command("findmnt", "-n", "-o", "UUID", "/data").stdout.strip() == uuid,
            "Mounted wrong filesystem")
    command("runuser", "-u", "sun", "--", "/usr/bin/python3", "-I", "-c",
            "import os,tempfile; fd,p=tempfile.mkstemp(prefix='.write-test-',dir='/data'); "
            "os.write(fd,b'data-partition-write-test\\n'); os.fsync(fd); os.close(fd); os.unlink(p)")
    require(command("findmnt", "-n", "-o", "UUID", "/").stdout.strip() == ROOT_UUID,
            "Root filesystem identity changed")
    result = {
        "status": "validated", "host": "gpu5070ti", "partition": PARTITION,
        "uuid": uuid, "mountpoint": "/data", "owner": "sun", "backup": str(backup),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "existing_partitions_unchanged": True, "fstab_remount_passed": True,
        "erased_old_filesystem_uuid": OLD_UUID,
        "verified_rescue_archive_sha256": receipt["archive_sha256"],
        "verified_rescue_local_archive": receipt["local_archive"],
        "user_write_test_passed": True, "reboot_tested": False,
        "df": command("df", "-hT", "/", "/data").stdout.strip(),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    save(backup / "RESULT.json", json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Requires sudo; writes the approved partition")
    parser.add_argument("--erase-old-uuid", choices=[OLD_UUID])
    parser.add_argument("--verified-backup-receipt", type=Path)
    args = parser.parse_args()
    if args.apply:
        apply(args.erase_old_uuid, args.verified_backup_receipt)
    else:
        preflight()
        print(json.dumps({"status": "unprivileged_preflight_passed", "disk": DISK,
                          "start_sector": START, "end_sector": END,
                          "size_GiB": (END - START + 1) * 512 / 2**30,
                          "privileged_partition_and_signature_checks_pending": True}))
