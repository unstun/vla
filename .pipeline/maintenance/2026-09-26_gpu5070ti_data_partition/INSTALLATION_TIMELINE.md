# Why the unpartitioned gap still contains an old Ubuntu system

## Confirmed from primary local evidence

The old ext4 filesystem occupies sectors 32768 through 586334207 on the KIOXIA
SSD with serial YFAKS06KZ3TE. It has no GPT partition entry, but its metadata and
files are readable. Its UUID is 89dc617c-0cf0-4757-a997-8e3c15e79b5a.

The old filesystem's superblock records creation on 2026-02-02 and its last
mount on 2026-04-19 at 06:47:24, with the last mount path recorded as /.
These are filesystem metadata timestamps, not proof of who performed an action.

The current Ubuntu installation has installer records from 2026-04-19.
Its root filesystem was created at 07:09:06; the installer log explicitly runs
mkfs.ext4 with UUID 6961a116-7df0-4282-9220-a46dbf555ea0, which matches the
currently mounted root.

The installer's saved pre-install probe contains only the Microsoft-reserved
partition and EFI partition on this SSD. The old filesystem's GPT entry was
already absent in that snapshot. The final storage configuration preserves
those two entries and creates new swap and root partitions after the EFI
partition, leaving the earlier 279.57 GiB range unallocated in GPT.

At installation the KIOXIA was named /dev/nvme1n1; it is currently
/dev/nvme0n1. Physical identity is established by the matching SSD serial number,
not by the changing NVMe device index.

All human-readable times above are as recorded/displayed by the server.

## Explanation and limits

The evidence is consistent with removing the old partition entry before the
saved installation probe, then reinstalling Ubuntu into another region of the
same SSD. Removing an entry does not necessarily erase the filesystem bytes.
Because the new swap and root were created elsewhere, the old files survived.

The available evidence does not identify the operator, the exact partition
deletion command, or the reason. Do not attribute this to Dr Sun, an assistant,
or a particular partition utility without additional evidence.

## Sources

See INSTALLER_EVIDENCE.json for selected, credential-free source extracts:

- /var/log/installer/block/probe-data.json
- /var/log/installer/curtin-install/subiquity-partitioning.conf
- /var/log/installer/curtin-install.log
- /var/log/installer/media-info
- Current root dumpe2fs -h output
- EXISTING_FILESYSTEM.json for the old volume's read-only inspection

No partition or filesystem modification has been made by this task.
