# Final planning review

Goal: repair safe continuation through the 43-second corner and test actual 30 Hz
planning. Plan ready; implementation and physics have not started.

| Order | Planned version | Change |
| --- | --- | --- |
| 1 | v53 from v52 | Exact requested-goal identity, transactional compatible refresh and geometric feasible-window reprojection; full curve/connector checks retained. |
| 2 | v54 from qualified frozen v53 | Apply newest queued input before recovery admission; 250 ms freshness limit retained. |
| 3 | v55 from qualified frozen v54 | Separate physical floor presence from traversal selection for drop/neighbor evidence; central costs and obstacle classification retained. |

Each version builds and passes inherited/new native regressions before freezing
and becoming the next parent. Integration acceptance contains two bounded 90-s
idle-host gpu5070ti trials, complete latency/frequency/reserve/progress analysis,
corner passage and all safety negatives. Bulk data/builds stay remote; return
compact reports/plots and one finished review MP4.

Out of scope: v49 hard solve deadlines/stop mechanics, goal/yaw/PVA or safety
threshold relaxation, physics/locomotion changes, old-version overwrite, training
or real robot. Reference remains v48 until reviewed runtime evidence.

Key verified decisions: authoritative requested goal pose already exists and is
stable across refresh; snapped endpoint jitter is separate reference geometry.
PCT neighbor floors exist but cost 50 removes them from selected <=20 evidence;
physical-floor presence must be a separate role, not central traversal or a raw
obstacle waiver. Explicit cache invalidation/target_connector are local v47/v48
additions; upstream still chooses fresh polynomial init after reference refresh.
Legacy unqualified goal messages keep original refresh invalidation.

Risks/deferred claims: physical floor presence is not complete-body clearance;
negative layer/drop/obstacle/history fixtures must pass. Shared-host load may
block performance trials. Corner repair, strict 30 Hz and arrival remain separate
measured gates; no outcome is promised before testing.

Artifacts: parent and three children contain PRD/design/execution plans with
explicit dependencies. Research records pin upstream/source comparison and PCT
input hashes. Frozen native predecessor hashes remain unchanged. Inline mode
intentionally skips dispatch JSONL curation.

Next gate: approve this latest planning summary in a subsequent user message;
then start only the v53 child. Task-creation consent alone does not cross it.
