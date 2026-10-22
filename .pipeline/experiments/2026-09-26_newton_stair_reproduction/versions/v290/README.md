# v290 terrain-continuous local search and terminal approach

Parent: immutable v289. Local repository is the source of truth; ultra9 /home/ubuntu/sun/vla_v290_20261021 is a private execution copy.

## Native change boundary
- Exact A-star endpoints and checked terminal connector are unchanged. Available selected terrain supplies interior node heights. Obstacle retreat stays support-aligned instead of disabling terrain mode.
- Selected-tread risers are classified using the same adjacent-height interval from either side. A source voxel entirely below the query-associated selected support surface cannot inflate upward through it. Raw occupancy and nonterrain history remain intact. Above-floor/unassociated obstacles, support gaps, unknown/stale inputs and map bounds retain refusal. Unscored physical floor presence is not classification permission.
- The existing position gain limits terminal approach speed before the original capture band. Only this additional binding speed ceiling slows phase. Original yaw coupling, slew,0.25m XY/0.20m Z capture and measured PD completion remain.

Radius0.35m, scan/deadline0.1s,0.35s cloud freshness, original body freshness, global reference ownership, ENV225, factory policy/PD and all53 inputs remain unchanged. No route/coordinate/scene predicates or exact source mesh calls were added to the local hot path.

## Qualification and claim boundary
Fourteen-package native build and functional suites, focused parent/candidate tests and captured-input comparisons are required before freezing. Inherited Nav2 cpplint/uncrustify/xmllint checks remain explicitly separate. The new exact-hill search passes2/2 directions against0/2 on the parent. Eight captured failed requests pass with precise endpoints only after the terrain/contributor repairs; the original parent and terrain-only development candidate pass0/8. The captured comparison uses synchronous mapping, measured starts and rounded logged targets, not identical asynchronous FSM state or new physics.

The actual Controller/LocalMotion/TrackingNode replay demonstrates earlier terminal slowdown on unchanged recorded CD12 poses. It cannot certify a new measured trajectory or eliminate the4.6cm recorded crossing retroactively.

Run the unchanged50+3 criteria: legal>=48/50,illegal3/3 refusal, admitted global median<=1.5s, required independent source/raw and local curve audits. Keep component, offline and physical results separate. Each new physical route runs once after the scored gate. Frozen navigation is immutable; reports and videos are later evidence artifacts.

Evidence: audits/2026-10-21_v290_terrain_terminal/ultra9 and the Trellis task10-21-v290-terrain-terminal. No baseline promotion is implied by the version number.
