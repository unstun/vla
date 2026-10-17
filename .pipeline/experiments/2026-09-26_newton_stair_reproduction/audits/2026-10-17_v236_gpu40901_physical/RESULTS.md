# gpu40901 v236: scanner repair passes; physical route fails on writer backlog

**One physical attempt only.** This is a failed route with a verified recorded
prefix, not a new accepted baseline. The v232/v233 single-route baseline on
5070Ti remains selected. The full-route verification fails; original result
was not synthesized. The original driver wrote a FAILED finish_request.

| Evidence | Outcome |
|---|---|
| Version / run |v236 / v236_linux_full_attempt01 |
| Navigation / native install | Frozen v232 source; v234 rebuilt install |
| Scanner period and absolute deadline | Both0.1s, unchanged |
| Completed scans |245,0 deadline failures |
| Scan total latency | Mean30.204114ms; max46.718744ms |
| Largest scan runnable wait |15.992870ms |
| Goal and locomotion | Goal sent; actual movement recorded |
| Last saved physical state |35.59206771850586s;1367 states |
| Failure | Evidence writer backlog exceeds its declared bound (>256) |
| Terminal proof | Result absent; original FAILED finish request present; gate fails |
|45–55s stairs, arrival, finalPD | Not reached / untested |

[Source diagnosis, repair and preflight](../../versions/v236/RESULTS.md).
The accepted preflight02 checks the actual12-second native graph, source/install
and full effective profile with zero physics. The original policy and ray
bytes pass their parity gates. RL, original endpoints,0.35m collision/support
thresholds and0.1s captures are unchanged.

## What changed and what this run establishes

The old scanner check confuses native-clock catch-up with elapsed wall time.
The fix gives a submitted scan only the remainder of its original100ms wall
budget. Separate real-ray tests also expose runnable contention on fixed hot
CPUs. Own host execution now has an enforced4-CPU quota with flexible affinity,
nice19/shares128; native ROS retains its separate4-CPU cap with flexible
affinity. Shared IsaacLab jobs, package environments, priority/affinity and
GPU settings were not changed. Host receipts record observed peer identities;
this is not a measured guarantee of unchanged peer training throughput.

This run crosses the old12.802s LiDAR failure and records navigation until
35.592s, with all245 scans inside the unchanged deadline. It establishes a
successful scanner prefix, not full-route scanner reliability. The remaining
failure is the original single writer serving current execution state plus
bulk evidence. The shared queue is source-confirmed; its dominant per-write
latency was not measured. The256 limit remains enforced. No second physics
trial or writer workaround was performed.

Diagnostic prefix planning:619/629 successful rounds,20.1777 successful wall
Hz, median9.1346ms/P9568.6050ms/max576.2950ms solve time. Incomplete route metrics
must not be ranked as a full-route speedup or staircase success measurement.

## Videos

- [Four-panel full physical-time comparison](delivered/full_physics_comparison.mp4):
  top left v219/5070Ti; top right v232 executionv233/5070Ti;
  bottom left failedv235/40901; bottom right repaired-scannerv236/40901.
- [This attempt, actual recorded states](delivered/v236_partial_attempt01.mp4).
- [45–55s comparison](delivered/stairs_physics_45_55.mp4): v235/v236 are explicitly
  ended, so the new run supplies no staircase observations.

The four-way comparison uses the already hash-verified historical video,
without needing powered-off5070Ti. Selection follows one common physical-time
grid at30FPS, selecting only already-recorded states; no interpolation or new
physics. New v236 has1108 displayed frames and ends at35.592s. Ended panels
turn black and retain their end labels. Native trajectory overlays come from
actual recorded plans. Full decode/frame-count/hash checks and frame mapping
are in results. Direct image review accompanies local delivery verification.

## Retention and reproducibility

Raw root (gpu40901):
`/home/ubuntu/sun/vla_v234_20261017/trials/v236_linux_full_attempt01`.
Verified non-pruning snapshot `capture_snapshot.zip`:67,694,719bytes,
SHA350aa0ab0889744418ae40d9dafe3c459caafd876240edf1e9ff144efd6e5869.
Every archive member was checked against its original; all originals remain.
Original helper retention failed because lsof was unavailable in the isolated
wrapper, so no deletion was attempted. Preparation failures, analysis failure
receipts and physical exceptions are retained. Heavy raw/build/cache data
are not returned or committed.

Executed audit source hashes are in source_identity.json. `preserve.py`,
`analyze.py`, `render_partial.py`, `compare.py` and `deliver.py` reproduce this
failed-prefix package; use the private interpreter and original ffmpeg PATH.
The unused full-run renderer/body-margin templates were prepared before the
attempt but were not executed; no new staircase/body-margin claim comes from
them. results/return_manifest.json binds returned payload sizes/hashes;
LOCAL_DELIVERY.json records local verification and visual review.

Next step: instrument writer service/backlog and separate critical state
publication from bulk evidence while preserving failure/finish closure, then
verify offline before seeking another physical attempt.

## Final packaging correction

The first partial-analysis branch incorrectly hardcoded finish-request absence.
The package assertion exposed this; analysis02 reads the original file and
records FAILED with note `Geometric sensing became unhealthy`. result.json
remains absent. Original analysis01 reports/sources are retained under results;
this is a reporting correction, not a change to physical evidence or runtime.
The verified capture snapshot is unchanged. Final local checks verify all61
returned payloads (16,751,665bytes), plus local source/visual additions; no
compiled cache or raw arrays are included.
