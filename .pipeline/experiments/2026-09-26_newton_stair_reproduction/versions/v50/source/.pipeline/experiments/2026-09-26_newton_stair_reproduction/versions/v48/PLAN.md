# v48: remaining-trajectory warm initialization

Stage: experiment + analysis. Authorized by Dr Sun on 2026-10-01, including
gpu5070ti testing. No Trellis task; inline implementation and checking. Parent
v47 and its qualified trial02 remain immutable. Candidate 1 remains unchanged.

The manager currently always searches the graph. Add a first initialization
from its own last accepted moving curve, bound to current P2B run/epoch/request,
goal/route/command/generation/map identity and exact goal. The FSM supplies the
same current-curve relative time used for its original start PVA. Validate the
complete remaining curve against newest native occupancy/support, then sample
and refit it following the upstream remaining-curve pattern, retaining the
accepted curve timing. The first arc-resampled candidate compressed that timing
and every paired warm optimizer attempt rejected; its evidence is retained. An endpoint
extension uses only the existing checked native segment; unsupported extensions
fall back. Do not restore the upstream unchecked polynomial extension or Z rewrite.

The warm samples are an initial guess for a new hard-PVA fit, optimization,
dynamic retiming, minimum-cruise and complete fresh full-curve check. No old
trajectory is republished or restamped. Invalid identity, expired/regressed
clock, malformed curve, mismatched input PVA, missing support, new obstacle,
unsafe connector, route regeneration and emergency invalidate reuse. A failed
warm solve falls back to the original graph solve and fixed-height recovery.

Ownership: planner_manager header/implementation for seed preparation and
fallback; FSM header/implementation only for identity/time binding and
invalidation; version-specific wiring, dependency package, tests and evidence.
Final goal, yaw, PVA acceptance tolerances, dynamics, stair/map/collision rules,
controller, physics, policy, sensing and schedules retain v47. No solve-budget,
cross-callback cache, global-planner or diagnostic-serialization optimization.

Verification: hash parent/source parity; compile on gpu5070ti; existing native,
cache and cold-geometry gates; real-map warm seed and fallback lifecycle tests;
paired cold/warm starts with identical source curve/input PVA on recorded native
fixtures (not representative of all live v47 states). Freeze source/install and
all backend dependencies before a 90-native-second Building trial (360 s wall
bound) with the same 6-CPU quota. Verify live global refresh and goal contract.
Return every original file and SHA-check locally. Compare local attempt and
successful-new-plan rates, controller/global rates, solve median/P95/P99/max,
warm selection/fallbacks, overruns, slots, measured progress/pauses and RTF to
v47 trial02. Separate live trajectories limit causal timing comparisons.

Local source: /Users/sun/tongbu/study/phdproject/vla.
Execution copy: /home/sun/vla_exec/vla on gpu5070ti. All dependencies and native
installation must match frozen hashes before launch. Evidence returns under
versions/v48 and runs/v48_realtime_trial01. No hardware or training is authorized
or used here. Frequency/route acceptance requires measured evidence.
