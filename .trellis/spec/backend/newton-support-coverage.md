# Static support coverage in Newton

## 1. Scope / trigger

The v133 second pilot loses a foot through a subcell floor seam. A 10 cm
tomogram height does not prove that an entire cell supports a 44 mm foot.
v134 adds a negative-only supplement to this simulator's existing static map.
This is not a general sensor-only gap detector or real-robot qualification.

## 2. Signatures

`versions/v134/generate_coverage.py` runs on gpu5070ti. It binds the original
Building mesh and original physical-floor payload, samples each cell at sixteen
25 mm subcell centers, and writes `/data/sun/vla_mppi_20261009/support_coverage_v134`.

`grid_map.support_gap_path` and `grid_map.support_gap_fnv64` are paired inputs.
`SupportGapMask::blocks(x, y, ground_z)` is queried by the common native
`GridMap::reactiveOccupancy` before any measured-body obstacle waiver.

## 3. Contracts

- Process all original static floor layers, with no failed-route coordinates.
- The live planner reads a pinned immutable negative mask, never simulator feet,
  mesh queries or future state. Recorded transforms are diagnostic only.
- Use the existing 0.26 m height capability and configured cylinder radius.
  Partial cell extent and query-cell extent count in conservative dilation.
- A mask may only reject. Absence from the mask never grants free occupancy,
  support, source freshness, trajectory validity or owner release.
- Bind mask SHA-256 in the native execution receipt and FNV in native config.
  The mask is immutable and shared in map snapshot parameters.
- PCT navigation/surface payloads, physical scene, policy and measured-stop
  thresholds retain their original bytes/values. Old native and new native
  comparisons use the same host. New native v134 is compared to parent v133.

## 4. Validation / error matrix

| Input or event | Required behavior |
| --- | --- |
| Missing paired path/hash, corrupt file, malformed/nonfinite record | Reject initialization |
| Invalid query | Reject |
| Known partial floor inside footprint at the associated height | Reject |
| Same XY on a different floor | Do not veto based on the unrelated layer |
| Complete floor or permitted step | Keep original checks |
| Component regression passes | No physical success claim |

## 5. Good / base / bad cases

Good: 255 original captured scans and the due torso pose yield old permit/new
reject before the unsafe rejoin. Base: the native check is repaired but complete
navigation has not passed repeated trials. Bad: hide a gap by editing collision
geometry, or call a sampled static supplement an unseen-hazard detector.

## 6. Required tests

Run the actual geometry generator on solid floor, a 7 cm seam, a permitted
20 cm step and an excessive 40 cm drop. Run actual mask identity/query tests,
and `contract/run.py` against both installed versions using the same captured
inputs. `lidar_pose` records are optical-frame poses; use recorded torso data
when evaluating body-footprint collision. Preserve stamp and quaternion order.
Then perform fixed bounded physical pilots and the declared repeat comparison.

## 7. Wrong versus correct

Wrong: a sampled point or maximum height within a cell proves its whole surface.
Correct: record coverage uncertainty explicitly; keep the veto separate from
positive traversability and state the finite sampling and static-map boundary.

## Local/global footprint consistency (v138)

A global conservative envelope alone does not keep the optimized local curve
inside it. The seed/control-polygon tangent and the final controller-lookahead
heading can differ. The recorded v137 third pilot stops upright, accepts every
reference, and repeatedly rejects a smoothed curve whose front cylinder cuts
into the static support-gap mask. The measured stop position itself lies inside
the global all-heading envelope. Do not label this a transport or stale-map
failure.

Local queries additionally test the body center against the same support-gap
mask dilated by cylinder radius plus absolute offset (0.35+0.18 m here). Retain
the original cylinder veto and all other checks: the change must only add
rejections. Native recorded-input sweep: 6,800 queries, every prior rejection
preserved, 608 added rejections, 3,808 unchanged clear queries; identical
reconstructed map digest. This establishes collision behavior, not a physical
success rate. Fresh runs must show prevention; an already invalid stopped pose
is not guaranteed escapable.

The three v138 physical pilots all fail at the initial pose (no falls, no
meaningful travel). The global all-heading envelope is too conservative when
applied directly to every local query. v138 is rejected; do not adopt that
implementation merely because the upper-landing query regression passes.
Subsequent repairs must return to v137 and validate initial stair passage too.

## Sampled-curve rebound feedback (v139)

Keep the actual controller lookahead heading and original footprint checks. A
partial/tangent optimizer check is not enough; final retiming can also introduce
a collision. A bounded same-height free witness may generate directional hints
for mutable cubic controls; it cannot grant free space or publish commands.
Preserve the three fixed controls at each endpoint. No-free-witness, fixed-only
collision or invalid input adds no constraint. The same original dynamic,
minimum-cruise, boundary-PVA, fresh-map and publication gates must still pass.

A final post-refinement collision may feed back for at most two additional
complete attempts with the same initial state and execution epoch. Release the
old publication lease on retry and reacquire/check the current map at the final
gate. Do not renew source times or relax the mission startup/stop constraints.
Build01 demonstrates why checking only before refinement is insufficient.
Build02 accepts the captured v137 failure while v137 rejects, on identical
recorded maps; this is a native regression, not a reconstructed executor schedule
or an independent physical-success claim.

Final v139 validation for the declared Building scenario: three fixed pilots
arrive3/3; six fresh candidate trials arrive6/6versus parentv1375/6, no falls.
All11candidate replacement-owner stop proofs pass. Thirty new raw trials are
reverified remotely and569compact files/hash-bound qualification checks locally.
This validates the scenario repair; maximum fresh candidate round706.406ms
keeps sustained30Hz and broader navigation/Jetson/robot acceptance open. See
`audits/2026-10-10_v133_posture/SCENARIO_ACCEPTANCE.json` under the experiment.
