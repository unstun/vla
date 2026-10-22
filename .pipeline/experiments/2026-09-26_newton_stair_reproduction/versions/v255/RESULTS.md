# v255 — One successful A02 physical regression on frozen v254

The single authorized attempt passes the original full-route and terminal PD
gates without moving the A02 start/goal or changing RL, 0.35 m or 0.1 s settings.
FINISHED at 112.589752 s; final XY error 0.108795 m, height error 0.006334 m,
measured PD suffix 4.397583 s. The full cross-floor window, 21.000088–98.897278 s,
has zero pauses >=0.5 s / >=1 s, 2144/2162 successful local rounds, 780/780 native
Free body queries and minimum gap-aware ENV extra-edge margin 0.091264 m.

Whole navigation retains two long low-speed intervals (initial wait and terminal
settling), 2474/2494 local success and 984/984 body queries Free. All 1016 scans
complete; maximum 31.726624 ms, no deadline failure. No emergency, fall or
process failure. Sustained 30 Hz is unvalidated (24.355 successful wall Hz).
No physical retry is performed.

The full recording and explicitly held-old-prefix comparison are regular files
in `../../audits/2026-10-18_v253_continuous_endpoints/delivered/`. The detailed
report and local/causal decode/hash checks are in that audit. G07/R11 retain
their v252 physical controls; they are not new v254 runs. The frozen execution
manifest retains its pre-physics scope. Selected baseline remains v232/v233.
