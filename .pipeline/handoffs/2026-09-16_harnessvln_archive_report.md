---
origin: ai_only
reviewed: false
date: 2026-09-16
---

# HarnessVLN Local Archive Report

Requested explicitly by Dr Sun. Main continuation entry:
[HarnessVLN local archive](2026-09-16_harnessvln_local_archive.md).
Stage remains experiment + analysis; the overall task remains in progress.

- Three archive workers inherited the parent model and independently handled
  cold facts/decisions, hot-zone compression and pipeline discoverability. The
  lead reviewed their changes and owns verification and the local Git backup.
- Change, pitfall, rationale and bounded diagnostic-milestone records were
  written to the four `bigmemory/冷区/*/2026-09-16.md` entries. No new literature,
  survey or terminology claim was introduced.
- The three prior hot-zone files were preserved byte-for-byte in
  `bigmemory/冷区/改动记录/2026-09-16_2129_pre-harnessvln-hot-zone/`. New hot-zone
  counts are 1171/19, 854/13 and 733/11 characters/lines. All meet their budgets;
  recent changes contain three entries for the day. Earlier MIP, InternVLA,
  camera and historical decisions remain discoverable and were not closed.
- Three records newly reached 31 days. Only summary headers were added;
  their original text and pre-edit hashes were preserved. No records were
  deleted or merged. Preferences/workflow files do not exist in this memory
  layout; no speculative replacements were created.
- Fresh archival verification matched **207/207 returned files across seven
  runs**. The native comparison was recomputed from saved artifacts and all
  nine checks still passed. No remote experiment was launched.
- The local [evidence bundle](2026-09-16_harnessvln_archive/evidence.tar.gz)
  contains **374 files**, 627,303,376 source bytes compressed to 233,634,523 bytes.
  Every archived member and the archive SHA-256 were verified. The tracked
  [manifest](2026-09-16_harnessvln_archive/evidence_manifest.json) records exact
  paths, sizes and hashes; the adjacent creation script records regeneration.
  One exact-path ignore keeps this large local bundle out of Git. The bundle
  does not claim to distribute the full Isaac/ROS runtime or all dependencies.
- Independent CLI knowledge review used `gpt-6-astra`, read-only and ephemeral,
  without loading user configuration. Two initial FAILs identified details
  omitted from the summary; the lead checked the actual source/configuration
  records and supplemented it. The third verdict was PASS with an explanation.
  All attempts remain recorded; the parser normalized the unambiguous PASS
  prefix while retaining the original response. No model fallback was used.
- A user-authorized global memory extension was written at
  `/Users/sun/.codex/memories/extensions/ad_hoc/notes/2026-09-17T04-45-00-vla-harnessvln-scan-local-archive.md`.
  It points to this archive and preserves the validation boundary. It is outside
  project Git; the main global memory files were not edited.

The local Git backup includes this archive's documentation, manifests, memory
changes, small diagnostic/recheck source, selected experiment summaries and
the owned task metadata. Original runtime directories and the verified bundle
remain available locally. Unrelated InternVLA source changes, literature-index
edits, media/arrays, upstream clones and other unfinished work are not newly
staged by this archive. See the explicit path list and validation in
`2026-09-16_harnessvln_archive/`. Nothing is pushed externally.

The backup commit is the commit containing this report:

```bash
git log -1 --format='%h %s' -- .pipeline/handoffs/2026-09-16_harnessvln_archive_report.md
```

Archive completion does not mean the candidate repair was adopted. Production
materializer and scan_03 remain unchanged, corrected Isaac navigation is still
unvalidated, and language/grounding/SLAM/physical deployment remain open.
