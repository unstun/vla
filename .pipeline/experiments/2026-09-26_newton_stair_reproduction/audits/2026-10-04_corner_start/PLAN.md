# Corner-local upstream/current comparison

Stage: experiment + analysis. Dr Sun explicitly requested initialization beside
the corner instead of traversing the entire route. Preserve previous versions.

Use the late landing event at v70 native time78.488495s (1316.856ms solve).
Spawn from the original measured approach pose near76.009857s, about1.1m before
the event: XY(6.538910,-6.003162), yaw-1.425451. Original Building triangle-ray
preflight gives floor3.041690m with five footprint samples spanning19.2mm.
Retain the original final goal and goal/stop/dynamics contracts. Keep the full
Building mesh/map, sensor rig, native factory/PD/RL startup and policy. The
route prefix is omitted; initial policy/planner/map state is fresh. This is a
local-scene test, not restoration of the historical recurrent or warm state.

v74 parentv70 introduces only the explicit corner_start profile (scenario,
native multi-floor selection equivalent to historical_full, source binding and
scenario checks). Its native source stays exactv63. v75 selects the pinned v71
upstream probe in the same host/physical condition. The upstream planner's own
terrain/dynamics acceptance and event scheduling remain different. No v49
timeout, safety relaxation, altered emergency stop or artificial warm curve.

Ranked predictions:
1. If local recovery amplification is the tail source, currentv63 can produce
   multi-attempt cold-recovery spikes at this scene while original upstream's
   complete reference chain has at most three initialization modes.
2. If the corner geometry alone drives expensive inherited search/optimization,
   original upstream can exceed33.3ms here even without our outer recovery.
3. If missing preceding state matters, a fresh corner episode may fail or take
   a different path; then it is not a historical same-state latency reproduction.

Owned changes: new version host/profile/check/freeze helpers; this audit;
versioned display-only video helpers/results; task/spec/journal/version index.
Core native source, frozen parents and currentv48 reference stay unchanged.
Use the existing entry/source/build/clock/supervisor/retention gates. Build exact
native arms in the same cached amd64 Humble image; pin fresh installed bytes.
Check the actual scenario seam and source/profile negatives before freezing.
Run one bounded40s total physical episode per arm, about29s navigation after
the normal factory stand. Preserve early failures. Measure complete-round
latency, attempts, successful wallHz, physical progress and terminal cause.
Render actual recorded states directly to MP4, verify decode/causality/hashes,
and visually inspect the corner. Further retries retain frozen bytes or use
the next integer for a logical change.

Mac execution exception: unique /private/tmp build/capture/cache roots outside
repo. Bulk destination gpu5070ti:/home/sun/vla_artifacts/2026-10-04_corner_start/.
Use storage-only SSH/rsync; no GPU job. Return source/config, compact reports,
metrics/plots/hash receipts, three video samples and finished review MP4s,
expected less20MB of new result/media bytes. Verify remote hashes before local
cleanup. Independent trajectories and fresh state limit causal claims.
