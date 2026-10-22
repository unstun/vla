# v286 supported-air and local refinement repair

## Authorization
Dr Sun explicitly requests implementation and complete execution of v286. Parent v285 is immutable. No subagents. Local VLA repository remains source of truth; remote copies execute only.

## Requirements
Supported, in-map, uninflated unknown air must not reject local motion when the existing support/edge/height checks and exact static solids permit it. Observed/inflated obstacles, missing support, gaps, out-of-map and stale inputs retain refusal. Terrain endpoint projection must use local feasible headings rather than a quantization-residual connector; target-neighborhood recovery must use terrain-supported local search. Refinement must avoid the environmental objective that creates repeated line-search failures while rebound and final collision review retain their roles. Coupled travel translation and phase must make progress without returning to pure-yaw travel. Local rebound should keep a 0.05–0.06 m source-solid soft buffer.

Keep exact 0.35 m hard geometry, 0.1 s scanner period/deadline, global route retention, factory PD/policy, unchanged cohort and start certificates. No scene/route/coordinate navigation branches. Preserve all earlier source, failures and videos.

## Acceptance
Run the complete frozen 50 legal +3 illegal cohort once, with legal >=96%, illegal refusals3/3, global median <=1.5 s and independent geometry review. Recheck all50 legal starts. Only after that gate, run A04/G05/CU06/D07/S04/CD12/CM02/CM07/CS03/CE03 once each, retaining v283 start replacements. Deliver actual goal/PD, full-recording measured support/source/raw geometry, progress/pauses, scanner timing, identical error counters and ten complete real videos. Distinguish development/native tests from scored runs, startup rejection from positive physics, and arrival from geometry. No success retries, baseline promotion or automatic commit/archive.
