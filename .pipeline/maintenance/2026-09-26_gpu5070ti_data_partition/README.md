# gpu5070ti storage maintenance — completed

Dr Sun explicitly approved making the approximately 5 GiB selective research
backup on the Mac, then clearing the entire old volume and creating `/data`.
This completed at 2026-09-26 12:50:53 UTC.

## Result

- New partition: `/dev/nvme0n1p5`, sectors 32768–586334207 inclusive.
- Filesystem: ext4, label `VLA_DATA`, UUID
  `6b824505-616f-4474-8ebc-3fe1424f33ab`, mounted at `/data`, owned by `sun`.
- Available after formatting: 294,316,666,880 bytes (274.1 GiB).
- Root available after transfer-staging cleanup: 67,296,342,016 bytes (62.7 GiB).
- Original partitions 1–4 retained their original GUIDs and geometry.
- Root UUID remains `6961a116-7df0-4282-9220-a46dbf555ea0`.
- UUID-based fstab entry, unmount/remount through fstab, and writing as `sun`
  passed. No reboot was performed; no existing experiments were moved.

The new data filesystem has zero reserved-block percentage. Its fstab entry
uses `defaults,nofail 0 2`. The mounted filesystem belongs to `sun`; the
underlying empty `/data` mountpoint remains root-owned.

## Verified rescue

The Mac holds `rescue_backup/old-research-selective.tar.zst`: 3.778 GiB compressed,
containing 25,561 regular files and 10 links, totaling 4.955 GiB of file content.
The Mac independently verified every selected file SHA-256 and every link
target before the erase gate passed. The full archive hash also matched.

See `RESCUE_README.md` for restoration, precise exclusions, copies, and hashes.
This is a selective research backup; full old-volume coverage by Google Drive
was not established or claimed. The old OS, periodic/checkpoint `.pt` files,
other home contents, and separate old `phdproject.zip` were outside the approved
rescue. Both Mac and current Ubuntu retain the complete rescue archive.
Temporary transfer chunks have been removed from both hosts.

## Execution evidence

- `RESCUE_PLAN.json`, `RESCUE_SELECTION.jsonl`: exact approved selection.
- `RESCUE_LOCAL_VERIFIED.json`: Mac verification before erasure.
- `PREOP_METADATA_LOCAL_VERIFIED.json`, `preop_metadata/`: off-host GPT/fstab
  copies verified before any partition write.
- `runtime_result/`: before/after GPT metadata, original fstab, Mac receipt,
  and the actual `RESULT.json` returned by the execution script.
- `FINAL_LIVE_CHECK.json`: post-cleanup filesystem, mount, permission, root UUID,
  partition and fstab checks.
- `TRANSFER_CLEANUP_LOCAL.json`, `TRANSFER_CLEANUP_REMOTE.json`: staging cleanup.

Local source of truth is this directory. Remote execution copy is
`/home/sun/storage_maintenance/2026-09-26_data_partition/`. Runtime metadata also
remains under `/var/backups/gpu5070ti-data-partition/20260926T125051Z/`.

The executed `create_data_partition.py` SHA-256 was
`353c085307e525019c045283b06acd7f451c4268116f8b8db306938250de499d` on both hosts.
It verified the KIOXIA SSD serial `YFAKS06KZ3TE`, exact disk and partition
geometry, old filesystem UUID and extent, and the verified Mac receipt before
formatting only partition 5. It refuses to run again now that partition 5
exists. Do not restore the historical GPT automatically: it omits the new data
partition, and restoring metadata cannot recover erased old file contents.

## Historical discovery

The first privileged preflight found old ext4 UUID
`89dc617c-0cf0-4757-a997-8e3c15e79b5a` inside a range with no GPT entry. It stopped
before changing the disk. Read-only inspection identified an old Linux root
with approximately 253.38 GiB allocated. See `EXISTING_FILESYSTEM.json`,
`INSTALLATION_TIMELINE.md`, and `data_audit/REPORT.md` for the historical evidence.
The later explicit selective-backup-and-erase authorization superseded that
initial stop. Earlier discovery records retain their original timestamps and
must not be interpreted as the current disk state.
