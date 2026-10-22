# Reference source storage on ModelArchive

Dr Sun requested on 2026-10-22 that the reference repositories be stored on the
external drive. The selected disk is the writable USB/APFS `ModelArchive`
volume, UUID `6C6A2FE8-9BB7-4F86-803C-3B3C55A29BB1`.

Destination: `/Volumes/ModelArchive/vla-references/`, preserving each source's
project-relative path. The dated manifests, catalogues and short verification
receipts remain in the project. Both old and newly acquired reference sources
are included, not only the current 50-repository collection.

## Scope and preservation

- Nineteen untracked source/cache directories, approximately 6.7 GiB, are
  relocated and replaced at their original paths by absolute symlinks.
- Two source snapshots already tracked by Git — the Lite3 simulation bridge
  and OmniVLA — are backed up on the external drive, while their local Git
  working-tree bytes (about 1.8 MiB total) remain intact. No tracked source
  files are removed or replaced with links.
- Existing dirty source files, Git objects, local branches, symlinks and assets
  inside the selected directories are copied as they exist. No reset, checkout,
  clean or repository-history rewrite is performed during migration.
- Small tracked excerpts outside these source roots and experiment working
  copies remain part of the project; this operation relocates reference
  repositories rather than the research project or experiment history.

## Evidence

[plan.json](plan.json) names every source and destination. [copy_receipts.json](copy_receipts.json)
records complete source/destination equality before switching. The local
`raw_logs/` contains per-entry SHA-256, symlink targets, modes and source-stat
snapshots. [migration_receipts.json](migration_receipts.json) records each final
state. Source bytes, Git history and the prior acquisition failures are kept.
The [post-migration verification](verification.json) checks every original path,
external link, retained Git snapshot and removed internal migration backup.

Copy runs first. Only after hashing all copies does `switch` recheck the target
disk, destination content and unchanged source; rename that one source to a
temporary local backup; install its external symlink; and remove that verified
local original. The already tracked snapshots are copy-only.

## Reconnecting paths

Keep the external volume mounted as `/Volumes/ModelArchive`. A missing disk
makes the source links unavailable; it does not cause the download tool to
silently create a replacement source directory on the internal drive.

After restoring the project from Git, reconnect the existing external sources:

```bash
python3 references/upstream/storage/2026-10-22_external/migrate.py relink
```

This verifies the disk identity and refuses to replace any existing directory.
The `copy` and `switch` phases are retained as migration evidence and are not
needed for ordinary use. Current research commits stay local under
`docs/agents/git-workflow.md`.
