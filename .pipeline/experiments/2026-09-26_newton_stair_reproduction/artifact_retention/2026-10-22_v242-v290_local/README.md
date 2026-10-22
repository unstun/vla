# v242–v290 local commit and evidence retention

Date: 2026-10-22. Dr Sun authorized local commits, state synchronization and
task closeout, preserving all experiments and failures, with **no GitHub push**.
This is repository maintenance, with no navigation changes or new experiments.

## What is saved

- All 49 version directories v242–v290 and 18 corresponding audit directories
  were inventoried before editing. The 23,010 existing files total
  1,593,758,180 bytes. No existing file in those directories is rewritten or removed.
- 16,684 source/configuration, compact result, test receipt and review-image
  files (137,994,881 logical bytes before Git deduplication/compression) are
  selected for Git. Original task records and six associated spec files are
  included in the same local research commit.
- 6,152 videos, full logs, sample streams and larger generated artifacts
  (1,454,578,994 bytes) stay at their **existing local paths**. Every path, size
  and SHA-256 is in `local-files.jsonl`. The experiment-scoped `.gitignore`
  lists only those exact paths. The 174 existing Python cache files also stay
  in place under the existing cache exclusion.
- `source-verification.json` records 42 frozen manifests and 2,494 declared
  source entries, all matched to their direct files or explicit frozen snapshots.
  Some manifests include build logs: those remain local and are inventoried,
  so a source-only checkout needs the retained payloads for the full legacy gate.

The first commit records the experiment state before task archiving. A later
commit records closeout/status updates. Neither makes a failed experiment pass.
The accepted v232 source / v233 execution baseline remains selected.

## Verification and recovery

From the repository root:

```sh
python3 .pipeline/experiments/2026-09-26_newton_stair_reproduction/artifact_retention/2026-10-22_v242-v290_local/verify.py
```

This verifies local retained payloads and the declared frozen sources. It does
not rebuild ROS, rerun tests/physics or validate a remote backup. Existing remote
locators are indexed in `historical-locators.json`; their availability was not
rechecked. In particular, historical host names do not certify current hosts.

Git alone does **not** back up the retained payloads. To copy their exact current
bytes to a chosen backup directory, run from this repository root:

```sh
rsync -a --files-from=.pipeline/experiments/2026-09-26_newton_stair_reproduction/artifact_retention/2026-10-22_v242-v290_local/local-files.txt ./ /ABSOLUTE/BACKUP/vla/
```

To restore from that backup, reverse the source and destination and run the
verifier again. No backup copy or restoration was performed by this closeout.
For retrieval from an original remote execution directory, use its indexed
historical locator and require the recorded SHA-256; do not rerun physics to
replace historical evidence. No compression, relocation, deletion, Git history
rewrite, baseline promotion or remote push is part of this work.
