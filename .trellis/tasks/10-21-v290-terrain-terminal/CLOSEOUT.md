# v290 delivery complete — repair review remains open

Date: 2026-10-22. Source/evidence commit: `77d4ca08e09d23f8193d9e7b9ca81de773669f34` (local only).
Status: `review`. Delivery is complete; **overall physical acceptance failed**.
No experiment is asserted to be running, and housekeeping authorizes no new run.

[Original complete report](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-21_v290_terrain_terminal/ultra9/RESULTS_zh.md)
records 49/50 legal calls, 3/3 illegal refusals, 1.361381101 s median, 6/10
arrival plus PD and 4/10 also passing sampled geometry. There are two scanner
deadline failures and no native signal crash. Preserve all ten once-only attempts.

## Remaining review

1. Unify outer Controller goal braking and tracker terminal centering. The outer
   `goal_braking_` path bypasses centering; early speed limiting alone failed.
2. Check measured intermediate yaw and PD transition drift with the unchanged
   source geometry, including D07/CD12 excursions; a valid final pose does not
   validate the approach or heading sweep.
3. Diagnose G05/CS03 scanner deadline failures, retaining CS03's earlier solid
   excursion and the original shared-host resource conditions.
4. Keep local-search/solver failures, sustained timing and repeated reliability
   as open requirements. A new implementation must receive a new version.

The eight v242–v289 delivery tasks are archived with failed acceptance and
linked here. Their original states are recoverable from the source/evidence
commit. The accepted baseline stays v232/v233. No push or baseline promotion.

[Project closeout and original-report table](../../../bigmemory/冷区/里程碑/2026-10-22_v242-v290-local-closeout.md).

## 2026-10-22 stop-timeline follow-up

[D07/CD12 recorded-stop analysis](../../../.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-22_v290_stop_timeline/REPORT.md)
completed the first item in the visual convergence plan. D07 stops through an
emergency spline while its goal yaw is still wrong; CD12's threshold crossing
and source call order identify outer Controller braking before continued XY
centering. Both first geometry crossings precede the all-zero applied command.
Maximum later XY displacement is 23.87/21.26 cm, with 12.573/4.557 s waiting
before PD transition. Most displacement occurs during RL-owned STAND_SETTLING,
not after fixed PD has taken over. Fourteen raw-source identities match.
No controller modification or new physics run occurred. Keep repair review open.
