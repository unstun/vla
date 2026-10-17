# v229: first-round support-aligned GPMP reference

Status: validated recorded-input implementation gate. Parent v228 is frozen.
No physics steps, training, robot actuation or accepted physical-source promotion.

The actual installed PCT plugin now admits the shared GPMP reference on its
first check: 3821 native STATIC_ONLY samples, zero rejection, exact original
XYZ goal. v228 rejected 26/3422 intermediate samples and used two repairs before
returning the raw A* fallback. The final v229 route has 3413 poses, including
collinear XY samples used to resolve terrain-height transitions. The original
GPMP XY polyline, original start/goal, native thresholds and RL are preserved.

| Actual installed plugin | v228 shared | v229 shared |
|---|---:|---:|
| Native admission requests | 3 | 1 |
| Rejected samples by request | 26, 152, 0 | 0 |
| Final checked samples | 4650 | 3821 |
| XYZ goal error | 0 m | 0 m |
| Full planning/repair/admission | 1.032185 s | 0.727385 s |
| Final length | 79.302078 m | 80.330027 m |
| Extra support-edge margin | 0.147524 m | 0.141488 m |
| Raw point-cloud solid margin | 0.064950 m | 0.056539 m |

The removed repair rounds save 29.53% in this measurement. The requested
~0.35 s has not been achieved: the unchanged GPMP 100-iteration optimization
alone takes 0.643 s in the installed-plugin call. No iteration/weight/tolerance
change is included. Standalone search+smoothing takes 0.660 s with zero native
rejections across 3583 samples. This is one host measurement, not a latency SLA.

The frozen v224 raw point-cloud scorer independently checks all 3821 final
samples, including connector and yaw interpolation. Minimum solid margin is
+0.056539 m, raw integrated cost 0.000169493, maximum atlas optimism 0.000686 m.
This remains the declared static voxel/cylinder oracle; STATIC_ONLY does not
prove live 3-D clearance, leg contact, future support or closed-loop execution.
Projection restores terrain-relative Z and is not a new dynamic Z controller.

Unconfigured mode preserves its route (729 poses, 4739 checked samples, length
79.083625954850362 m, zero final rejection) and its original third-round fallback.
Its raw solid margin remains -0.029809 m. Shared mode has not altered that mode.

## Implementation and failed attempts

Reuse PCT's matched GPMP layers, canonical v228 cells, ground validity/ceiling,
and ENV225 original surface heights. Project Z into the intersection of the
navigation proxy and actual surface's original native clearance/tolerance
bands, with a 5 mm quantization inset. Prefer actual surface+reference height.
Neighbor bands bound interpolation; ambiguous/missing association or disconnected
bands reject. Final native checking remains mandatory. No native geometry or
admission changes are made.

Initial attempts incorrectly treated nominal body clearance as a hard minimum,
first rejecting the float16-offset original goal and then disconnecting a step.
Both failures and their exact source revisions remain under results/. The final
helper uses both original tolerance bands. Regression cases cover the original
goal, navigation proxy depression, true height error, 18 cm step connectivity,
missing surface and impossible ceiling. Final component gate: nine packages,
168 colcon records (148 distinct cases plus 20 wrappers), zero failures/errors/skips.

## Original collision window

All 126324 original v217 queries and three critical queries retain the same
binary verdicts as v223. Independently recorded cylinder, historical 1/0/1,
other occupancy, torso and unknown predicates have zero changes. At
48.10519028 s the 1.5580306959152221 m floor remains associated, and
0.28284271247461906 < 0.35 m still rejects with EdgeClearance. No edge waiver
or recovery connector was introduced.

Evidence: results/{build_probe03,field_probe02,admission_probe02,raw_route03}.log,
results/build/attempt03/, results/test_xml/, results/replay_comparison.json and
results/admission_output02/. Source identity, composed inventory and sync gate
bind the actual executed bytes. Full replay CSVs remain on gpu5070ti under
/data/sun/vla_mppi_20261009/support_height_v229/replay_output01/ with returned
SHA-256/size. tools/return_results.py returns only explicit logs, test XML,
compact receipts, source revisions and final route CSVs; no CMake intermediates.
