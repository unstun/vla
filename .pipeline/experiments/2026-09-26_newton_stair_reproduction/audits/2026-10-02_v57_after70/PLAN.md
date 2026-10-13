# Diagnose the post-70-second v57 slowdown

Analysis only, under the active corner-continuity task. No new physics, runtime
version, stop policy, timeout, final goal or safety change. Frozen v57 and its
v56 native source/install stay unchanged.

Recompute both original traces, distinguish goal-search time, input application,
warm fitting, optimization, scheduler gaps and measured motion. Test these ranked
hypotheses: repeated final-goal search after lattice entry; cloud processing or
queued input amplification; warm/fallback growth; host contention.

Run one bounded offline native probe against recorded input streams. Reuse the
actual AStar/GridMap library and callbacks; observe reached nodes and geometry
without changing their search or collision implementation. Fixed-clock observer
replay does not reconstruct live DDS batches, so replay timings are component
evidence and must not replace measured live timings.

Local source of truth: this repository. Sync only this audit's sources, verify
native source hashes before/after, use an idle host and no-network diagnostic
container. External bound: 300 s, 3 CPUs, 6 GiB; this is not a planner deadline.
Keep event streams, clouds, derived round arrays and build files on gpu5070ti
under this audit. Return report, plot tables, native result and source/storage
provenance, targeting less than 2 MiB. No full capture return or deletion.
