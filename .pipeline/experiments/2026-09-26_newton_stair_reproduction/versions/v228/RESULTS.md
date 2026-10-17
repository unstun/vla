# v228: admitted Building reference with shared scoring

Status: validated recorded-input implementation gate. Both actual installed
PCT modes return complete references to the original XYZ goal, and every final
sample passes an independent native STATIC_ONLY support recheck. No new physics,
training, robot actuation or accepted-source promotion. v219/v220 remain the
accepted physical source/display pair.

## Final returned route, including repair and admission

Same original Building map, pinned XYZ endpoints and explicit zero endpoint
yaws. Actual installed plugin, RoutePolicy, service client, bounded repair,
connector/rotation sampler and native GridMap are exercised. These are the
final returned references, not preliminary search or smoothing outputs.

| Final reference | Unconfigured scoring | Shared scoring |
|---|---:|---:|
| Returned poses | 729 | 731 |
| Native static recheck samples | 4739 | 4650 |
| Rejected final samples | 0 | 0 |
| XYZ goal error | 0 m | 0 m |
| Length | 79.0836 m | 79.3021 m |
| Integrated environmental cost | 0.969377 | 0.023304 |
| Minimum extra edge margin | 0.026370 m | 0.147524 m |
| Minimum atlas static-solid margin | -0.029111 m | 0.065481 m |
| Entire planning/repair/admission call | 0.2253 s | 1.0322 s |

The environmental cost drops 97.60% with a 0.28% length increase. Edge margin
is extra beyond the existing 0.35 m envelope, not foot-placement margin. Static
solid scores use the declared original PCD prior and the v225 approximation;
STATIC_ONLY itself checks native support/gap geometry, not live 3-D occupancy.
The negative legacy prior margin must not be described as a native live hit.

Both references use the existing third-round raw-graph fallback. The first
two smoothed candidates are rejected; no rejected spline is published. Shared
requests reject 26,152,0 samples; legacy 23,18,0. GPMP's independent height
smoothing remains inconsistent at some stairs. This gate establishes a useful,
fully checked returned global reference, not valid smoothed height everywhere.

Evidence: `results/admission_probe01.log`,
`results/admission_output01/{legacy,shared}_admitted.csv`.

The frozen v224 raw point-cloud scorer independently resamples the retained
full-precision XYZ/yaw routes with the same connector/rotation sampler. Counts
match 4739/4650. Raw minimum solid margins are -0.029809/0.064950 m; integrated
raw costs 0.971201/0.018673. On the shared final route, maximum atlas optimism
is 0.000669 m, maximum absolute error 0.010958 m, and raw minimum edge margin
remains 0.147524 m. The positive final clearance therefore does not rely on an
atlas interpolation underestimate. This is the declared static voxel/cylinder
oracle, not a leg-contact or live-space certificate. `results/raw_route02.log`
retains its result. The tool's first build lacked a generated-interface include
dependency; that failed build remains in `results/raw_route01.log`.

## Source-bound cell identity

TerrainBundle checks the original PCT bytes against the existing manifest and
reads the PCTMAP01 header. It binds nominal lower cell-edge origin
(-7.99531478881836,-9.636811256408691) m into the native profile. Qualified
matching sources use half-open cells, normalizing double-arithmetic ULPs only.
Source-cloud minima, actual query XYZ, heights, selected labels, LiDAR classifier,
ETH adjacency, the .12/.26 height rules, .35 evidence-fill drop guard and gap
mask remain unchanged. Unconfigured sources retain their original lookup.

All five exact corner witnesses from v224/v225/v227 pass. v227's physical-origin
attempt remains frozen as a failed comparison; do not reuse its profile.

## Intermediate stages and latency

The shared A* graph retains 0.125601/0.127614 m minimum edge/solid margins,
zero rejected samples out of 3563. Shared smoothing retains
0.142418/0.145824 m but has 26/3422 WrongHeight samples. That is why the actual
admission/repair outcome above is reported separately.

Search+smoothing takes 0.6994 s, versus v224's 8.023 s. The configured optimizer
uses its existing 100-iteration cap; no tolerance is relaxed. Its original
velocity-coupled heading and objective weight remain. Active SCAN environmental
cost+gradient takes 0.03674 ms; this is one objective evaluation, not total
controller latency. v225's 0.113 s prematurely stopped geometry is not combined
with this version's improved margins.

## Original window and components

9 packages pass. 167 colcon records comprise 147 distinct test cases plus
20 wrappers, zero errors/failures/skips. New tests bind the nominal origin to
the verified header, exercise both sides of cell boundaries, preserve wrong
height and unknown/occupied rejection, and retain the original classifier.
Earlier full-factor, curve, corridor-selection and legacy regressions remain.

All 126,324 original v217 queries and three exact planning queries preserve
their binary verdicts against v223. Every independently recorded occupancy
predicate has zero changes, including historical 1/0/1 and unknown evidence.
The 48.10519028 s query still associates floor 1.5580306959152221 m and rejects
0.28284271247461906 < 0.35 m with EdgeClearance. The other exact queries retain
0.3162277660 and 0.3000000000 m edge rejections. No recovery connector or edge
waiver is introduced. The overlapping and first-reason ledger remains in
v223/RESULTS.md; this later cell correction does not invalidate its counts.

`results/replay_comparison.json` returns the compact comparison and SHA-256/size
of remote full CSVs. Heavy replay bytes remain at
`gpu5070ti:/data/sun/vla_mppi_20261009/environment_lattice_v228/replay_output01/`.
Regenerate using `replay/run.sh` against the archived input/critical_input and
the newly generated SHA-bound profile, then `replay/compare.py`.

Atlas approximation failures remain explicit in v225/RESULTS.md. No leg
contact, unknown future live-space, closed-loop navigation or new physics
acceptance is inferred from this offline result. Upstream pins, licenses and
reuse remain in v224/REUSE.md; local source/remote execution hashes are bound
by this version's source inventory, sync receipt and frozen manifest.
