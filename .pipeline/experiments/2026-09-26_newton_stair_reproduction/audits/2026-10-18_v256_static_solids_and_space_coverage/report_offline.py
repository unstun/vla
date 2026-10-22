"""Render the original frozen 52-case result, without post-score relabeling."""
from pathlib import Path
import collections,csv,hashlib,json,math,statistics
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1];V=EXP/'versions'
R=V/'v257/results/compact';summary=json.loads((R/'matrix_summary.json').read_text())
manifest=json.loads((V/'v257/cases_manifest.json').read_text());cases={c['case_id']:c for c in manifest['cases']}
rows=summary['calls'];positive=[r for r in rows if r['expected']=='admit'];admitted=[r for r in rows if r['global_admitted']]
assert len(rows)==52 and len(positive)==49 and len(admitted)==34
assert not summary['gate']['passed']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((R/'return_receipt.json').read_text())
for rel,item in receipt['files'].items():
 p=R/rel;assert sha(p)==item['sha256'] and p.stat().st_size==item['bytes'],rel
fmt=lambda x:'—' if x is None else f'{x:.5f}'
xyz=lambda p:'('+', '.join(f'{x:.5f}' for x in p)+')'
strata=[]
for name in ('ascent','descent','intermediate','same_floor','boundary'):
 rr=[r for r in rows if r['stratum']==name];pp=[r for r in rr if r['expected']=='admit']
 strata.append(f"| {name} | {len(rr)} | {len(pp)} | {sum(r['end_to_end_pass'] for r in pp)} | {sum(r['expected']=='reject' and r['expected_outcome_pass'] for r in rr)} |")
table=['| Case | Expected | Global | First GPMP | SCAN | ENV edge m | Independent solid m | Local solid m | First publish ms | Rejection |','|---|---|---|---|---|---:|---:|---:|---:|---|']
for r in rows:
 m=r['metrics'];yes=lambda key:'pass' if r[key] else '—'
 table.append(f"| {r['case_id']} | {r['expected']} | {yes('global_admitted')} | {yes('first_gpmp_static_pass')} | {yes('scan_published')} | {fmt(r['edge_margin_min'])} | {fmt(r['raw_solid_margin_min'])} | {fmt(r['local_raw_solid_margin_min'])} | {fmt(m.get('scan_first_publish_s')*1000 if m.get('scan_first_publish_s') is not None else None)} | {m.get('global_error','').replace('Native PCT: ','')} |")
full=['# v257 — All 52 distinct requested spatial cases','',
 'All coordinates are ground XYZ in metres. Requested headings are radians. Body reference is ground + 0.30 m. Original expected labels remain unchanged after scoring. Every row has one cold scored invocation; diagnostic graph ablations are separate.','',
 '| Case | Stratum | Expected | Start XYZ | Start yaw | Goal XYZ | Goal yaw |','|---|---|---|---|---:|---|---:|']
for c in manifest['cases']:
 full.append(f"| {c['case_id']} | {c['stratum']} | {c['expected']} | {xyz(c['start']['ground'])} | {c['start']['yaw']:.8f} | {xyz(c['goal']['ground'])} | {c['goal']['yaw']:.8f} |")
full+=['','Full scores follow. Margins saturate at 0.15 m; a saturated value means at least that much scored clearance, not an exact distant obstacle distance. ENV edge is additional clearance beyond the unchanged 0.35 m support geometry. Missing values mean no admitted route or no SCAN evaluation, never a zero-distance measurement.','']+table
(HERE/'ALL_CASES.md').write_text('\n'.join(full)+'\n')
with (HERE/'ALL_CASES.csv').open('w') as f:
 keys=['case_id','stratum','expected','start_xyz','start_yaw','goal_xyz','goal_yaw','global_admitted','first_gpmp_static_pass','scan_published','end_to_end_pass','edge_margin_min','raw_solid_margin_min','legacy_raw_solid_margin_min','local_raw_solid_margin_min','global_s','scan_first_round_s','scan_first_publish_s','rejection']
 w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
 for r in rows:
  c=cases[r['case_id']];a={k:r.get(k) for k in keys};a.update(start_xyz=json.dumps(c['start']['ground']),start_yaw=c['start']['yaw'],goal_xyz=json.dumps(c['goal']['ground']),goal_yaw=c['goal']['yaw'])
  a.update({k:r['metrics'].get(k) for k in ('global_s','scan_first_round_s','scan_first_publish_s')});a['rejection']=r['metrics'].get('global_error','');w.writerow(a)
