# Newton v36–v46 archive

Archived on 2026-10-01, America/Los_Angeles. Stage: experiment + analysis.
The local VLA repository is the source of truth; gpu5070ti is an execution copy.

The requested local 30 Hz and simulation 1:1 gates remain unmet. Actual v45
local planning was 16.8619 Hz, raw controller 29.9648 Hz, actual global PCT
0.99998 Hz and navigation RTF 0.9400. The run ended on
`global_refresh_failed:pct_no_route`, without Building arrival. v46 delivered
an ordinary 57-second video on the recorded wall timeline. Video playback at
30 FPS establishes neither local 30 Hz nor physical simulation 1:1. CPU graph
execution was adopted after exact CPU trace qualification; CUDA was not adopted.
Performance proposals are recorded, but v47 does not exist.

## Read and resume

- [Session facts and pins](SESSION_SUMMARY.md)
- [Timing experiments and failed acceptance gates](../../experiments/2026-10-01_newton_nav2_timing_archive.md)
- [SCAN paper and author-code frequency check](../../survey/2026-10-01_scan_planner_frequency.md)
- [Local-planner optimization proposal](../../experiments/2026-09-26_newton_stair_reproduction/audits/2026-09-30_local_30hz_opportunities/PLAN.md)
- [Delivered ordinary video](../../../output/2026-09-30_lite3_realtime/v45_actual_wall_57s.mp4)
- [Quality-gate receipt](quality_gate.json)
- [Explicit backup scope](backup_scope.json)
- [Local-only byte inventory and recovery](LOCAL_ONLY_BYTES.json)
- [Original hot-state snapshots](history/)

## Archive receipt

Four archive agents started successfully with default model inheritance. The
facts agent wrote five change and six pitfall entries; the decisions agent
wrote research and rationale records; the hot agent rewrote all three hot
documents. The pipeline agent completed drafts and degradation inspection;
its final follow-up failed at model capacity, so the root finalized the four
pipeline writes from the reviewed drafts. No implementation or experiment was
delegated as part of this archive.

Hot budgets passed: state 1,090 characters / 22 lines; open decisions 930 / 16;
recent changes 688 / 22. Four cold files were created. Preferences and workflow
were unchanged. Literature, experiment and survey entries were added;
terminology and milestone records were unchanged. No cold files newly crossed
a degradation threshold; only the inspection date/receipt changed. The old
hot documents were preserved before rewriting. No full chat export was made.

The requested Codex quality check was attempted with CLI 0.153.3 but failed
before model execution: `failed to initialize in-process app-server client:
Operation not permitted (os error 1)`. New pipeline entries explicitly carry
**[未门控]**, with `reviewed: false`. Root factual review against actual rate
records, video hash and proposal boundaries passed; it is not an independent
Codex verdict or human acceptance. Only summary and proposed entries were
supplied to that attempted check; private robot assets were not supplied.

## Backup and preserved exclusions

The local backup uses an isolated Git index seeded from the original HEAD,
with an explicit per-file path list. For `.gitignore`, literature/experiment
indexes and degradation state, only this archive's added content/date fields
are committed; earlier unrelated dirty content remains in the working tree.
The two preexisting staged v34/v35 `LOCAL_ONLY_BYTES.json` blobs are recorded
in [original_staged_entries.json](original_staged_entries.json) and remain staged.
HarnessVLN, `.trellis`, older cold records and other unowned Newton artifacts
are excluded. There is no Git remote; the backup is local only. The archive's
commit can be identified with `git log --all --grep='备份：Newton v36-v46'`.

The inventory accounts for 8,517 files / 6,467,900,683 logical bytes preserved
locally, including raw captures, installed native products, view derivatives
and render frames. Some paths share bytes; this is not unique disk usage.
Original sensor/physics observations cannot be recreated bit-for-bit simply
by rerunning simulation. Their exact local storage and SHA-256 are retained.
Source snapshots, configurations, result/qualification receipts, selected logs
and the delivered MP4 are included in the backup scope. No model, video, raw
record or frozen source was deleted or overwritten.

Next work remains a reviewed new-version design for local-window reuse,
previous-trajectory initialization and a total attempt budget, plus separate
diagnosis of global `pct_no_route`. This archive launches no further run,
training, robot actuation, Trellis task or v47 implementation.
