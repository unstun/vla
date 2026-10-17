# Newton geometric sensor port evidence

## 1. Scope

Applies to the bounded local experiment
`.pipeline/experiments/2026-09-26_newton_stair_reproduction/`. It does not declare
RTX equivalence, a hardware sensor calibration or accepted stair navigation.

## 2. Signatures

`scripts/geometric_lidar.py` exposes
`GeometricLidar(robot, human, emitter_self_exclusion=False)` and
`sensor_view(model, state, excluded_shapes)`. The qualified probe explicitly
selects `emitter_self_exclusion=True`; no-exclusion remains the diagnostic
default. Use the experiment's `scripts/run_bounded.py` with a new run ID and
`scripts/probe_lidar.py`; the README contains the exact interpreter and command.

## 3. Contracts

- Resolve sensor-owner geometry from the original `mid360_body_link` URDF
  visuals and exact scaled mesh contents. Do not use the collapsed rigid-body
  ID, which also owns other robot parts.
- Construct a separate shape-flags/BVH view. Physical and rendered shapes stay
  unchanged; all other robot and external shapes continue to occlude.
- Reject invalid ranges only after selecting the nearest actual ray hit. A
  distinct obstacle inside0.1m still blocks the background.
- Update current official skin vertices and refit before querying. Actor truth
  is a separate audit output, never tracker input.
- Preserve all original ray windows, pose conventions, assets and hashes.

## 4. Error and acceptance matrix

| Condition | Required outcome |
| --- | --- |
| Original sensor link/visual contract or unique mesh match changes | Raise; do not guess shape IDs |
| Duplicate/out-of-range exclusion IDs | Raise |
| Other robot shape disappears from the ray scene | Reject the sensor gate |
| Near external blocker exposes the background | Reject |
| Repeated identical skin gives different ranges | Reject |
| Single positive cloud without occlusion/skin controls | Diagnostic only |

## 5. Cases

The native-MuJoCo comparison checks background1.9m, a distinct robot part0.35m
and an external blocker0.06m. The last hit is below the valid return range but
remains the occluder. Original-scene sweeps retain thousands of other robot
near hits. A fixed-root skin change alters180 rays in the recorded condition;
an identical-frame repeat is exact.

## 6. Verification

Require `result.json` to record the native comparison, unchanged flags, exact
excluded shapes, other-robot near occlusion and both skin controls. Check raw
process completion separately. Evidence:
`runs/lidar_upstream_contract_v2/` and `validation/component_review.json`.
The flat controller's six regressions also pass after adding the scene seam.

## 7. Source use and common mistake

The selected convention is grounded in Robotec RGL `Scene.cc` at `d4bf3cf3`
and MuJoCo rangefinder/body-exclusion code at `a79d65c4`; Newton's public BVH
API and Warp's point-update/refit pattern implement the local adapter. Exact
pins/licenses/excerpts are in the dated upstream survey. Livox's minimum-range
ray-start convention is a different behavior and was not substituted.

Do not treat a failed, opaque-housing probe as justification to move the
sensor or remove all robot geometry. First inspect upstream implementations
and record which behavior applies. Likewise, a macOS/Linux monotonic-origin
diagnostic is not a clock adapter: keep the original freshness gates until
a source-backed cross-OS solution is qualified.

## 2026-09-26 visibility limitation discovered during color review

The original official USD has five visible and four invisible mesh parts.
The qualified geometric sensor used all nine. Its old occlusion/skinning tests
remain evidence for that recorded condition, but do not establish visibility
parity with the source USD or Isaac. Rendering now respects visibility; sensor
selection must be separately corrected and requalified before stronger claims.
Never silently rewrite the old cloud files after a display-only correction.

## Captured tracking interruption diagnostics

Before attributing a stopped trajectory to an obstacle, resolve the native
verdict enum and pair it with the measured-cloud tracker snapshot. In this
baseline, verdict 3 is `MissingInput`; generic occupied-target text is not
specific enough. A later watchdog message may be downstream of candidate
rejection rather than the initial cause.

Replay saved clouds and received poses through the original tracker before
altering gates. Trace the actual candidate function, including point count and
horizontal/vertical spans. Require a frozen ray replay to reproduce saved
points before interpreting pattern, pose or visibility controls. An artificial
orientation that restores detection is sensitivity evidence, not an approved
sensor calibration. Preserve current-only observations and unresolved-input
behavior until a separately tested change exists.

Evidence: the experiment's `DIAGNOSIS.md` and
`runs/trajectory_diagnosis_review_v3/`. Published optimized spline controls
must not be relabeled as missing initializer seed arrays when investigating
timing; exact input identity applies to both sensor and planner replay.
