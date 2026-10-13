# v78 recorded-map processing diagnosis

Stage: experiment + analysis. Parent v76, native v63, observation-only isolated
map replay. The v77 upstream arm remains frozen. No simulator/control/stop,
trajectory, goal, occupancy/support or inflation parameter change.

Replay v76 measured cloud/pose history through the original map callbacks,
without DDS, the optimizer, rendering or physics. Compare an unmodified native
map build with one containing bulk stage timers and operation counters. Require
the final occupancy, inflation, ray flags/counts and retained terrain/nonterrain
state to match. Instrumentation adds no admission, timeout or return condition.
Original historical input totals and native replay timings are distinct evidence.
Observer/scan history does not recreate the historical native DDS take batching.

Owned source: this diagnostic package and the 2026-10-05 map-processing audit.
Generate the instrumented translation unit from the exact pinned v63 file and
save its diff/hash; never modify native v63. Reuse its captured-input readers.
Build only map dependencies in the cached amd64 Humble image, with a bounded
Mac CPU replay. Freeze source before executing recorded-input profiles. Keep
build/cache/selected input bytes outside the repository in a unique private/tmp
root. Raw originals remain SHA-verified on gpu5070ti; remote access is storage
only. Return compact stage results, state parity and provenance before cleanup.
