# v284 static mission continuity

Dr Sun directly authorized implementation and execution on 2026-10-19. Work
inline without sub-agents. This is a new candidate; frozen v283 stays intact.

## Requirements

1. Remove v283's local source-field hard veto and forced measured-seed warm
   reset. Preserve live obstacle/freshness/epoch checks and genuine support-gap
   refusal. WrongHeight during a supported static stair traversal is diagnostic,
   not a reason to destroy an admitted mission or local continuation.
2. Retain the first admitted global static-building reference for the same goal
   and mission, trimming passed prefix only. Local hint/replan events must not
   trigger a new global search with a moving start. Goal change/cancel still
   resets ownership. Initial illegal requests still refuse.
3. Couple translation and heading during travel, removing nonterminal in-place
   yaw and phase freezing. Final yaw alignment is confined to the existing
   terminal capture region. Add shared smooth source-solid repulsion extending
   through 0.35--0.42 m absolute clearance; hard radius remains 0.35 m.
4. Keep the frozen v283 50+3 cohort, all uniformly certified starts and same ten
   route identities. No scene/route/coordinate production special cases. Keep
   sensor period/deadline 0.1 s, policy, PD, geometry and goal tolerances.

## Acceptance and execution order

- Build and regress actual route lifecycle, local query/optimizer and command
  owners; translated/rotated cost/command tests and positive collision controls.
- Freeze source/install/cohort/evaluator before the 53 scored offline calls.
- Run all 50 legal plus 3 illegal cases. Require >=48/50 legal full-chain passes,
  3/3 illegal refusals, report independent hard geometry and global median,
  initialization/p95/max. Target median around 1.3 s; admission ceiling 1.5 s.
- Only after returned passing offline gate, run A04,G05,CU06,D07,S04,CD12,CM02,
  CM07,CS03,CE03 once each in Newton. Startup rejection before physics is retained
  and excluded. No outcome-seeking physical retries.
- Deliver complete report, arrival/PD, stalls, nonterminal pure yaw, support and
  source/raw solid margins, scanner deadlines and ten full real local MP4s with
  source/hash/decode/coverage and visual checks. Report failure as failure.

No baseline promotion, automatic commit, policy training or real-robot work.
