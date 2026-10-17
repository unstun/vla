# Measured-geometry repair evidence

Stage: experiment + analysis. Navigation acceptance is still open. Dr Sun
requested class-independent avoidance using sensor measurements and established
GitHub implementations. See `UPSTREAM_REUSE.md` for exact revisions/licenses
and the distinction between executed components and surveyed references.

## Directly verified changes

| Change | Direct evidence | Limit |
| --- | --- | --- |
| Remove mandatory person-track input | `native_contract_v1/result.json`: old header fails on fresh geometry without a person batch; candidate passes. `native_contract_v2/result.json`: geometry, occupied/unknown/stale negatives, footprint negatives and four driver tests pass. | Sensor/body poses and terrain support remain required. No classification or movement confirmation is needed. |
| Keep terrain classification with native occupancy lifetime | `runs/generic_native_height_v2/`: empty scene is free; static human, box, post, low box and partially occluded human are occupied; available native AStar paths pass edge checks. | Frozen actual ray inputs, not continuous navigation. |
| Generic detours | `runs/generic_temporal_native_v1/` and `v2/`: human, box, post, low box and thin-wall cases block the straight reference and admit checked AStar detours. | Uses the earlier 0.25 m two-circle radius. Larger whole-robot envelope is evaluated separately. |
| Restore SCAN sampling and optimize-before-retime | `replays/flat_empty_native39_v1/` and `flat_human_native39_v1/`: accepted 5.90985-second complete native curves with endpoint, dynamics and collision checks. | These two curves are identical. This pair proves curve production, not causal obstacle avoidance. |
| Bounded post-optimization time adjustment | `replays/flat_human_behind_native39_v1/`: zero published curves; short prefixes fail acceleration checks. Same input in `flat_human_behind_native40_v1/`: two accepted short curves, four checked seeds. | Short safe progress is not passage around the human or goal completion. No dynamics limit was relaxed. |
| Native physical contact capacity | `validation/flat_contact_capacity_review.json`: nine checks pass. Automatic Newton sizing gives 1218 contacts/4872 constraint rows. Same continuous 30.7-second command replay matches the first seven seconds exactly and keeps base height above 0.2558 m. | Isolates physics capacity; not closed-loop navigation. |
| Fail on contact-buffer overflow | `runs/flat_legacy_capacity_guard_v1/`: expected failure before solver step at 101 contacts versus capacity 100. | This negative run must not be counted as a failed navigation regression or as a successful episode. |
| Original policy/interface regression | `runs/flat_interface_contract_v3/result.json`: six tests, no errors or failures. | Preserves the established observation/history/motor contract. |
| Stable voxel-boundary indexing | `runs/flat_curve_map_native_v1/` versus `v2/`: the same native refined-curve samples change from six rejected points to zero; two genuine collisions in the earlier optimized curve remain rejected. | Reuses Voxblox's coordinate epsilon, not a physical obstacle-clearance relaxation. Full re-planning and physical avoidance remain separate gates. |

All paths above are relative to the Newton stair experiment root except the
two `native_contract_*` directories, which are relative to this repair.

## Continuous physical failure and corrected diagnosis

`runs/flat_static_human_live_v3/` ran 30.69476 seconds and 30,700 physical steps
with a stationary official human, exact visible-mesh contacts, original sensor
rig, native PCT/SCAN/controller and no tracker process. The body advances about
1.34 m but does not reach the original goal. The driver eventually fails its
measured-stop condition. This is a **failed run**.

The first nonzero native contact-candidate count at 7.99960 seconds is not a
physical touch. Newton's default detection gap produces speculative candidates;
its native surface-separation function reports about 0.198 m separation there.
Contact count first exceeds the old 100-slot solver capacity at a recorded
10.12046 seconds. The log explicitly reports capacity overflow. Later, the body
sinks and first negative human surface separation appears at 13.94200 seconds.
Do not attribute the entire sequence to a planner-human collision at 8 seconds.

`runs/flat_contact_audit_v2/` recomputes collision geometry from recorded poses
without stepping. `runs/flat_auto_capacity_replay_v1/` replays the exact command
sequence with Newton's documented automatic capacities and stays standing.
The current runtime also rejects overflow before stepping. These observations
support the capacity diagnosis, without claiming that the trajectory was safe
or that avoidance is finished.

Actual failure video, regular file (not a symlink):
`output/2026-09-26_newton_macos/lite3_flat_static_human_failure.mp4` at project root.
Source: `runs/flat_contact_video_v2/`, rendered from the immutable physical states.

