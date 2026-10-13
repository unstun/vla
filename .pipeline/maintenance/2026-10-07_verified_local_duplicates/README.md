# Verified local duplicate removal

Dr Sun authorized removing local bulk files that already have identical copies on gpu5070ti. The local repository remains the source of truth for code and configuration. Remote payloads were not modified.

Every entry in `manifest.json` records the exact restore location, byte count, full SHA-256, and removal status. Both copies were freshly hashed before removal; only untracked regular files with no local open handles were selected.

Keep model payloads on the server for remote execution. To restore non-model data when needed, create its original parent directory and copy the recorded `gpu5070ti:<remote_path>` to `local_path` with `scp`. Verify the recorded SHA-256 after transfer. Historical verification receipts describe their original snapshots and are retained unchanged.

## Verified result

Removed 42 untracked local payloads, totaling 14.48 GiB of allocated-file accounting. Actual APFS free-space changes are recorded separately. Code, configuration, review videos, tracked files, and unmatched payloads were retained.
