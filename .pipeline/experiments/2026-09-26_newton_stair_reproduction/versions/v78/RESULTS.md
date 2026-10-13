# v78 map-processing diagnosis

Stage: experiment + analysis. Frozen diagnostic child of v76/nativev63;
observation scopes/counters only. No production or simulator/stop/safety change.
Currentv48 stays the reference and v49 stays excluded.

Two native map dependencies and both unmodified/instrumented executables build.
Three runs per arm replay188original scans with exact paired support assets.
All six final occupancy/inflation/ray/count/origin/history digests match. All116
selected current/snapshot source identities pass; observation removal recovers
exact parent map source. Actual wire pose/cloud widths and planner configuration
match the prepared seven-scan witnesses.

The original976.721msinput scope contains12refreshes/7newscans,941.490msthreadCPU.
Replay identifies occupancy fusion/inflation as the main intrinsic cost:
926,950fusedvoxels,905,074occupancycalls,25,175,190inflationneighborvisits,
threeactualslides clearing474,416cells. Representative fusion163.691ms,
sliding57.719ms,projection/classification49.746ms,traversal37.653ms,decode0.416ms.
Unmodified seven-scan total266.600–312.992ms; original live977msisnotfully
reproduced. Historical native batching/map history, planner/cache context and
concurrent live workload remain unseparated. No causal live speedup,30Hz,full
navigation/safety/continuity qualification or production fix is claimed.

Original raw and full profiling results stay remotely hash-verified; compact
report/selected results/source/provenance stay local. Temporary inputs/builds
are removed only after proof. Preserve the two unfrozen preflight errors.
See [diagnosis/report](../../audits/2026-10-05_map_processing/REPORT.md),
[summary](../../audits/2026-10-05_map_processing/profile_summary.json) and
[storage](../../audits/2026-10-05_map_processing/storage.json).
