# v50 cold-tail continuation evidence

Stage: experiment + analysis. Executed on gpu5070ti on 2026-10-02.
Native v50 behavior is unchanged. No physics was run by this audit.

## Reproduced failure and limitation

The native replay was rebuilt against the original v50 installation and repeated
six times for each of three recorded states. All 18 repetitions agree on result
and accepted control points/knots. The first initializer input in every case is
byte-equivalent under canonical JSON to the original live seed (SHA-256 checked).
The two corner cases fail as they did live; the earlier case succeeds.

| Simulation time (s) | Original live latency (ms) | Fixed-input replay range (ms) | Replay outcomes |
|---|---:|---:|---|
| 33.453 | 178.036 | 96.288–98.402 | 6 successes |
| 44.952 | 1829.626 | 476.071–481.525 | 6 failures |
| 74.041 | 664.971 | 233.877–235.636 | 6 failures |

These are different executions, **not a measured optimization speedup**. Replay
uses observer receive order and a frozen per-case ROS clock; it does not reproduce
live DDS drain batches or the full native hidden state. No new sensor input is
applied during a replay solve. At the worst case, the original final accepted
curve is already expired (start 42.708 s, duration 1.998 s); its endpoint supplies
the repeated start PVA. Replay retains 12 seed/optimizer calls and produces the
same classes of missing-rebound-constraint and blocked-first-control rejection.
It does not reproduce all 1829.626 ms of the live round.

## Duplicate work audit

Original trial01 contains 1297 captured seeds and 20 same-seed/same-height-mode
repeats within a round; 18 have intervening logged input messages. Trial02 has
1847 seeds and 20 such repeats; seven have intervening messages. The remaining
15 across both runs are not proof of equivalent problems: the clock can advance,
and seed equality does not capture all map, optimizer or ownership state.
Broadly dropping outer retries or reusing prior safety decisions is unjustified.

## CPU profile

A separate `-pg` diagnostic executable compiles the unchanged native map, search,
optimizer and spline source. Sampling is enabled only during the three planning
cases (six repeats each); all 18 deterministic output comparisons pass again.
The flat profile reports 3.83 sampled seconds; instrumented elapsed times are
not production performance measurements.

| Self CPU sample category | Share |
|---|---:|
| Terrain cell ordered-map lookup | 24.28% |
| Raw occupancy contributor classification/cache | 21.41% |
| Footprint-to-layer association helper | 9.40% |
| Grid address conversion | 8.09% |
| Reactive occupancy query | 7.83% |

Call counters include replay warm-up even while sampling is disabled; do not
interpret their totals as calls within one cold round. Shared-library time and
instrumentation overhead limit this profile. The measured hotspot supports a
bounded lookup-data optimization, not cached collision/support verdicts.
The subsequent v52 candidate targets raw/scored terrain-cell lookup only; this
audit alone claims neither a fix nor 30 Hz.

## Identity and storage

100 native source files match frozen v50. Remote installation verification
checked 518 files with no mismatch; its manifest matches the frozen local one.
Compact returned results and locator files pass SHA-256 checks. Original source,
stop handling, final goal/yaw and safety contracts were not modified by the audit.

The 112,513,488-byte converted input stream, full logs, executables and builds
remain on gpu5070ti. The first replay returned 140,823 bytes and the CPU profile
returned 297,893 bytes. `attempt01/remote_artifacts.json` and
`cpu_profile/attempt01/remote_artifacts.json` give exact remote paths, sizes and
hashes. No full run directories were returned.

## Reproduce or retrieve

From the local repository, run `python3 AUDIT/analyze_retries.py` and
`python3 AUDIT/verify_return.py`, with AUDIT set to this audit directory.
The exact Docker commands, image and read-only mounts are in each returned
`request.json`. A rerun needs a fresh attempt directory and owned container name;
never overwrite either preserved attempt. The CPU replay reuses the first
attempt's remote input stream without duplicating it.

To retrieve one needed raw artifact, select its relative name from the locator,
copy that exact file from `gpu5070ti:<absolute_root>/<name>`, and verify its listed
SHA-256 before use. Do not recursively copy the attempt directory.
