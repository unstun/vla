# v256 / v257 — Static solids repaired; full-space gate failed

Stage: experiment and analysis. **The expanded offline cohort does not qualify for physical execution.** Frozen v256 repairs the B08 hard-solid omission; frozen v257 executes 52 distinct cases once each. 34/49 predeclared positive cases pass global/static/cold SCAN, all 34 on first GPMP. All three predeclared illegal controls are refused. Fifteen positive cases fail. No new formal Newton attempt, video, commit, archive or selected-baseline promotion occurred. v258 is an unfrozen conditional execution preparation only.

## B08 root cause and repair

The old static admission predicate tested physical support but omitted non-ground body solids. Frozen v254 reproduced the B08 admission twice, with no static rejected poses despite the legacy original-cloud score −0.186928809 m. That minimum voxel itself contains three upward-facing floor returns: its 4.533–5.098 labels describe overlying-floor association, not physical material thickness. A separate **original vertical wall point** at (−6.4347811, −3.2528491, 4.9316163), normal (1,0,0), penetrates the original returned double-cylinder pose by 0.133301882 m even without voxel padding. This independently establishes the unsafe original returned pose.

v256 shares one immutable StaticSolidField between PCT continuous graph edges, GPMP hard-feasibility residual and dense final static review (`StaticObstacle=7`). The finite-cylinder SDF, original source uncertainty and PCL implementation are reused from v224. Both consumers require the same source identity and geometry. Physical support/layer transition and ENV225 soft preference remain separate. No coordinate conditions, endpoint relocation or component policy were added.

Correcting the source material annotation is necessary before making it hard. SOLID256B preserves every original solid XYZ and every existing below-floor-volume association. It additionally records actual source-Z bands only for voxels whose **all original normals face upward**; either independently documented floor association can exempt floor material for that queried floor. Mixed/vertical/downward voxels receive no new exemption. A failed replacement-only experiment revoked existing slab exemptions and failed original controls; its evidence remains remote and it was not frozen. The original ENV225 soft atlas and legacy raw reference remain unchanged.

At the original unsafe returned B08 pose/yaw, the final independent margin remains **−0.183233718 m**, with native typed verdict **7**. This is not an all-heading rejection of that XYZ. The actual requested B08 control remains unadmitted. The 0.35 m radius, ±0.18 m centres, up/down 0.55/0.35 m, 0.30 m body clearance, support/height/step limits, RL, 0.1 s scanner and v237 deadline semantics are unchanged.

Qualification before freezing: 61 plugin/geometry tests across eight targets, 97 native regressions across twelve targets (10 overlap; 148 distinct test cases); 10,928 independent SciPy/Numpy poses against runtime PCL, zero value/admission/binary mismatches, maximum margin error 4.44e−16 m. Fourteen original controls include the original twelve, H00 and the measured A02 request: ten original positive cases retain first-GPMP/global/SCAN admission, B08/B09 refuse, H00 passes and measured A02 preserves its exact continuous endpoint and first-GPMP/static admission. The measured A02 diagnostic is not a new physical or cold-SCAN result.

## Frozen 52-case outcome

This cohort has **52 distinct spatial pairs, 52 distinct start positions, 52 distinct goal positions**, explicit start and terminal yaw, and no scored substitution or retry. Distribution: 17 ascents, 15 descents, eight intermediate routes, six same-floor constrictions and six boundary/control cases. A04/G05 keep their original coordinates. U14 is the near-stair back-facing case (actual initial departure turn 3.0613 rad). Each uses six original per-case geometric scans captured with zero physics steps; all 312 capture jobs meet 0.1 s. This is offline sensor geometry, not physical scheduling or post-PD validation.

| Stratum | All | Predeclared positive | Full-chain positive passes | Correct illegal refusals |
|---|---:|---:|---:|---:|
| ascent | 17 | 17 | 14 | 0 |
| descent | 15 | 15 | 7 | 0 |
| intermediate | 8 | 8 | 8 | 0 |
| same_floor | 6 | 6 | 4 | 0 |
| boundary | 6 | 3 | 1 | 3 |

- Positive full-chain rate: **34/49 = 69.39%**, below the prospective ≥90% requirement. Correct expected outcomes including illegal controls: 37/52 = 71.15%.
- First GPMP/static passes: **34/34 admitted routes = 100%**; also report **34/49 positive requests**, not “100% across the building.” All 34 SCAN first curves publish and pass the independent solid audit; none is an admitted unsmoothed fallback.
- Independent negative solid margin among admitted global paths or first local curves: **zero**. Global minimum **0.020531857 m** (U08); local minimum **0.076167873 m** (U08). ENV additional edge minimum **0.020000381 m** (G05). Each margin caps at 0.15 m.
- Accepted start/goal XYZ errors are exactly zero in the sampled route; maximum terminal-yaw error is floating-point roundoff (2.22e−16 rad).
- With the recorded two-CPU evaluation quota, admitted global wall time median **16.4555 s**, maximum **23.9309 s**. First SCAN publication median **32.6909 ms**, P95 **287.7557 ms**, maximum **439.9019 ms**. The new hard graph queries add substantial global cost; no former ~0.35 s global or sustained-local-frequency claim survives this measurement.
- U08 and M03 have negative **legacy** raw margins (−0.0170601 / −0.0114442 m), but independent corrected-material margins are positive (0.0205319 / 0.0878671 m). Both channels are kept in the CSV; the changed floor annotation is disclosed rather than the legacy channel being overwritten.

See [all 52 exact endpoints and scores](ALL_CASES.md), [machine-readable table](ALL_CASES.csv), [coverage map](coverage.png), [original failed gate](../../versions/v257/results/compact/offline_gate.json), and [all per-case logs and typed witnesses](../../versions/v257/results/compact/cases/).

