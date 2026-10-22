# Remaining failure boundary

A02is a measured native SupportGap, not merely a rounded-cell artifact. Its
post-PD start must not be made executable by soft margin or endpoint tolerance.
A02nominal/measured actual installed graph replay and support verdicts are in
results/measured_start_replay/summary.json.

G07's final local round has four seed failures, no optimizer/refinement/final
check, and1.905mswall time. At least one candidate endpoint is occ=0; several
shorter ones are occ=1. The robot's actual support query is Free. None of these
facts proves the connecting edge or planning yaw is free. A throttled remote
UnknownObstacle query is a rejected future candidate, followed by a different
selected local frontier; it is not the root cause. The final global shared
review reports two refused directed poses without recording their coordinates.

Minimal next diagnostic: capture one failed local search round's measured
start/yaw, actual target, revision/stamps, first refused edge, sampled point,
planning yaw and typed verdict. Preserve the two refused global poses/verdicts.
Replay this owned failure window using the existing C++ path, then change only
the general faulty mechanism. Do not add endpoint anchors, component branches,
future-target exceptions or reduce0.35m. No new repair or physical retry is
claimed by this report.

Primary source pointers: v238scan_replan_fsm.cpp451–494; v247
scan_reactive_grid_methods.inc573–578; v202planner_manager.cpp352–357;
v240dyn_a_star.cpp404–407. Exact G07captured line ranges and log SHA are
saved in results/G07_failure_log_excerpts.json. SEARCH_ERR=2is a seed-stage
failure, not a whole-map no-route theorem.
