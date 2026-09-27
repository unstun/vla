# v5 height-repair component evidence

Stage: experiment + analysis. Date: 2026-09-27.

The frozen v4 start failure is repaired in the native optimizer and complete
planner replay. These checks do not establish closed-loop Building arrival.
Physical outcomes are recorded separately in `RESULTS.md`.

## Native build and frozen seed

`runtime/scan44_height_v5` builds successfully in the pinned ROS Humble image;
the build reports unchanged source bytes. Only the optimizer header/source
change relative to `scan43_prefix_diagnostic_v2`. The Building YAML selects the
new optional mode; the empty-floor YAML retains the false default.

`runs/v5_height_regression01` recompiles the existing native API caller against
the new header/library. Both cases use byte-identical original map, clouds,
body poses and captured seed derivatives:

| Check | Height fixed | Height optimization enabled |
|---|---|---|
| Native initial search | 15 nodes | Same 15 nodes |
| Original fitted seed | Same curve | Same curve |
| First optimization | Fails | Passes |
| Original endpoint position/velocity/acceleration | Retained | Retained |
| Complete native collision check | Rejects | Passes |

The fixed-mode results match every original v4 audit field exactly. At the
previous rejected sample, height changes from 0.459822 m to 0.414120 m when
optimization is enabled. Its footprint passes the unchanged native occupancy
test. No collision, ground-support, height-envelope or dynamics limit changes.

## Complete recorded-input planner

| Replay | Moving curves | Accepted plans |
|---|---:|---:|
| Original-format Building, v5 enabled | 1 | 1 |
| Original measured body twist, v4 baseline | 0 | 0 |
| Original measured body twist, v5 enabled | 1 | 1 |
| Recorded v3 empty floor, v4 baseline | 3 | 3 |
| Same empty floor, v5 default fixed mode | 3 | 3 |

Requests, exact input manifests and execution results are under
`runs/v5_replay_inputs01` and the corresponding `replays/v5_*` directories.
The empty-floor replay stops at recorded physical time 20.5 s; it is a partial
geometry regression, not a second 12 m arrival. Scheduling is intentionally
slower than the recorded clock. Curve counts are observations, not a claim of
deterministic wall-timer scheduling.

The prior v4 audit replay input omitted the legacy `linear` field. Although
`linear_body` was present, the unchanged replay's outer dispatch predicate
therefore left published twist at zero. The original-format control is retained
with that limitation. The paired measured-twist inputs preserve every original
body-frame velocity and add its calculated world-frame fields to satisfy the
existing dispatch contract. The existing assignment routine then directly uses
the original body-frame vectors. Both paired Building outcomes confirm the
same conclusion. The frozen-seed API check uses the actual captured derivatives
and is unaffected by this input-format issue. No production or replay source
was edited for this correction.

## Existing geometric sensor cases

`runs/v5_sensor_regression02` runs all eight original cases: empty, static human,
box, thin wall, post, low box, occluded human and blocked corridor. Occupancy,
search status and path-edge verdicts match the earlier native case results.
Unknown space and stale observations remain blocked in all cases. Successful
searches have checked edges; the two rejected searches return no path. This
tests map/search behavior, not closed-loop obstacle avoidance.

Attempt 01 failed before execution because its command used relative paths
under the supervisor's different working directory. Attempt 02 uses absolute
paths with unchanged code and conditions. The first result-review expression
also incorrectly required checked edges for a rejected empty path; retain that
failed review as `checks.json`, and use the explicitly corrected predicate in
`checks_review02.json`. Native case results were not changed or rerun to alter
their verdicts.