## What the failures establish

The original expected labels remain immutable. Endpoint standability alone did not prove route reachability; five nominal positives have now acquired separate original-mesh disconnection evidence. They remain failures in the original 49-positive denominator.

1. **U13, D12, D14, D15, S03:** original Newton mesh diagnosis finds the pertinent ground endpoints in wall-separated regions with no upward surface permitting a first ≤0.26 m step. This uses the weaker heading-independent disk of radius sqrt(0.35²−0.18²)−1 μm, an un-eroded floor projection and inscribed wall buffers, with no point-cloud padding. Even that permissive necessary geometry is disconnected under the unchanged standing/step contract. It is an offline certificate, not a runtime component rule or post-score label change. Original USD and exported Newton triangles were compared exactly. The open mesh's winding values and zero-radius polygonization are retained as preliminary diagnostics and **not used as occupancy truth**.
2. **U11, U12, D09, D10, D11, D13:** exact global error is `pct_no_route`; true physical disconnection has not been established for these six. Separate installed graph ablations show U11/U12 still fail with the added solid query disabled, with all observed rejected transitions typed `UnknownSupport(8)` (2,615 / 2,589 in that support-only observer). D09/D13 also remain no-route in support-only diagnostics. These expose unresolved support coverage/association versus real geometry; unknown support was not accepted. D10/D11 were not separately ablated and are not assigned the same proven cause by extrapolation.
3. **E02:** the selected endpoint is individually Free, with 0.0493854 m solid margin. The support-only installed graph finds a path; the exact solid-enabled graph does not. Whether this is genuine approach infeasibility, a conservative source-material boundary or lattice-direction incompleteness remains unresolved. It is not relabeled as an illegal point or moved inward.
4. **D07, S04, E03:** graph/GPMP output exists but dense pose/yaw review refuses it on all inherited attempts, including fallback. Source inspection shows the PCT solver consumes XYZ, while RoutePolicy writes the requested terminal orientation afterward; intermediate static poses interpolate both translation and yaw. A Free endpoint is therefore not proof of a feasible approach rotation. The following are actual first rejected poses; counts are **sample occurrences across repeated internal review requests**, not independent routes or unique physical poses.

| Case | First rejected body XYZ m | Planned yaw rad | Verdict | Aggregate typed occurrences |
|---|---|---:|---:|---|
| D07 | (5.45784181, 7.18693156, 0.35803010) | 1.79898641 | 7 | `{"7": 130}` |
| S04 | (7.91933527, 7.14673842, 4.83953001) | 0.79665281 | 8 | `{"8": 76}` |
| E03 | (5.47637474, -6.28697121, 4.83949329) | -2.68879980 | 7 | `{"7": 36, "8": 149}` |

Verdict 7 = StaticObstacle; 8 = UnknownSupport. The final checker is correctly stopping these sampled trajectories. Source/interface mismatch motivates a generic orientation-consistency investigation; no claim is made that every such rejected connection has a feasible alternative. Diagnostic graph ablations are recorded separately in `graph_diagnosis.log`; they never replace the one scored case invocation.

## Conditional physical cohort and next executable boundary

The frozen ranking produced A04, G05, U14, D04, D06, M01, M05, S01, S05 and E01 as eligible candidates. **The global physical-admission flag is false.** These ten survivors are not claimed to be the hardest routes across the full building. They were not run to conceal the fifteen failed positives. The prepared v258 binding and explicit-heading driver are not frozen or runtime-qualified. `delivered/` therefore has no new videos.

Next investigate original floor geometry at the UnknownSupport frontier, and bring the actual endpoint/connection yaw into the same physical feasibility domain used by search, smoothing and final review. Preserve all 52 requests and labels for any newly versioned comparison, plus independent mesh adjudication as a separate analysis. Do not add coordinate rules, endpoint snapping, unknown-space waivers or wider step/radius tolerances. Requalify the full cohort before one frozen 8–10-route Newton cohort. Profile the static-solid broad phase with exact query parity before claiming latency recovery.

## Local return and provenance

Local repository remains the only source of truth. The 495-file compact return is 4,101,680 bytes and each returned file was locally SHA-256 checked. It includes all 52 per-case scenarios, capture receipts, logs, metrics, original expected labels, first typed witnesses, independent solid audits, and remote inventories. Source, installed libraries, fixture identities and evaluator hashes were rechecked after scoring. Heavy clouds/scans, route sample arrays, diagnostic frontiers, build objects and raw data remain at `/data/sun/vla_mppi_20261009/space_coverage_v257` and `generic_mechanisms_v256` on gpu5070ti; the inventories give exact bytes/SHA and local scripts provide reconstruction. No CMakeFiles, model, raw scan or raw physical archive was returned.

- Native v256 manifest: `cbfbc0d09162a3411aae3a6e6861b5f03919da12e302f14d4cc1afc2fd59531c`.
- Evaluator v257 manifest: `fcc0a966993413d24bfbd8fc992c213b0b439112713c5e28a205081e151c7172`.
- 52-case manifest: `93e1b304cee649aa45113d7e09020657d87a6c0c8b2dfffded3de8b8f2bca569`.
- SOLID256B SHA: `e27f308f4bf6e69a6cb09ed72f3ad32f493933114319ba7ba0b7d51f2d02f3ac`; FNV `17629216882668158307`.
- Original PCD SHA: `8721efeb74415336d47c97d861d6e30ad213669b120d5b37c62461100c1f2eae`.
- RL SHA: `7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b`.

Original v219/v220 comparison and user-selected v232/v233 baseline remain unchanged. Earlier v252/v255 physical videos are earlier treatments, not v256 evidence.