## Remaining planning gate

For a goal directly behind the human, the previous local-target code searches
backward only along the original reference. It therefore selects a stopping
point in front of the obstacle. The measured-map diagnostic in
`runs/flat_query_grid_native_v1/map_query.png` shows free lateral space; a native
path to the offset probe goal exists. Unknown space behind the human remains
blocked and must not be turned into free space from simulator object data.

SCAN41's empty-cell neighborhood is a rejected candidate: empty does not imply
reachable. SCAN42 uses native reached nodes within an explicit local tolerance,
following the inspected Nav2 Smac termination pattern. The original final goal
and its actual-arrival criterion remain unchanged, and an intermediate endpoint
cannot complete the global reference. Full B-spline acceptance is still required.

The explicit flat profile restores SCAN's original search-plane interpolation
and eight planar neighbors; the default stair profile retains the local 3D
graph. The preexisting local 3D expansion was repeatedly exhausting the original
0.2-second search budget. The search-plane function is copied byte-for-byte from
the pinned SCAN source. No search deadline was increased.

Current candidate experiments, including unsuccessful proposals and builds,
remain under `runtime/scan34*` through `runtime/scan42*`, with returned evidence
under `build_evidence_*` and immutable replay directories. Do not treat the newest
candidate number, process exit zero, or internal `final_plan_success` as a route
success; check actual published curves and continuous physical behavior.

### Captured curve-stage diagnosis

`replays/flat_curve_capture_native42_v7/result/captured_curves.json` contains
the actual controls and knots before and after native time refinement. The
first optimized curve lasts 2.88 seconds; the refined curve lasts 4.77500
seconds. Height varies only at double-precision roundoff around 0.3 m.
`sample_native_curve.cpp` reuses the original complete-curve checker and its
0.8-second heading lookahead to produce exactly 290/479 query samples. These
queries are fed into the same measured-cloud native map.

The optimized curve has two real rejected samples, even with exact 0.3 m query
height. The refined curve has six raw rejected samples and zero with exact
height; the first raw rejection is at
`[0.58355076656, -0.30007325387, 0.29999999999999993]`. This confirms a numerical
voxel-layer error in the refined output. Yaw-only controls do not resolve it.
`validation/flat_curve_stage_diagnosis.json` records the distinction.

SCAN42 v8 applies the pinned Voxblox epsilon-before-floor convention. All 479
raw refined samples pass, while the two actual optimized-curve collisions stay
blocked. This is a direct numerical regression fix. A fresh full planning run
can choose a different temporary endpoint and still fail later optimization;
the numerical repair alone is not a complete avoidance result.

## Other unresolved limitations

- Native ray-clearing tests retain occupied voxels after a removed box or low
  box. Neither the original geometry candidate nor the experimental
  ground-marking variant passed that clearing expectation.
- The 0.35 m two-circle radius and recorded vertical envelope are bounds on the
  measured robot poses, not a proof for every articulation or stair contact.
- A flat support prior is a synthetic control scene, not the original Building
  or an Isaac reproduction. Newton geometric rays are not calibrated MID360 or
  RTX equivalence.
- The original Isaac A4 stair gate remains open. The remote server stays off;
  no formal training or physical-robot actuation was performed.

## Selected candidate and continuous acceptance

The selected candidate is `runtime/scan42_geometry_v9`, with
`geometry_smac_approach_flat.yaml`, automatic Newton contact capacity and an
explicit 240-second total goal wall budget. Sensor/command age gates are
unchanged. `FLAT_ACCEPTANCE.md` was written before the full-rate repeat and box
run; acceptance was not changed after observing their failures.

| Episode | Actual result | Contact/posture evidence | Acceptance |
| --- | --- | --- | --- |
| `flat_static_human_live_v4` | Arrived after quiescence; final XY error 0.1520 m; five moving native curves; actual lateral detour. | 28,080 continuous physics steps; minimum up-z 0.9219; 50 Hz contact candidates all zero. | Arrival pilot only: full 1 ms contact scoring was not yet installed. All 15 interface checks pass. |
| `flat_static_human_live_v5` | Did not arrive; two short moving curves, final goal error 2.0868 m. | All 28,100 physics steps scored, zero contact candidates/touches; upright and measured stop pass. | Repeat fails the declared arrival/distance checks; all 15 interface checks pass. |
| `flat_box_live_v1` | Did not start moving; zero moving curves/commands; terminal `initial_heartbeat_missing`. Native goal-neighborhood proposals were followed by optimization/seed-search failures. | All 28,080 physics steps scored, zero obstacle touches; upright and measured stop pass. | Fails motion and arrival checks. Driver completion is not navigation success. |

