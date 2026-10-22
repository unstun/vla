# v247 — generic native support and symmetric physical adjacency

Frozen source parent: v240. This treatment replaces the rejected v244
endpoint-anchor/component architecture. It adds no endpoint relocation,
component exception, Building coordinate condition or new body-oracle admission.

## Measured conclusions

- Strict removal of v135 alone is insufficient: each unchanged C++ A* map
  treatment admits only 1/12 requested directions. A04/G07's exhausted region
  grows from 1232 to 1337 states; it remains disconnected. Original PCT costs
  already exceed 20 at some legal endpoints. Restoring original gateways also
  does not resolve the matrix. See the audit ablation ledger.
- In the simplified physical mode, raw PCT cost no longer decides standability.
  A single native static-support helper serves both PCT and SCAN GridMap,
  preserving the original 0.35 m radius, 0.18 m offsets, scored support/drop
  guard, nearest-floor association and <0.26 m adjacent-height limit.
- PCT associates proxy slices with actual support floors and enumerates
  adjacent supported physical surfaces in both directions. DecideLayer/gateway
  and raw cost thresholds do not veto this mode. ENV225 remains the shared
  orientation-aware clearance/terrain objective; original smoothness/dynamic
  terms remain. Legacy raw-cost GPMP residual is disabled in this mode.
- The original PCT map bundle is restored; navigation/surface/physical-floor
  cloud and ENV225 bytes remain unchanged. The immutable native support export
  is hash-bound rather than an extra safety-margin mask.

## Verification

10855 sampled queries agree with the previous native typed support verdict
and with the exported field admission (zero mismatches). 97 native regression
cases and six PCT CTest targets pass, including synthetic reverse stairs,
ramps, genuine cliffs, nearest-floor/heading and slice-alias cases. All 11
non-B09 cases reach their goals in both actual C++ A* query directions.
B09 remains refused; only 14/72 sampled goal headings are supported.

The H00 original-route control uses its own fresh six-ray zero-physics fixture:
global native support admission, cold first SCAN publication and independent
final curve check pass; stale inputs still refuse. Global time 1.383 s and
cold local first-round time 0.117 s. This is a component control, not a new
historical full physical run.

## Frozen 12 x 5 component matrix

55/60 calls pass global native static-support admission, cold first-local
publication and its independent check. Every admitted call uses the original
third-attempt A* graph fallback; first GPMP passes are 0/60. This does not solve
smooth-path quality or planning latency. B09 fails 5/5 without moving its goal.
The table's raw-cloud margin is an independent voxel-solid comparison with
sqrt(3)*0.025 m padding, not observed collision freedom. ENV margins cap at
+0.15 m. Unknown observation coverage remains recorded separately.

| Case | Native chain | GPMP first | Graph fallback | ENV extra edge m | Raw-cloud solid m | Global median s | Local median s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A01 | 5/5 | 0 | 5 | 0.147524 | 0.098978 | 1.047 | 0.028 |
| A02 | 5/5 | 0 | 5 | 0.147524 | 0.098978 | 1.074 | 0.019 |
| A03 | 5/5 | 0 | 5 | 0.122721 | 0.098978 | 1.086 | 0.021 |
| A04 | 5/5 | 0 | 5 | 0.122721 | 0.098978 | 1.060 | 0.053 |
| G05 | 5/5 | 0 | 5 | 0.070000 | 0.098978 | 1.408 | 0.022 |
| G06 | 5/5 | 0 | 5 | 0.122721 | 0.098978 | 1.266 | 0.009 |
| G07 | 5/5 | 0 | 5 | 0.122721 | 0.098978 | 1.510 | 0.024 |
| B08 | 5/5 | 0 | 5 | 0.070000 | -0.189997 | 1.668 | 0.027 |
| B09 | 0/5 | 0 | 0 | N/A | N/A | 0.386 | N/A |
| R10 | 5/5 | 0 | 5 | 0.141554 | 0.098978 | 1.824 | 0.022 |
| R11 | 5/5 | 0 | 5 | 0.141554 | 0.098978 | 1.720 | 0.009 |
| R12 | 5/5 | 0 | 5 | 0.141554 | 0.098978 | 1.779 | 0.028 |

B08 has a negative raw-cloud global reference margin (-0.190 m). Its 5/5
component admission is not whole-route body-clearance qualification. Only
A02/G07/R11 were predeclared for physics and each has positive reference
raw-cloud comparison margin and 5/5 native component results. The practical
offline gate requires >=50/60 and all three predeclared strata 5/5; it passed.
Live SCAN observation, collision, dynamic, epoch and publication gates remain
mandatory. No claims of foot contact or future stepping coverage are made.

The scored repetitions share frozen fixtures/ROS epochs; they measure component
repeatability and wall durations, not live scheduling reliability. Physical
outcomes are recorded separately under v248. The selected baseline remains
v232/v233; no baseline promotion follows from this offline matrix.

## Provenance and reproduction

Source and installed inventories: results/source_inventory.json and
results/installed_files.json. Source snapshot: manifest.json and source/.
Run prepare.py, build.py, prepare_fixtures.py, native_regressions.sh/regressions.py,
historical_regression.py, native_receipt.py and freeze.py before run_matrix.py,
in the pinned gpu5070ti execution layout. Preserve every development/scored
ledger; do not overwrite frozen versions or reuse results as fresh runs.

Large map/clouds/native output and caches remain at
gpu5070ti:/data/sun/vla_mppi_20261009/physical_traversability_v247/.
Local compact matrix_summary.json contains each output hash and recorded
stage result. No compilation cache or raw point-cloud stream is returned.
