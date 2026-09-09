# Local archive report — 2026-09-09

Requested by Dr Sun before quota exhaustion. Main continuation entry:
[`2026-09-09_vla_lightnav0_handoff.md`](2026-09-09_vla_lightnav0_handoff.md).

- Archive execution: one inherited-model archive worker refreshed the hot/cold
  memory files while the lead wrote the handoff, indexes and backup manifest.
- LightNav status remains **prepared_not_dispatched**. No inference, model
  download, remote setup, navigation run or experiment dispatch was performed
  during archival.
- Frozen preparation integrity: **18/18** package/input files still match their
  preparation manifest. The previously verified 2,236 scene-asset checks and
  2,459 source-file identities remain recorded; archival did not rerun inference.
- Hot memory budgets: state **850 characters / 24 lines**; open decisions
  **620 / 15**; recent changes **471 / 14**. All pass the configured limits.
- Previous hot-zone contents are preserved byte-for-byte in
  `bigmemory/冷区/改动记录/2026-09-09_075521_pre-lightnav-hot-zone/`; **3/3**
  snapshot hashes passed. Older OmniVLA decisions were not discarded or closed.
- New source-backed cold record:
  `bigmemory/冷区/调研记录/2026-09-09-lightnav0-package-and-navigation-evidence.md`.
- `.pipeline` literature/experiment indexes now link LightNav preparation.
  Existing unrelated edits are preserved; the backup stages only this archive's
  focused index additions, not their prior uncommitted changes.
- Independent CLI gate: first attempt rejected the skill's obsolete
  `--full-auto` flag; a supported read-only retry returned a context-insufficiency
  FAIL and exceeded its 40-second deadline during MCP shutdown. The supplied
  summary omitted the exact host and local import path. The lead checked both
  against saved source hashes and SSH evidence. Entries retain a pending-gate
  marker; **no automated PASS is claimed**. Transport diagnostics were sanitized
  before backup to exclude possible connector authentication material.
- Manual checks: JSON parsing, source paths, old-state hashes, frozen preparation
  hashes, hot-zone limits and owned Git diff. No dedicated project harness
  validator was located by the targeted script-name search.
- Cold degradation: no dated record has reached 31 days; no aging/merging needed.
- A short user-authorized global memory extension points to this handoff:
  `/Users/sun/.codex/memories/extensions/ad_hoc/notes/2026-09-09T07-56-04-vla-lightnav0-local-handoff.md`.
  This is outside the project Git repository.

The local backup includes only the new LightNav preparation/provenance/task,
archive-owned memory/handoff files and focused index additions. Raw weights,
source clones, prior large experiment outputs and unrelated dirty files are not
newly staged. These remain at their existing local paths. No Git remote is
configured; nothing is pushed. The backup commit is the Git commit containing
this report (`git log -1 --format='%h %s' -- <this report path>`).

Validation and the explicit staged path manifest are in
`2026-09-09_vla_archive/`. Resume through the main handoff; archive completion
does not imply experiment completion or lead acceptance of an Opus result.
