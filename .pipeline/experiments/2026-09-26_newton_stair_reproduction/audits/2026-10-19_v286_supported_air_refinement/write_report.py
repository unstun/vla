"""Write v286 results from verified returned evidence; never reuse old outcomes."""
from pathlib import Path
import csv,hashlib,json,statistics
HERE=Path(__file__).resolve().parent;V=HERE.parents[1]/'versions/v286'
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
num=lambda x,places=3:'n/a' if x is None else f'{x:.{places}f}'

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])

def main():
    g=load(HERE/'offline/offline_gate.json');matrix=load(HERE/'offline/matrix_summary.json')
    p=load(HERE/'physical_summary.json');q=load(V/'qualification_report.json');starts=load(HERE/'results/all50_start_verification.json')
    bill=load(HERE/'results/failure_terminal_bill.json');old=load(HERE/'results/reference_v285_error_counts.json')
    delivery=load(HERE/'results/local_physical_delivery_verification.json')
    visual=load(HERE/'results/visual_review.json')
    assert delivery['passed'] and delivery['full_local_videos_verified']==10 and not delivery['visual_review_pending']
    assert visual['passed'] and visual['return_inventory_sha256']==sha(HERE/'physical_return/return_inventory.json')
    assert delivery['visual_review_sha256']==sha(HERE/'results/visual_review.json')
    current={c['case_id']:c for c in bill['cases']};prior={c['case_id']:c for c in old['cases']}
    assert g['calls']==53 and len(matrix['calls'])==53 and p['formal_attempts']==10 and len(current)==10
    assert g['passed'] and starts['passed'] and q['passed']
    all_legal_times=[float(r['metrics']['global_s']) for r in matrix['calls'] if r['expected']=='admit']
    assert len(all_legal_times)==50 and statistics.median(all_legal_times)<=1.5
    old_bill=load(HERE.parent/'2026-10-19_v285_local_search_tracking/results/failure_terminal_bill.json')
    old_refinement={r['case_id']:r['refinement_error_count'] for r in old_bill['cases']}
    labels=[('pool_exhaustion','Ran out of pool'),('endpoint_adjustment_failed','Endpoint adjustment failed'),
        ('astar_optimization_failed','A-star failed'),('inside_obstacle','Robot inside obstacle'),
        ('lbfgs_minus1008','L-BFGS -1008'),('no_executable_trajectory','No executable trajectory')]
    totals=[]
    for key,label in labels:
        before=sum(c['counts'][key] for c in prior.values());after=sum(c['target_errors'][key] for c in current.values())
        totals.append([label,before,after,num(100*(1-after/before),1)+'%' if before else 'n/a'])
    error_rows=[]
    for c in p['cases']:
        cid=c['case_id'];a=prior[cid]['counts'];b=current[cid]['target_errors']
        error_rows.append([cid,*[f'{a[k]} → {b[k]}' for k,_ in labels]])
    rows=[[c['case_id'],c['terminal'],'yes' if c['goal_and_pd_passed'] else 'no',
        'yes' if c['goal_pd_and_physical_envelope_clear'] else 'no',num(c['simulation_duration_s']),
        num(c['physical_gap_min_m'],6),num(c['source_solid_min_m'],6),num(c['raw_point_min_m'],6),
        num(c['maximum_pause_after_first_translation_s'])] for c in p['cases']]
    endpoint=sum(len(c['endpoint_rejection_log_lines']) for c in p['cases'])
    comparison=load(HERE.parent/'2026-10-19_v285_local_search_tracking/physical_summary.json')
    prior_duration=sum(c['simulation_duration_s'] for c in comparison['cases']);duration=sum(c['simulation_duration_s'] for c in p['cases'])
    overall=p['goal_pd_and_all_recorded_physical_envelope_clear']==10 and p['scanner_deadline_failures']==0 and p['native_process_failures']==0
    report=f'''# v286 supported-air and local refinement results

Complete protocol: 53 scored offline cases, then ten distinct physical routes once each. Overall physical acceptance: **{'passed' if overall else 'unmet'}**. Offline acceptance: **passed**. Hard radius **0.35 m** and scanner period/deadline **0.1 s** remain unchanged. No navigation scene/coordinate branches, actual retries or baseline promotion.

## Results

- Offline legal passes: **{g['positive_passed']}/50 ({2*g['positive_passed']:.0f}%)**; illegal controls: **{g['illegal_correct_rejections']}/3** refused.
- Global median over admitted legal routes: **{g['global_median_s']:.6f} s**, p95 {g['global_p95_s']:.6f} s, maximum {g['global_max_s']:.6f} s. Across all 50 legal calls, including failed admission, median {statistics.median(all_legal_times):.6f} s and maximum {max(all_legal_times):.6f} s. Required median <=1.5 s.
- Physical goal plus terminal PD: **{p['goal_and_pd_passed']}/10**. Goal/PD plus sampled physical support and source/raw geometry: **{p['goal_pd_and_physical_envelope_clear']}/10**.
- Including all recorded startup and post-navigation poses, goal/PD plus sampled physical geometry: **{p['goal_pd_and_all_recorded_physical_envelope_clear']}/10**.
- Scanner jobs: {p['scanner_jobs']}; deadline failures: {p['scanner_deadline_failures']}; native process failures: {p['native_process_failures']}.
- Endpoint rejection log lines: {endpoint}; original global reference geometry preserved on {p['cases_with_original_global_geometry']}/10.

The physical acceptance target is **{'met' if overall else 'unmet'}** under the declared ten-route protocol. The route and whole-recording tables below determine the result; an incomplete route with positive geometry is not a pass. Compared with v285, goal/PD changes from {comparison['goal_and_pd_passed']}/10 to {p['goal_and_pd_passed']}/10, and goal/PD plus all-recorded geometry changes from {comparison['goal_pd_and_all_recorded_physical_envelope_clear']}/10 to {p['goal_pd_and_all_recorded_physical_envelope_clear']}/10.

## Changes and native verification

Parent is immutable v285. The complete owned diff is [changes.patch](../../versions/v286/changes.patch).

1. Unknown uninflated air is admitted only after the existing support, edge, selected-layer height, observation freshness and exact source-solid checks all pass. Measured-trunk geometry is unchanged. Real inflated hits, missing/stale support and true support gaps remain refusals.
2. Quantized terrain endpoints are checked at their projected support height along actual neighboring support edges. Quantization residuals no longer determine robot yaw or recheck the unprojected height. Local target-neighborhood queries now use the same terrain-aware A-star with the original goal tolerance; remote endpoints outside the local map use the existing checked forward-reference mechanism.
3. Environmental cost is removed only from second-stage combineCostRefine. First-stage rebound and final collision review remain. Smooth translation and phase share a 0.5–1.0 heading scale, with the original 0.6/1.0 rad transition. Final alignment, maximum speed, slew limits and the existing 0.15 m measured-seed fallback are unchanged.
4. Source-solid clearance has a local rebound-only 0.055 m quartic soft hinge outside the unchanged 0.35 m hard envelope. Its analytic control-point gradient agrees with individual-control and rigid-translation finite differences. ENV225 and global GPMP are unchanged; no source repulsion is added to refinement or GPMP.

{q['test_count']} native test executions pass (including one environmental suite through two entry points). The same new 13-check probe reproduces six targeted failures on immutable v285 and passes all 13 checks on v286; seven obstacle/support/freshness controls remain correct. The existing four hill/corner directions remain passed. Four translated/rotated tracker cases retain coupled nonzero travel and phase progress; final-yaw and emergency/cancel tests pass. Ten selected routes pass the final unscored initial planning check before freeze.

The first development probe had an invalid gradient-sign assertion: moving one control point also changes the spline heading. Its analytic and numerical gradients agreed. The final test checks individual-control differences and the rigid-translation repulsion direction; production mathematics was unchanged. Failed development receipts are retained and are not scored or physical attempts.

Native manifest SHA-256: `{sha(V/'native_manifest.json')}`. Execution manifest SHA-256: `{sha(V/'manifest.json')}`. [Native qualification](../../versions/v286/qualification_report.json), [source inventory](../../versions/v286/results/native_source_inventory.json).

## Complete offline cohort and all legal starts

The exact frozen v283 cohort/captured scans/endpoints are reused, including the existing G05 and CM02 replacements. No score-based resampling. All 53 timed native calls finish before independent geometry audits. Native timing uses the same two-CPU limit and excludes separately reported initialization. The host is shared; this is not an exclusive-host timing claim.

All 50 legal starts are independently rechecked by the frozen v286 native support and source fields, with unchanged extra-margin requirement >=0.10 m. Minimum support-gap extra margin {starts['minimum_support_gap_extra_m']:.9f} m; minimum source-solid extra margin {starts['minimum_source_solid_extra_m']:.9f} m. Each result agrees with its frozen start certificate. [All-start audit](results/all50_start_verification.json), [all 53 outcomes](offline/matrix_table.csv), [complete offline gate](offline/offline_gate.json).

Global admission: {g['global_admitted']}/50; first GPMP pass: {g['first_gpmp_passed']}/{g['global_admitted']} admitted. Every admitted/published result is independently checked against source and raw geometry; failures remain in the matrix. The strict complete offline gate passed before physical qualification. No inherited v285 timing waiver applies.

Legal offline failures: **{', '.join(r['case_id'] for r in matrix['calls'] if r['expected']=='admit' and not r['end_to_end_pass']) or 'none'}**. The complete matrix retains every call in the 50-case denominator.

## Ten actual physical attempts

A04, G05, CU06, D07, S04, CD12, CM02, CM07, CS03, CE03: one attempt each. Startup/preflight failures do not count as physical attempts; any such records are retained separately. Full failed prefixes remain failures. Clear geometry on an incomplete route is not full-route validation.

{table(['Route','Terminal','Goal + PD','Goal + PD + geometry','Physics s','Support gap m','Source solid m','Raw solid m','Max pause after motion s'],rows)}

Margins use measured navigation-window body poses at 10 Hz and saturate at +0.15 m. Physical support-gap margin is separate from static WrongHeight/other verdicts, which remain in the compact tables. Full physical geometry means nonnegative sampled support-gap/source/raw margins; it does not mean every original static verdict is Free. Original static-Free and stricter acceptance fields are also preserved. Startup and final PD are outside the comparable navigation window, and are additionally checked in the all-recording table below. Low-speed pauses may include permitted terminal yaw alignment and are not all mid-route deadlocks.

{table(['Route','Global epochs','Same reference','>=60 s pauses after motion','Max nonterminal pure-yaw s','Nonterminal settling samples','Local success/completed'],[[c['case_id'],c['global_route_epoch_count'],c['global_reference_geometry_preserved'],c['pauses_ge_60s_after_first_translation'],num(c['maximum_nonterminal_pure_yaw_s']),c['nonterminal_stand_settling_samples'],f"{c['local_successes']}/{c['local_completed']}"] for c in p['cases']])}

## Entire recording and post-navigation geometry

These values include every recorded body pose, including factory startup and the final settling/PD tail. They do not control the robot or add a publication gate. The separate navigation-window values above retain comparability with v285.

{table(['Route','All-recorded support gap m','All-recorded source m','All-recorded raw m','Post-navigation source m','Post-navigation raw m','Goal/PD + all-recorded geometry'],[[c['case_id'],num(c['all_recorded_support_gap_min_m'],6),num(c['all_recorded_source_solid_min_m'],6),num(c['all_recorded_raw_point_min_m'],6),num(c['post_navigation_source_solid_min_m'],6),num(c['post_navigation_raw_point_min_m'],6),c['goal_pd_and_all_recorded_physical_envelope_clear']] for c in p['cases']])}

## Error comparison against unchanged v285 recordings

Counts below are per-line literal log mentions under the same extractor, including retries; they are not counts of independent crashes or failed missions. v285 had four routes without goal/PD completion and one additional geometry failure. Current terminal outcomes are in the table above. Total physical duration differs: v285 {prior_duration:.3f} s, v286 {duration:.3f} s, so raw count reductions alone do not establish a causal or reliability result.

{table(['Message','v285 mentions','v286 mentions','Reduction'],totals)}

{table(['Route',*[label for _,label in labels]],error_rows)}

Reactive blocked-query log mentions retain their original verdict and voxel codes. In particular, v285 was not 100% unknown air; observed/inflated hits also occurred and remain refusals. These are candidate-query diagnostics, not measured-body collision counts.

{table(['Route','v285 Unknown(6/0)','v286 Unknown(6/0)','v285 Observed(7/2)','v286 Observed(7/2)'],[[c['case_id'],sum(r['mentions'] for r in prior[c['case_id']]['reactive_blocked'] if (r['verdict'],r['voxel'])==(6,0)),sum(r['mentions'] for r in current[c['case_id']]['reactive_blocked'] if (r['verdict'],r['voxel'])==(6,0)),sum(r['mentions'] for r in prior[c['case_id']]['reactive_blocked'] if (r['verdict'],r['voxel'])==(7,2)),sum(r['mentions'] for r in current[c['case_id']]['reactive_blocked'] if (r['verdict'],r['voxel'])==(7,2))] for c in p['cases']])}

{table(['Route','Rebound -1008 before → after','Refine -1008 before → after','Progress-failure mentions before → after'],[[c['case_id'],*[str(prior[c['case_id']]['stage_errors'][k])+' → '+str(current[c['case_id']]['stage_errors'][k]) for k in ['rebound_minus1008','refine_minus1008','failed_to_make_progress']]] for c in p['cases']])}

Refinement-only solver-error counts use the same original `Solver error while refining` extractor as the v285 failure bill; they are reported separately from all -1008 mentions.

{table(['Route','v285 refinement solver errors','v286 refinement solver errors'],[[c['case_id'],old_refinement[c['case_id']],current[c['case_id']]['refinement_error_count']] for c in p['cases']])}

{table(['Route','Measured-seed fallbacks','Distance triggered','Occupancy triggered','Largest distance before fallback m'],[[c['case_id'],current[c['case_id']]['measured_seed_fallback']['count'],current[c['case_id']]['measured_seed_fallback']['distance_triggered'],current[c['case_id']]['measured_seed_fallback']['occupancy_triggered'],num(current[c['case_id']]['measured_seed_fallback']['maximum_predicted_distance_before_fallback_m'],6)] for c in p['cases']])}

The remaining `The robot is inside an obstacle` warning comes from `BsplineOptimizer::check_collision_and_rebound`: after an occupied control point is found, it searches backward through control points; when none is free it logs that warning and sets `in_id=0`. It is not a direct measured-body test or, by itself, proof of a runaway initial seed. Existing native source and actual body audits must be read together. First error contexts are retained in the failure bill.

The combined v286 iteration tests the four requested repairs together; physical outcomes do not isolate each change's causal contribution. The fallback table records actual native FSM decisions. It does not reconstruct the internal tracker phase from wall time: v286 intentionally scales that phase. Phase/translation consistency is directly checked in the native clock tests; actual physical symptoms and geometry remain separate evidence. [Failure bill](results/failure_terminal_bill.json), [unchanged v285 baseline extraction](results/reference_v285_error_counts.json).

## Videos, source return and limits

Ten regular local MP4 files, {p['video_bytes']} bytes total, cover the full actual attempts. Each is bound to its original recorded states and frozen version, fully decoded and render-only verified with zero new physics. Local frame checks are recorded separately. [All ten full videos](delivered/README.md), [compact physical table](physical_table.csv), [returned file hashes](physical_return/return_inventory.json).

Local return verification checks the returned compact-file inventory, analysis-source hashes, frozen execution source/snapshot pairs and every MP4 SHA-256. All ten videos pass a second full decode locally. Twenty temporal samples across the ten cases are visually inspected. [Local delivery verification](results/local_physical_delivery_verification.json), [visual review](results/visual_review.json). Detached coordinator receipts and positive physics-step counts establish the once-per-route execution record.

Raw recordings stay on gpu5070ti at `/home/sun/vla_exec/physical_runs_v286`; compact source/configuration, reports/provenance and review videos return locally. Physical startup uses the previously authorized capacity admission (available RAM >=16 GiB, output disk >=10 GiB; GPU occupancy observed); physics/policy remain CPU, and rendering may share available GPU capacity. Other jobs are untouched. The five prior v283 startup-failure records and frozen v283/v284/v285 sources remain preserved.

This is one attempt per route, not a statistical reliability study. Sampled measured-body geometry is not continuous-time clearance or foot-contact certification. A zero command is not proof that the body is stationary. Removing a cost, successful native tests or a safe reference is not itself evidence of physical success. Remaining failures and excursions are not relabeled as passes. The selected baseline remains v232/v233.
'''
    (HERE/'RESULTS.md').write_text(report)
    (V/'RESULTS.md').write_text('# v286 results\n\nSee the [complete report](../../audits/2026-10-19_v286_supported_air_refinement/RESULTS.md).\n\n'+f"Offline {g['positive_passed']}/50 legal, {g['illegal_correct_rejections']}/3 illegal, global median {g['global_median_s']:.6f} s. Physical goal/PD {p['goal_and_pd_passed']}/10; with sampled physical geometry {p['goal_pd_and_physical_envelope_clear']}/10. Exact 0.35 m and 0.1 s; no retries or baseline promotion.\n")
    videos=HERE/'delivered';videos.mkdir(exist_ok=True)
    (videos/'README.md').write_text('# v286 full physical videos\n\nOne actual attempt per route; full failures retained. Video rendering adds zero physics.\n\n'+table(['Route','Video','SHA-256'],[[c['case_id'],f"[Full attempt](v286_{c['case_id']}_full_attempt01.mp4)",c['video_sha256']] for c in p['cases']])+'\n')
    with (HERE/'error_comparison.csv').open('w') as f:
        writer=csv.writer(f);writer.writerow(['case_id',*[key for key,_ in labels]]);writer.writerows(error_rows)
    print(json.dumps(dict(report=str(HERE/'RESULTS.md'),offline_passed=g['passed'],physical_acceptance_passed=overall)))

if __name__=='__main__':main()
