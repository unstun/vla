# Saved G07 input export

This is input extraction and integrity verification only. It runs no planner,
simulator or physics integration. The original capture is v248_G07_attempt01;
the native replay parent is the frozen v247 installation.

The extractor adapts the formats in
`audits/2026-10-17_v237_terminal_approach/prepare_replay.py`. Its local source is
`prepare_g07.py`; `returned/metadata.json` binds the executed adapter SHA-256.

## Storage and verification

Remote input directory:

`/data/sun/vla_mppi_20261009/generic_mechanisms_v249/g07_input`

The raw capture archive SHA-256 is
`7a211b1f9f70c94d38cd9b52bac6c27c78caf27c8a4fbf20a83dfc423bd5b658`.
All 910 original published NPZ members were checked against their capture hashes.
The export contains 11,920,077 points, or 143,040,924 bytes of little-endian XYZ
float32 data. The second read-back verified every exported cloud hash, point
count, pose/twist field count, route text/JSON equality and original freshness.
Raw NPZ files and exported point arrays remain remote. Only compact provenance
and frame metadata are returned here.

| Frame | Query/body source ns | Last published source ns | Published/observer prefix | Historical mapper count | Historical FSM admission generation |
|---|---:|---:|---:|---:|---:|
| 0 | 100096618652 | 99976684570 | 890 | 884 | 13 |
| 1 | 101106063843 | 100976135254 | 900 | 894 | 14 |
| 2 | 102110511780 | 101975585938 | 910 | 904 | 14 |

The six-scan difference is real: saved cloud and lidar-pose observers each contain
the complete published count. The exact original mapper consumption/drop/batch
sequence was not recorded. No scans were removed to force agreement with its
counter. A new replay is an ordered published-prefix reconstruction until its
failure signature agrees with the saved failure; the old revision number is a
label, not a serialized map snapshot. The controller's starvation generation13
must not be substituted for the later FSM admission generation14.

## C++ input formats

- `scans.txt`: index, original source nanoseconds, body filename, sensor filename,
  cloud filename. Rows retain original publication audit order. The index starts
  at zero; `scan_inventory.json` also preserves the original scan_id.
- `cloud_NNNNN.f32`: little-endian float32 XYZ triples in sensor frame, no header.
  Use the original sensor pose and original source stamp. No resampling, filtering
  or coordinate translation was applied.
- `body_NNNNN.txt`: x y z qx qy qz qw vx_world vy_world vz_world wx_world wy_world
  wz_world from that scan's captured body state. `sensor_NNNNN.txt` has only the
  first seven pose fields for the sensor frame.
- `frames.txt`: frame index, query_ns, body_source_ns, cloud_cutoff_ns.
- `query_NNNN.txt`: the same 13 fields as body files, taken from the exact saved
  body observer, not the nearest 20 ms physics telemetry sample.
- `route_NNNN.txt`: 401 lines of x y z, matching `route_NNNN.json` exactly.
  The JSON retains all original pose orientations, header stamp and observer times.
- `curve_NNNN.txt`: first line original start seconds, control-point count, knot
  count; then XYZ control-point lines and one line of knots. `frame_NNNN.json`
  retains the complete original Bspline message, trajectory ID, reverse flag and
  both original clock/source times.
- `input_events.jsonl`: original observer sequence, clock, monotonic receipt time,
  source stamp and complete body/lidar-pose/cloud metadata through the last query.
  It includes intermediate body observations between scans. `body_events.txt`
  flattens these as index, observer_clock_ns, wall_monotonic_ns, body_source_ns,
  followed by the 13 pose/twist values.
- `navigation.f32`, `surface.f32`, `physical_floor.f32`: exact hash-verified v247
  static fixtures. These retain the existing ground-cloud format of four float32
  fields per point; they are not XYZ-only live lidar files.

The old `v81/recorded_readers.h::read_pose` reads only seven fields. Extend the
evaluation reader to consume the six twist values rather than silently leaving
velocity zero. The old `v84/recording.h::read_scans` asserts exactly188 scans;
reuse `apply_scan` but parse this listing without that historical count assertion.

Frame0 and frame2 have expired active curves, so the original FSM chooses measured
odom position/velocity and zero acceleration. Frame1 has a valid reverse curve;
its original start branch also depends on the recorded/reconstructed failure
counter. Do not unconditionally use curve PVA for all frames.

## Time and global-review limits

Keep the original query nanoseconds and original source stamps. Query body age is
zero in all three exact frames; cloud ages are 0.119934082, 0.129928589 and
0.134925842 seconds. A frozen original query clock preserves those original ages
but does not reproduce wall-clock scheduling. Rebasing all sources to a fresh
epoch would be a separate diagnostic and cannot replace original-time admission.

`global_recoverability.json` retains every saved `pct_shared_rejected` line.
The final count was2, but the original rejected candidate path and service request
coordinates were not saved. A regenerated two-pose rejection needs its own
provenance. Published admitted route messages cannot be relabelled as that rejected
candidate. Record future service inputs/results and rejection provenance at the
existing PCT and QueryLease seams.

## Late global-start candidates

`late_global_starts.txt` contains all146 saved body observations with source time
in104.0–105.7s, without resampling. The first/last source stamps are104009468079
and105698539734ns. The remote counterpart is
`/data/sun/vla_mppi_20261009/generic_mechanisms_v249/g07_late_global/starts.txt`.
Each row has no header and uses this order:

`index body_source_ns observer_clock_ns observer_wall_monotonic_ns x y z qx qy qz qw`

The text SHA-256 is
`c4d9b37a55cb43fa3c7a93ed8c9c868b9d0932a70a416d6c42034467bd5bf11f`.
`late_global_pre104_controls.txt` separately preserves18 saved observations from
103.8–104.0s. These are candidate start states, not recorded planner requests.
`late_global_goal_canonical.txt` contains the seven pose fields of the canonical
goal, verified identical across all10 admitted route messages.

The original final graph attempt2 begins after the timestamped attempt1 rejection
at1792318669.374664892 and before the shared rejection at1792318669.844112799.
The tighter exact start timestamp is absent. The preceding recovery wait completes
at1792318668.146897116 and attempt0 rejects at1792318668.774810218; these are
scheduling context rather than a directly recorded createPlan entry interval.
Underlying PCT printf output has no timestamps and may be buffered.

Crucially, all three attempts reuse the same const `createPlan(start,goal)`
arguments; the final shared service can acquire a newer `request.body`. A body
observed at the final graph start/review must not be asserted to be the original
global request.start. `late_global_log_timing.json` preserves this distinction and
the exact original log lines. No cloud extraction, planner call or physics step
was performed by the late-state extractor.

## Re-extraction command

Run only to a new output directory; the extractor refuses an existing directory.

```sh
env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /home/sun/vla_exec/envs/newton_worker/bin/python \
  /data/sun/vla_mppi_20261009/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/audits/2026-10-18_v249_generic_mechanism_repairs/research/G07/prepare_g07.py \
  --output /data/sun/vla_mppi_20261009/generic_mechanisms_v249/g07_input_new
```