The v5 and box trials use the same build, planner configuration, sensor rig and
policy; only the simulated obstacle geometry differs. Geometry metadata and
contact scores are never navigation inputs. Human v4 had 9 rejected clock
samples and 4 command reconnects; v5 had 14 and 6, respectively. All recorded
disconnect/clock-unsynchronized commands are zero. Do not omit this timing
variation when interpreting the one success.

`flat_box_qualification_v2` first qualified the native box sensor/contact path:
3,000 continuous steps, 668 actual box ray hits, no human geometry and no touch.
A separate frozen-overlap negative control produces negative native surface
separation. Its earlier v1 serialization failure remains available.

Videos are actual recorded physical states, rendered afterwards with Newton.
The fixed side camera is display only and never supplies navigation data:

- Project output: `output/2026-09-26_newton_macos/lite3_flat_human_arrival_sideview.mp4`.
- Source render: `runs/flat_human_arrival_video_v3/`; SHA-256 and ffprobe result:
  `validation/flat_human_sideview_video_delivery.json`.
- Failed-repeat render: `runs/flat_human_repeat_video_v1/`.
- Delivered failed repeat: `output/2026-09-26_newton_macos/lite3_flat_human_repeat_failed.mp4`;
  SHA-256/ffprobe: `validation/flat_human_repeat_video_delivery.json`.

## Repeat-failure diagnostic

`prepare_recorded_map_probe.py` exports original sensor points and their
paired recorded body/sensor poses into the existing native map probe. It uses
the same flat PCT support data. A common one-second timestamp translation
keeps all stamps positive; no obstacle labels or simulator coordinates are
added. The map consumes the original measured sequence before diagnostic
queries. These replay observations are not a bit-for-bit snapshot of the live
callback schedule.

`runs/flat_repeat_native_map_v1/` links an isolated diagnostic executable to the
unchanged qualified native libraries. With fresh inputs, the human-v5 snapshot
near 11.901 physics seconds reports its actual body position
`[0.899996, 0.123803, 0.298095]` occupied at its actual yaw. The forced diagnostic
reports `StaticObstacle`, not stale input. At the same map snapshot, shifting
only the diagnostic query 0.15 m backwards is free; lateral-heading queries
are also free. These shifts are scoring controls, never robot commands.

The previous short curve ends at x=0.768750, so physical execution has crossed
that endpoint before entering the inflated region. There is no actual contact.
This confirms a planning/tracking-clearance problem at this snapshot; it does
not establish one sufficient cause for every earlier rejection. A fresh map
and fresh AStar instance also fail the selected v5 searches, so residual state
from repeated live searches is not required for failure. Search timeouts from
this diagnostic are not a performance benchmark: rendering overlapped part
of the replay. Geometry query results are independent of that wall budget.

The pinned SCAN controller comparison is in `UPSTREAM_REUSE.md`. No speculative
controller or relaxed clearance/age threshold was applied after these results.
The next causal check is the captured short-curve execution and stop response,
including replanned hold targets and measured tracking error. The box's initial
optimization failure is a separate unresolved reproduction case.

## Final component regression

`runs/generic_native_current_v1/` uses the selected v9 libraries and current
0.35 m footprint on all eight measured fixtures. Every occupied-object probe
is blocked; empty control points are free; unknown corners and expired inputs
remain blocked. Six fixtures have checked native paths. Thin wall and blocked
corridor return no path; their requested goal queries are occupied. This does
not prove physical avoidance of each class or obstacle-removal clearing.

`native_contract_v3/result.json` passes the current geometry-only native
contract and four driver tests. `runs/flat_interface_contract_v4/result.json`
passes all six policy/observation/motor-interface tests after full-rate scoring
was added. `runs/geometry_probe_bridge_v1/` additionally verifies the corrected
geometry-only `--probe` readiness: 3 seconds of actual physics, zero navigation
commands, no tracker streams, synchronized cloud/pose and terrain input, and
four rejected invalid applied-state controls (stale, future, foreign, duplicate).
The legacy tracking mode retains its original track readiness condition.
Full flat navigation and original Isaac A4 remain **open**.
