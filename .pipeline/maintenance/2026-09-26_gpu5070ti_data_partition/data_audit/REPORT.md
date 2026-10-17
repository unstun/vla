# Old research data backup comparison

## Final disposition: approved selective rescue and erasure

The later instruction from Dr Sun was to make the approximately 5 GiB rescue
first, then clear the entire old volume. On 2026-09-26 the Mac independently
verified all 25,561 selected regular files and 10 links before the old filesystem
was erased. Its range is now the ext4 `/data` partition. See
`../RESCUE_README.md`, `../RESCUE_LOCAL_VERIFIED.json`, and
`../runtime_result/RESULT.json` for the preservation boundary and results.

This authorization and verified selective rescue supersede the earlier pending
decision below. Full cloud coverage of excluded old data was never established.
All remaining sections are historical audit findings from before erasure;
statements that no data had been deleted refer to that earlier audit stage.

## Update after Google Drive reauthorization

The original gdrive-phd connection was successfully reauthorized. Live provider
metadata for all 2592 objects covered by the September archive receipts matches
the recorded sizes and hashes. Two extra objects are obsolete split-v1 metadata
files; there are no mismatches or missing receipt objects. See
CLOUD_REVALIDATED.json and CLOUD_AUTH_RECOVERY.json.

Two separate backups were also discovered at the Drive root, outside that
September archive tree: DQN8_runs_20260521.tar.zst (24.319 GiB) and
DQN9_runs_20260521.tar.zst (37.866 GiB). Thus the earlier search did not establish
absence of a DQN8 cloud backup. A bounded 32 MiB compressed-prefix read of DQN8
successfully parsed and hashed 325 complete archive members. None of that
prefix's files matched the old-volume hashes; this sample cannot establish
whether later archive members cover the old files. The deliberately truncated
prefix ends inside a member; its premature-end decoder status is expected and
does not imply the full cloud archive is corrupt. Temporary sample bytes were
removed after recording DQN8_PREFIX_SAMPLE.json.

The original comparison below remains accurate for its stated local-file and
September-manifest scope. Its earlier authentication limitation is superseded.
Full coverage of the old filesystem, especially DQN8, still requires an entire
archive member/content comparison before deletion can be justified on backup
grounds.

## Conclusion

The old research tree is not established as redundant. A SHA-256 comparison
confirmed current Mac copies for only 0.888 GiB of its 58.386 GiB logical file
contents. Do not erase the old filesystem based on the assumption that all
research data is already local.

The largest unresolved directory is DQN8: 49.781 GiB had no identical-content
match in the searched local candidates or historical per-file hash manifests.
This is not proof of global uniqueness: renamed files, archive contents,
unreachable Git objects, other locations, and cloud-only files remain possible.

## Measured coverage

| Category | Files | Bytes | GiB |
| --- | ---: | ---: | ---: |
| Current Mac file with identical SHA-256 | 1600 | 953602589 | 0.888 |
| Historical archive path and size match only | 19733 | 5092421661 | 4.743 |
| No match established | 27623 | 56645894839 | 52.756 |
| Total old regular research files | 48956 | 62691919089 | 58.386 |

The raw byte total is authoritative in SUMMARY.json and the sum of the three
coverage categories; the comparison never treats path/size equality as a
content match. Detailed per-file results are in comparison_details.jsonl.gz.

## What takes space

- 23767 .pt weight files occupy 55.233 GiB.
- 23395 weight files under checkpoints or periodic directories occupy
  53.431 GiB. These path labels identify candidates for retention review,
  not automatic deletion permission.
- 372 weights outside those directory categories occupy 1.802 GiB.
- Other research files occupy 3.153 GiB, including code, configurations,
  metrics, maps, figures, documents, Git data, and some download leftovers.
- A separate old /home/sun/phdproject.zip is 57698484302 bytes (53.74 GiB).
  Its central directory has 68147 entries. It is another copy on the same old
  filesystem, not an independently verified off-volume backup. Archive
  contents were indexed but not fully decompressed and hashed.

A selective preservation plan could begin with approximately 4.955 GiB of
non-periodic-directory material, then add the required final/best checkpoints
per experiment. That is a candidate plan, not a verified minimal complete
research backup.

## Local and cloud boundaries

The search covered /Users/sun/tongbu/study, Documents, Downloads, and Desktop:
708391 regular-file metadata candidates were inspected and 7590 matching
basename/size candidates were hashed (1913093359 bytes), with no read errors.
Generated environments, caches, node_modules, and .git directories were
pruned. This means renamed files and Git-object-only payloads are not
exhaustively covered.

The historical DQN9/DQN10 per-file SHA-256 manifests were searched across
directory names. They produced no additional content-hash matches for this
old tree. The full-tree manifests for RL_sac, dqn3, dqn, and DQN6 do provide
some matching paths and sizes, but do not have original per-file hashes.

The Mac's /Users/sun/tongbu/study/phdproject/dqn no longer exists. The
2026-09-12 offload records report deletion of local source trees after cloud
transfer. The retained full_tree directories contain manifests, receipts,
and restore instructions, not the archive payload shards.

Current cloud recovery was not verified: the connected Google Drive tool
could not access the historical folder ID; the original gdrive-phd rclone
connection failed with invalid_grant. This does not prove deletion of the
cloud data. Authentication was not changed.

The actual local /Users/sun/tongbu/study/phdprojec/dqn contains about 547 MiB
of earlier code and models. dqn9paper contains about 78.6 MiB of paper assets;
ugv-global-planning is a later research/code scaffold. Neither establishes a
complete backup of the old research tree.

## Evidence

- SUMMARY.json: old-volume scan and archive inventory.
- old_research_manifest.jsonl.gz: full old research SHA-256 and MD5 list.
- old_archive_entries.jsonl.gz: old zip central-directory metadata.
- COMPARISON.json and comparison_details.jsonl.gz: actual comparison results.
- CLOUD_CHECK.json: live cloud-verification limitations.
- Historical sources:
  /Users/sun/tongbu/study/phdproject/machine-dog/artifacts/2026-09-12_dqn_google_drive_offload/.

The old filesystem was mounted read-only with journal replay disabled and
unmounted after the scan. No old data was deleted and no GPT entry was added.
