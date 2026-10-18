# v238: continuing-reference target selection

Parent native source/install: frozen v232, physically exercised by v237.
Execution host: gpu5070ti. Local VLA repository is the source of truth.

Remove demonstrated avoidable final-goal-neighborhood search on local rounds
that still have a valid forward reference proposal. Preserve new-route
admission, actual no-progress terminal recovery, original requested goal,
local horizon, minimum translation, RL,0.35 m collision/support guards,0.1 s
scans, cloud/body freshness, all native seed/spline/dynamic/publication gates
and the existing emergency/terminal/PD protocol.

Only src/plan_manage/src/scan_replan_fsm.cpp and its header change. Keep the old
three-argument overload and class layout so existing native controller/test
binaries can load the isolated replacement library. No new recovery protocol.

Verify full original scan prefix, actual target/optimizer seams, original
45–55 s and109–114.5 s windows, existing native regressions and short-pause metrics.
Do not promote offline timing to physically eliminated pauses. Keep all
remaining slow/rejected native calls visible. No new physical run authorized.

Rollback: use untouched v232 install/v237 host entry. Heavy input/build files
remain at /data/sun/vla_mppi_20261009/terminal_approach_v238. Rebuild with the
verified parent plus prepare_candidate.py/build.sh; replay.sh in the linked
audit runs baseline/candidate arms. Source/artifact hashes accompany results.
