---
origin: ai_only
reviewed: false
status: surveyed
date: 2026-10-16
---

# PCT–SCAN stair failure attribution

**The recent failures do not establish that PCT or SCAN is inherently unsuitable
for stairs. They expose local coordination and locomotion-transition defects,
plus unresolved interactions between the modified terrain/collision contract
and the native planner.**

The [detailed audit](../../references/upstream/2026-10-16_pct_scan_origin_audit/comparison.md)
compares the author PCT `35cd73f`, author SCAN `348e8a5`, imported community
PCT-SCAN-ROS2 `1cf45a1`, and the current v219 executable source receipt.
All 136 selected local planner source/config files resolve to matching local
frozen hashes. This review updates the earlier discussion that stopped at v208.

Decisive findings:

1. Author PCT explicitly models multi-layer terrain, step limits and standable
   neighborhoods; author SCAN consumes 3D ground routes, applies body height,
   uses projected search and preserves vertical trends. Their source and author
   experiments include stairs. Neither supplies Lite3 locomotion feasibility.
2. The community Building demo actually disables local sensing by default and
   warns that enabling dense stair clouds can cause collision inflation and
   emergency stops. Its animation is not proof of sensor-driven physical stair
   navigation. This is an inherited integration gap.
3. Our collision queries add unknown/input-age/support/floor checks and larger
   geometric inflation. Our timed-curve acceptance adds a minimum-cruise rule.
   These change the feasible set; they are not merely ROS portability edits.
4. v212 removed periodic global refresh without a native local-failure signal
   to the route owner. v217's expiry recovery was late. v219 adds route-bound
   continuous-failure reporting and passes one full route without changing the
   parent native geometric algorithm. This is direct integration evidence.
5. The local v208 standing transfer lacked supported admission and immediate
   disturbance abort. Rerunning the existing 14-test suite produces 35 failed
   assertions/subtests on v208 and zero on v216, with zero errors on both.
   These are component replays, not new physical experiments.
6. Archived runtime logs show geometric/A-star rejection in the failing stair
   windows. The added minimum-cruise dynamic-limit rejection is observed in
   successful v210/v219 windows but not the sampled v212/v217 windows; it is
   not established as the main cause of those failures.

Recommendation: retain the current baseline and perform a same-captured-input
comparison of original versus local collision decisions before replacing the
algorithms. Identify terrain, unknown, footprint, support and speed effects
separately. Original acceptance alone would not prove physical feasibility.

No navigation source, frozen version, acceptance threshold or adopted pointer
was changed. No new simulation, policy inference or robot run occurred. See the
[manifest](../../references/upstream/2026-10-16_pct_scan_origin_audit/repository_manifest.yaml)
for pins, commands, dependency/license boundaries and returned evidence.
