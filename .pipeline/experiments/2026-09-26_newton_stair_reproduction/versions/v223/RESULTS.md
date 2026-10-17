# v223: physical-floor association and exact rejection reasons

Status: component and recorded-input validation passed; zero new physics steps. Parent source is v221 attempt03. The v217 42–62 s recording is replayed with the inherited v219 native mapper. The accepted physical run remains v219.

## Changed behavior

`physicalSupportDiagnostic` associates a physical floor independently of `selectedSurface`. When the evidence-fill drop guard prevented that floor from becoming selected support, the caller reports the new appended enum `EdgeClearance` (12). The report includes floor height, square-to-square guard gap, witness coordinates and evidence category. It does not insert an admissible surface or change any hard predicate. No recovery connector or execution-state protocol was added.

At the exact 48.10519028 s planning query, floor z is 1.5580306959 m and the guard gap is 0.2828427125 m. The 0.35 m guard still rejects it. Both cylinders have free obstacle verdicts at that exact planning yaw. At 49.1146 and 58.1447 s, edge rejection additionally overlaps historical nonterrain occupancy, including voxel (7.575, -3.725, 1.575). These exact planning queries use logged planning yaw; the 78 recorded-body queries use measured yaw. They are different query sets.

## Validation

- Nine packages build. Colcon reports 158 test records, zero failures; this includes wrapper records, not 158 distinct cases.
- 508 ordered scans; 78 diagnostic frames; 126,324 identical sampled queries.
- Binary changes versus the previous v219 replay: **0**. Explanation/native mismatches: **0**.
- Three exact failed planning queries: all now `EdgeClearance`; binary changes: **0**.
- Torso/voxel OBB predicate checked against python-fcl 0.7.0.8 on 5,000 seeded pairs, including 100 near-contact pairs: **0 mismatches**.

An existing fixture used two consecutive clock reads, allowing its observation to be newer than its query. The test now uses one timestamp; production freshness checks are unchanged. Failed attempts are retained remotely.

## Rejection ledger

The denominator is queries, not independent collisions, planning attempts or elapsed seconds. Sampled surface points dominate this deliberately dense diagnostic set.

| Query group | Queries | Rejected | Edge guard | Historical 1/0/1 and occupied cylinder | Cylinder occupied, torso clear |
|---|---:|---:|---:|---:|---:|
| Recorded body poses | 78 | 59 | 59 | 59 | 59 |
| Forward reference samples | 2,283 | 205 | 0 | 27 | 27 |
| Surface-domain samples | 123,318 | 50,346 | 24,804 | 19,050 | 23,729 |
| Recorded seed samples | 645 | 7 | 0 | 7 | 7 |
| Total | 126,324 | 50,617 | 24,863 | 19,143 | 23,822 |

The last three columns overlap and must not be added. All 59 rejected recorded-body queries satisfy all three predicates. Of the 19,143 history-overlapping rejections, 3,298 include the specified voxel. Other nonterrain contributors can coexist with the history flag; removing that one voxel is not proven sufficient.

A mutually exclusive ledger using the first rejecting cylinder/predicate is:

| First reason | Queries |
|---|---:|
| EdgeClearance | 17,769 |
| UnknownSupport at associated footprint | 12,855 |
| Explicit support-gap mask | 10,303 |
| UnknownObstacle | 7,423 |
| StaticObstacle | 2,267 |
| Total | 50,617 |

No `WrongHeight` remains in this sampled window. Support-gap and unknown-support rejections still exist independently of the physical-floor relabeling.

For exact overlap accounting, E = edge guard, H = historical 1/0/1 within an occupied cylinder, X = cylinder occupied and torso clear:

| E | H | X | Rejected queries |
|---:|---:|---:|---:|
| 0 | 0 | 0 | 15,714 |
| 1 | 0 | 0 | 8,370 |
| 0 | 0 | 1 | 3,622 |
| 1 | 0 | 1 | 3,768 |
| 0 | 1 | 1 | 6,418 |
| 1 | 1 | 0 | 2,711 |
| 1 | 1 | 1 | 10,014 |

Only **1,847** sampled rejections have solely an occupied-cylinder first verdict, a clear torso, and no remaining support/unknown rejection in either cylinder. Holding support rules fixed, swapping only the occupancy envelope could clear these queries in this recorded map. This count is **0** for recorded-body poses and for all three exact failed planning queries. It is not an executable trajectory count.

## Geometry and evidence boundaries

The comparison uses the two torso collision boxes from the pinned Lite3 URDF, with the same query XYZ/yaw as the cylinders. It checks nonterrain raw voxel intersections, including retained history. It excludes legs, swing trajectories and future contacts. It also excludes actual roll/pitch in the same-yaw comparison. The earlier 78-pose original-mesh/actual-orientation audit is a separate experiment and is not substituted for this one.

The 0.283 m value is a grid square-gap guard measure, not physical foot margin. Extra cylinder rejection and historical occupancy are two dimensions of the same possible failure, not alternative mutually exclusive diagnoses.

Machine-readable results: [attribution_summary.json](results/attribution_summary.json), [geometry_oracle.json](results/geometry_oracle.json), [test-result.log](results/attempt02/test-result.log), [source inventory](results/source_inventory.json). Every replay CSV has its SHA-256 and byte count in the summary. Full CSVs and retained attempts live at `gpu5070ti:/data/sun/vla_mppi_20261009/floor_reason_v223/`; they are regenerated by `replay/run.sh` and `replay/summarize.py` against the preserved replay inputs. No frozen run or display pointer was changed.