typed=[]
for cid in ('D07','S04','E03'):
 rr=next(r for r in rows if r['case_id']==cid);requests=json.loads((R/'cases'/cid/'static_witnesses.json').read_text());first=next(r['first_rejected'] for r in requests if r['rejected'])
 typed.append(f"| {cid} | ({float(first['x']):.8f}, {float(first['y']):.8f}, {float(first['z']):.8f}) | {float(first['yaw']):.8f} | {first['verdict']} | `{json.dumps(rr['static_rejection_counts'],sort_keys=True)}` |")
report='''# v256 / v257 — Static solids repaired; full-space gate failed

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
'''+ '\n'.join(strata)+'''

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
'''+ '\n'.join(typed)+'''

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
'''
(HERE/'RESULTS.md').write_text(report)
(HERE/'delivered').mkdir(exist_ok=True)
(HERE/'delivered/README.md').write_text('# No v256 physical delivery\n\nv257 did not pass the prospective 52-case offline gate. No v258 formal physical attempt was started and no new recording exists. Earlier v252/v255 videos remain under their original audits and are not evidence for v256. See [the failed offline report](../RESULTS.md).\n')
(V/'v256/RESULTS.md').write_text('# v256 — Offline native solid-body repair qualified\n\nFrozen from v254; B08 original unsafe pose is now StaticObstacle(7), independent margin −0.183233718 m. Shared 0.35 m non-ground body geometry is used in graph, GPMP and static admission; original support/RL/sensor thresholds are unchanged. 61 plugin tests and 97 native regressions pass (10 overlapping; 148 distinct), with zero mismatches over 10,928 independent solid poses. Original controls retain ten positive first-GPMP/SCAN passes, B08/B09 refusals, H00 and exact measured A02 checks.\n\nThis is a native repair qualification only. The subsequent frozen v257 expanded 52-case cohort fails its prospective physical gate (34/49 positive full-chain). No new physical acceptance claim. See [complete mechanism and expanded evidence](../../audits/2026-10-18_v256_static_solids_and_space_coverage/RESULTS.md), [native receipt](results/acceptance_receipt.json) and [manifest](manifest.json).\n')
(V/'v257/RESULTS.md').write_text('# v257 — 52 distinct spatial cases scored; physical gate failed\n\nInstalled frozen v256, one cold scored call per distinct case. 52 different start positions and 52 different goals, with explicit start/goal yaw. 34/49 predeclared positives pass global/static/SCAN; all 34 first-GPMP; 3/3 illegal controls refused. Zero admitted negative independent global/local solid margins. The ≥90% positive requirement fails (69.39%). Original labels, failures and gate are retained.\n\nNo Newton attempt or new video. v258 preparation remains unfrozen. See [full report](../../audits/2026-10-18_v256_static_solids_and_space_coverage/RESULTS.md), [all cases and coordinates](../../audits/2026-10-18_v256_static_solids_and_space_coverage/ALL_CASES.md), [scored table](results/compact/matrix_table.csv), [failed gate](results/compact/offline_gate.json), [local verified provenance](results/compact/return_receipt.json) and [frozen manifest](manifest.json).\n')
print(json.dumps(dict(report=str(HERE/'RESULTS.md'),cases=52,positive_passed=34,positive_total=49,physics_attempts=0)))
