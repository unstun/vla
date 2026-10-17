# Building/PCT stair encounter geometry screen

Stage: experiment and analysis. CPU and local source only. The outputs are
`route_audit.json` (per-sample evidence) and `proposed_stair_encounter.json`
(candidate coordinates). No Isaac contact, planner path, or human motion was
executed. `geometry_reviewed` remains **false**, and the separate Building
candidate's `APPROVED_ROUTE_SHA256` remains unset.

## Pinned inputs and method

| Input | SHA-256 |
| --- | --- |
| Building collision mesh USDA | `e55e4a9507441b8f1788503f909505a49b63d6eb36f6882ba782aee7c38a5d39` |
| PCT `new_building.pickle` | `ab5499ff100fe233f6cfabb59ce7592290cddd042c92ead5e37e9e2b593d24da` |
| Frozen P2B `planner.yaml` | `42a265a35cefb69eae43896acdd13780d1a7bd36a874b2f3aae967376b6e435e` |

The tool uses the exact selected PCT cells emitted by the clock-gated terrain
sidecar, subtracting its +0.03 m display offset. For each route point it
records the selected grid cell, world position, cost, XY query residual,
matched Building triangle ID, mesh height difference, signed surface normal,
and nearest overhead triangle. It samples lateral support every 0.05 m and
checks the frozen SCAN double-cylinder radius 0.25 m, front/rear offset
0.18 m, the official human 0.30 m horizontal envelope, and a 0.05 m margin.
Four nearby ground samples approximate human shoe placement. These are
geometry screens; the official animation's actual shoe contacts and robot
collisions must be checked in Isaac.

For the selected segment, matched ground triangles have signed normal z
between +0.970 and +1.000. The checker accepts `abs(normal_z) >= 0.7` so a
triangle with reversed winding is not mistaken for a wall; it records the
sign so winding remains reviewable. A missing overhead intersection is
recorded as `no_mesh_overhead_intersection_unknown_or_open`. It is neither a
measured obstacle nor measured free headroom, and the screen does not promote
it to a clearance pass. Every sample of the proposed encounter has a measured
overhead intersection.

## Screen outcome

At x=-5.30 m, a short robot segment along y=2.0 to 1.3 m has 8/8 supported
center samples, 8/8 front/rear placements, and 8/8 lateral fits under the
frozen 0.25 m cylinder radius plus margin. Its selected PCT ground height
rises from 0.740234375 to 0.859375 m at the final sampled step. The maximum
PCT-to-Building ground difference is 0.0061 m; measured overhead clearance is
at least 2.224 m. This is a **candidate reference corridor**, not the native
PCT/SCAN route that a future episode would actually follow.

The official person can be placed on the same tread at x=-5.30 m, y=1.4 to
1.9 m. Its six selected ground heights are all exactly 0.740234375 m, so a
linearly interpolated actor root stays on one measured tread and does not
cross a riser. All 6/6 center, sampled shoe, lateral, and overhead checks pass.
The maximum PCT-to-mesh difference is 0.00023 m; the measured overhead
clearance is 2.343 m, above the official visible height 1.736 m plus the
0.05 m screen margin. The robot and human intervals overlap from y=1.4 to
1.9 m. The recorded PCT source cells vary from `[26,110]` to `[26,115]`
across those six waypoints. Their **proposed initial poses are not safe**:
the robot center and person center are 0.60 m apart, but the forward robot
cylinder is 0.18 m closer, leaving a -0.13 m hull gap after the 0.25 m robot
and 0.30 m person radii. A separated staging pose and stopping/yield distance
need a separate design before any episode. Actor timing, sensed tracking, and
safe yielding remain untested.

A 0.4 m **transverse x crossing** on one stair tread was screened first. No
tested y had a 0.4 m run of valid official-human center positions. The longest
was 0.20 m (at y=5.5, 4.0, 3.5, and 1.8 m). At the upper landing y=-4.5 m,
the selected ground is 1.570 m but measured headroom at x=-5.3 m is only
1.513 m, shorter than the official person height. The secondary along-tread
pedestrian route above is therefore proposed for review. It must not be
relabelled as a full staircase traversal or crossing solution.

## Reproduce and limits

```sh
PYTHONDONTWRITEBYTECODE=1 python3 .pipeline/experiments/2026-09-23_scan_reactive_stair/isaac_candidate/route_audit/audit_stair_routes.py
PYTHONDONTWRITEBYTECODE=1 python3 .pipeline/experiments/2026-09-23_scan_reactive_stair/isaac_candidate/route_audit/test_route_audit.py -v
```

The 3 focused tests pass: pinned map/mesh and a real step-height difference,
correct selected PCT x/y source-cell indices, no-overhead interpretation,
initial overlap rejection, and the proposed segment/transverse rejection.
Evidence file SHA-256: `route_audit.json`
`6780e0201567355ba12f7689abac477b31753e1454ceb919fb274c710e38d98a`
and `proposed_stair_encounter.json`
`fb2b738cae58434f920a270e4bb42804cec52d20e48c559642c23b42b979c504`;
recompute hashes after any rerun. The JSON rows are
the authority for exact cell/triangle IDs and any later changes to the
candidate. The selected x/y poses lie up to 0.0563 m from their source PCT
cell centers. Continuous swept-body and foot contact, stair stance safety,
sensor returns from the official USD, and a live native PCT route still need
direct runtime evidence.
