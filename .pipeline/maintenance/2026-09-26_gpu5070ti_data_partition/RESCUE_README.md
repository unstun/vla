# Verified selective rescue of the old gpu5070ti research tree

> Storage update (2026-10-07): Dr Sun authorized removing the local archive after a fresh full SHA-256 match against the retained gpu5070ti copy. The payload is now remote-only at the server path below. Restore it before using the local verification/extraction commands. See [the removal receipt](../2026-10-07_verified_local_duplicates/manifest.json). The original rescue verification remains historical evidence.

Dr Sun approved preserving this selection on the Mac before clearing the entire
old volume. This is a selective research backup, not an image of the old OS.

- Source: `/home/sun/phdproject` inside old ext4 UUID
  `89dc617c-0cf0-4757-a997-8e3c15e79b5a`.
- Mac payload: `rescue_backup/old-research-selective.tar.zst` in this directory.
- Second payload copy:
  `gpu5070ti:/home/sun/storage_maintenance/2026-09-26_data_partition/rescue_backup/old-research-selective.tar.zst`.
- Compressed size: 4,056,586,200 bytes (3.778 GiB).
- SHA-256: `30f767e9a87679e93f0e9a44dc6ee806fdaa6839bbebb45960b2fbda22a02c70`.
- Contents: 25,561 regular files, 10 symbolic links, 5,320,387,407 regular-file
  bytes (4.955 GiB).

All regular files and symbolic links from the source research tree are selected
except `.pt` paths containing `/checkpoints/` or `/periodic/`. That excludes
23,395 regular checkpoint files and 12,274 checkpoint links. The old operating
system, other home-directory contents, and the separate `phdproject.zip` are
outside this backup. Preserved links retain their original targets; the backup
does not promise that every target remains present after this selection.

The source was mounted read-only with journal replay disabled. Every selected
source file was hashed while packing. After transfer, the Mac verified the
archive SHA-256 and independently decompressed and checked every member's size,
content hash, or link target against `RESCUE_SELECTION.jsonl`. The full member
set matched, with no missing or unexpected members. See
`RESCUE_LOCAL_VERIFIED.json` for the actual verification receipt. Its timestamp
precedes the authorized erase operation.

## Restore into a new directory

Run from this maintenance directory. Install `zstd` first if unavailable.

```sh
shasum -a 256 rescue_backup/old-research-selective.tar.zst
mkdir restored-old-research
zstd -dc rescue_backup/old-research-selective.tar.zst | tar -xf - -C restored-old-research
```

Compare the hash with the value above before extraction. To repeat the full
member verification without extracting files:

```sh
python3 rescue_backup.py --verify rescue_backup/old-research-selective.tar.zst
```

`RESCUE_PLAN.json` and `RESCUE_SELECTION.jsonl` define the exact preservation
boundary. `RESCUE_REMOTE.json` records the original payload. The path-specific
`.gitignore` excludes only `rescue_backup/`. Since 2026-10-07, retain the server
payload together with the tracked provenance. Git alone cannot restore its bytes.
The old-volume scan, selection manifest, and packing script document how it
was produced. After erasure it cannot be regenerated from the old disk; recover
the identical archive from one of the retained copies instead.
