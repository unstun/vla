# v252 — physical execution of frozen v251

Three explicitly authorized single attempts on gpu5070ti, no retry:

- A02 FAILED before route movement: `pct_no_route`. Measured continuous body
  support passes, but its PCT discrete start searches only 18 unique grid nodes.
- G07 PASS: complete ascent/new upstairs goal, recording end 137.810 s,
  final XY error 0.1174 m and measured final PD 4.411 s.
- R11 PASS: complete reverse descent, recording end 119.506 s,
  final XY error 0.1314 m and measured final PD 4.298 s.

Both successful routes have zero >=0.5 s or >=1 s pauses in the full cross-floor
interval. Each retains two whole-navigation low-speed episodes, at initial
planning wait and terminal settling/stand. Local round success is 3263/3294
(99.06%) and 2695/2709 (99.48%); sustained 30 Hz remains unvalidated.
All 2439 scans complete with zero deadline failures; maximum 29.184 ms.

Native v251, frozen v248 bridge, original v216 RL/PD, v237 scanner, scenarios,
0.35 m hard radius and 0.1 s scan/deadline remain unchanged. Three zero-step
preflights, actual ACTIVE-before-goal, installed/source verification and loaded
library provenance pass. No fall or process crash. Physical verification is
separate from outer process success and display qualification.

All three full recorded attempts are returned as regular MP4s, including the
A02 failure. [Full report](../../audits/2026-10-18_v251_physical_generalization/RESULTS.md)
and [videos](../../audits/2026-10-18_v251_physical_generalization/delivered/README.md).
The cohort is 2/3 full-route passes, with A02 unresolved. Task remains open;
selected baseline v232/v233 is unchanged. No commit or archive in this follow-up.
