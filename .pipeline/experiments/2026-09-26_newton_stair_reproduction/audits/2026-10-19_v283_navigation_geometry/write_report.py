"""Write the v283 report from returned, verified numerical and video evidence."""
from pathlib import Path
import csv
import hashlib
import json
import math
import re

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1] / 'versions/v283'
load = lambda p: json.loads(p.read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
fmt = lambda x: 'unavailable' if x is None else f'{x:.6f}'
yes = lambda x: 'pass' if x else 'FAIL'


def main():
    summary = load(HERE / 'physical_summary.json')
    rows = summary['cases']
    assert len(rows) == 10
    offline = load(VERSION / 'results/offline_gate.json')
    previous = load(HERE.parent / '2026-10-19_v280_source_generalization/physical_summary.json')
    parent = {r['case_id']: r for r in previous['cases']}
    starts = load(VERSION / 'start_admission.json')
    visual = load(HERE / 'results/visual_review.json')
    bill = load(HERE / 'results/failure_terminal_bill.json')
    assert bill['analysis_source_sha256'] == sha(HERE / 'failure_bill.py')
    control = load(HERE / 'results/candidate_recording/control_witnesses.json')
    assert control['analysis_source_sha256'] == sha(HERE / 'witness_controls.py')
    assert visual['reviewed_cases'] == [r['case_id'] for r in rows]
    assert visual['all_reviewed']
    pd_rows = []
    for row in rows:
        cid = row['case_id']
        results = HERE / 'physical_return' / cid / 'results'
        window = load(results / 'window_audit.json')
        diagnostic = load(results / 'physical_diagnostics.json')
        poses = list(csv.DictReader((results / 'body_margins_with_raw.csv').open()))
        support = [json.loads(s) for s in (results / 'physical_support_margins.jsonl').read_text().splitlines()]
        assert len(poses) == len(support)
        index = min(range(len(poses)), key=lambda i: abs(float(poses[i]['time_s']) - window['goal_request_physics_s']))
        pose = poses[index]
        assert abs(float(pose['time_s']) - window['goal_request_physics_s']) <= .11
        spawn = diagnostic['actual_spawn_ground']
        pd_rows.append(dict(case_id=cid, goal_request_physics_s=window['goal_request_physics_s'],
            sampled_physics_s=float(pose['time_s']),
            post_PD_xy_displacement_m=math.hypot(float(pose['x'])-spawn[0], float(pose['y'])-spawn[1]),
            support_verdict=support[index]['hard_support_verdict'],
            physical_support_gap_extra_m=support[index]['support_gap_extra_margin_m'],
            source_solid_extra_m=float(pose['native_source_solid_margin_m']),
            raw_point_extra_m=float(pose['raw_point_margin_m'])))
    (HERE / 'post_pd_start_audit.json').write_text(json.dumps(dict(cases=pd_rows,
        scope='Nearest10Hz measured pose to the original goal-request snapshot, after factory PD. Not a maximum over the entire startup trajectory.'), indent=2)+'\n')
    endpoints = []
    for row in rows:
        for line in row['endpoint_rejection_log_lines']:
            fields = dict(re.findall(r'(role|support|solid|repair|live_hint)=([^\s"]+)', line))
            endpoints.append(dict(case_id=row['case_id'], fields=fields, log=line))
    (HERE / 'endpoint_rejections.json').write_text(json.dumps(endpoints, indent=2)+'\n')
    geometry_clear = sum(r['measured_geometry_clear'] for r in rows)
    solid_bad = [r['case_id'] for r in rows if r['source_solid_min_m'] < -1e-10]
    support_bad = [r['case_id'] for r in rows if r['hard_support_free'] != r['hard_support_samples']]
    endpoint_free = [r for r in endpoints if r['fields'].get('support') == '0' and r['fields'].get('solid') == '0']
    text = [
        '# v283 — Full offline and ten-route physical evaluation',
        '',
        f'The updated offline gate passes 49/50 legal cases (98%) and correctly refuses 3/3 illegal controls, '
        f'with CPU2 median global solve {offline["global_median_s"]:.6f}s. All ten frozen '
        f'physical routes were then executed once. Goal and terminal-PD acceptance passes '
        f'{summary["goal_and_pd_passed"]}/10; {summary["goal_pd_and_measured_geometry_clear"]}/10 '
        f'also clear the sampled geometric screen. Overall physical repair acceptance '
        f'{"passes" if geometry_clear == 10 and not endpoint_free else "is NOT met"}.',
        '',
        'CD12 now has no sampled SupportGap and positive solid clearance. Solid-envelope '
        'violations remain in D07/S04/CE03, including a new S04 regression. Three other '
        'routes contain WrongHeight refusals; local progress/trajectory/settling failures '
        'also remain. These failures prevent acceptance of v283 as a completed repair.',
        '',
        'Every failed outcome and complete recorded video prefix is retained. Five earlier '
        'disk-gate launch rejections performed zero physics and are excluded from the '
        'ten-attempt denominator. No physical retry, frozen navigation-source change, '
        '0.35m/0.1s relaxation, production scene/coordinate special case, policy change '
        'or baseline adoption occurred.',
        '',
        '## Changes and source identity',
        '',
        '- Global route-selection feedback is request-scoped at endpoint attachment cells '
        'and connections. Required static checks remain authoritative. Reused references '
        'trim the obsolete prefix and validate the remaining route and measured connector. Initial static readiness '
        'polls within the original 1500 ms total request budget.',
        '- The common local optimizer/publication/controller collision query now checks '
        'the same exact StaticSolidField/static traversability as global planning before '
        'the existing live query. No second approximate static ESDF was introduced.',
        '- Warm continuation must agree with both measured cylinder centers within half '
        'the existing map resolution; otherwise the existing measured-state initializer '
        'owns the seed. This addresses the recorded CD12 stale theoretical seed, without '
        'certifying later physical tracking.',
        '- All 50 legal starts require physical support-gap and source-solid extra margins>=0.10m. '
        'Eight geometry-only replacements: G05,CU04,CU08,CU11,CU12,CU13,CM01,CM02. '
        'The other 42 starts, all goals/headings and three illegal controls are unchanged. '
        'There are exactly 50 distinct spatial start/goal pairs.',
        '',
        f'Native SHA256: `{summary["native_manifest_sha256"]}`. Execution SHA256: '
        f'`{summary["execution_manifest_sha256"]}`. The unchanged profile is radius0.35m, '
        'offset0.18m, original vertical envelope, factory PD/RL and scanner period/deadline0.1s.',
        '',
        'The 171 inherited native tests pass. Endpoint contrasts pass0/12 on v280 and 12/12 '
        'on v283 under translation/rotation. The same source-wall witness with a free live '
        'buffer is allowed by the parent local query and rejected by v283. Readiness resumes '
        'after 30.475 ms; persistent absence times out 1.50008 s within the original request budget. '
        'Recorded CD12 reconstruction found0.32–0.36m displacement and0.43–0.54rad yaw '
        'disagreement despite a clear newly published curve. This reconstruction is not an '
        'exact original asynchronous replay.',
        '',
        '## Complete 53-case offline result',
        '',
        f'All 53 scored calls and 53 independent audits finished once. First GPMP passes 47/50 '
        f'(94%) or47/49 admitted (95.92%). CPU2 admitted global median/p95/max are '
        f'{offline["global_median_s"]:.6f}/{offline["global_p95_s"]:.6f}/{offline["global_max_s"]:.6f}s; '
        'all50 legal median/p95/max are1.316707/1.916303/2.589370s. Cold initialization '
        'is separate. CS01 retains its no-route failure; CS02/CE01 retain first-GPMP '
        'SupportGap failures before successful graph fallback. All ten physical selections '
        'pass offline admission. Admitted/published independent support/source/raw checks '
        'have no negative hard margin. The minimum global source/raw margins are '
        '+0.005710/+0.006174m at CD12; local minima cap at+0.15m.',
        '',
        'An offline pass means global route admission plus a local publication from '
        'the captured request. It is not a complete physical mission rollout.',
        '',
        'See [full53-case table](offline/matrix_table.csv), [offline report](../../versions/v283/OFFLINE_RESULTS.md), '
        '[native ledger](offline/native_ledger.json), [audit ledger](offline/audit_ledger.json) '
        'and [all50 start certificates](../../versions/v283/start_admission.json), with an '
        '[all50 old/new start table](all50_start_audit.csv). '
        'New98% versus v281 96% is not an algorithm-only paired comparison because eight starts changed.',
        '',
        '## All ten physical attempts',
        '',
        'Margins below use 10 Hz measured body poses during navigation, including planning '
        'waits and turns, excluding startup and final PD. +0.15m is a reporting cap. '
        'SupportGap clearance and source/raw solids are distinct from the retained ENV soft proxy.',
        '',
        '| Route | Recorded terminal | Goal + PD | Geometry | Support free / poses | Physical gap min m | Source solid min m | Raw point min m |',
        '|---|---|---|---|---:|---:|---:|---:|',
    ]
    for r in rows:
        text.append(f'| {r["case_id"]} | {r["terminal"]} | {yes(r["goal_and_pd_passed"])} | '
            f'{yes(r["measured_geometry_clear"])} | {r["hard_support_free"]}/{r["hard_support_samples"]} | '
            f'{fmt(r["physical_gap_min_m"])} | {fmt(r["source_solid_min_m"])} | {fmt(r["raw_point_min_m"])} |')
    text += ['', f'Sampled support refusals occur in: {", ".join(support_bad) or "none"}. '
        f'Negative source-solid margins occur in: {", ".join(solid_bad) or "none"}. '
        'The14 support refusals are WrongHeight(10); no navigation-window sample '
        'has SupportGap(11). A positive gap margin does not waive another hard support verdict.', '',
        '### Endpoint and remaining failure evidence', '',
        f'There are {len(endpoints)} endpoint-pose rejection log lines; '
        f'{len(endpoint_free)} have both static supportFree and solidFree. '
        'These typed diagnostics do not substitute for the measured-pose audit.', '']
    text += ['Global planner action failures, including recovered events:', '',
        '| Route | Reason and count |', '|---|---|']
    for r in rows:
        counts={}
        for line in r['planner_failure_log_lines']:
            reason = line.split('Native PCT: ', 1)[-1].rstrip('"')
            counts[reason]=counts.get(reason,0)+1
        if counts:text.append('| '+r['case_id']+' | '+'; '.join('`'+reason+'` ×'+str(count) for reason,count in counts.items())+' |')
    text += ['', 'Failed-route controller/mission errors from the original log:', '']
    for r in bill['cases']:
        if r['finish']['backend_terminal_status'] == 'FAILED':
            for line in r['mission_error_lines']:
                text.append(f'- {r["case_id"]}: `{line.split("]: ",1)[-1]}`.')
    text += ['', 'Refinement -1008/line-search errors also occur on arrived routes; '
        'they are retained in the [full terminal bill](results/failure_terminal_bill.json) '
        'and are not by themselves proof of the terminal cause.', '']
    text += ['', '### D07, CD12 and CS03 comparison', '',
        '| Route | v282 source solid min m | v283 source solid min m | v282 physical gap min m | v283 physical gap min m | v283 SupportGap(11) poses |',
        '|---|---:|---:|---:|---:|---:|']
    for r in rows:
        if r['case_id'] not in ('D07','CD12','CS03'):continue
        old=parent[r['case_id']]
        text.append(f'| {r["case_id"]} | {fmt(old["source_solid_min_m"])} | {fmt(r["source_solid_min_m"])} | '
            f'{fmt(old["physical_gap_min_m"])} | {fmt(r["physical_gap_min_m"])} | '
            f'{r["hard_support_verdict_counts"].get("11",0)} |')
    text += ['', 'These are single independent physical attempts with evolving state; the '
        'comparison does not isolate one mechanism causally.', '',
        '**S04 is a regression:** its earlier v282 sampled geometry passed, while this '
        'attempt has a negative source/raw solid margin despite goal/PD completion.', '',
        '### Remaining command/physical tracking gap', '',
        'At the inspected D07/S04 excursions, all sampled published-curve poses in '
        'this reconstruction are source/support-clear. D07 at270.462830s has7.90mm position discrepancy and '
        '1.629964rad nominal heading discrepancy; the applied command is pure yaw '
        '`[0,0,+1]`. S04 at37.610958s has0.312647m position discrepancy and applied '
        'command `[0,0,-1]`. At the first S04 excursion36.511562s, the applied command '
        'is zero while horizontal velocity remains about0.423m/s in STAND_SETTLING.', '',
        'The pinned tracker emits final/in-place yaw through `publishStop(yaw_rate)` '
        'before advancing curve phase. `LocalMotion::command` checks finite command '
        'values but does not apply a measured-pose swept-rotation query to that '
        'returned command. This uncovered command-owner gap is outside the new '
        'local curve query and warm-start binding. Later work must cover actual '
        'heading/terminal commands and zero-command drift with the same geometry; '
        'this frozen version is not silently repaired or retried.', '',
        'See [curve query/geometry reconstruction](results/candidate_recording/recorded_summary.json) '
        'and [actual applied-control/source evidence](results/candidate_recording/control_witnesses.json). '
        'This uses nominal published-time phase; actual tracker phase freezes during '
        'yaw control. It is not an exact asynchronous tracker replay, and time past '
        'the nominal curve end does not prove the internal phase expired.', '',
        '### Factory-PD start screen', '',
        'The following nearest 10 Hz goal-request samples check the measured post-PD state. '
        'They are not maximum drift over the entire crouch/stand trajectory.', '',
        '| Route | Post-PD XY shift m | Support verdict | Physical gap extra m | Source solid extra m |',
        '|---|---:|---:|---:|---:|']
    for r in pd_rows:text.append(f'| {r["case_id"]} | {fmt(r["post_PD_xy_displacement_m"])} | {r["support_verdict"]} | '
        f'{fmt(r["physical_support_gap_extra_m"])} | {fmt(r["source_solid_extra_m"])} |')
    text += ['', '### Local planning, pauses and scanner timing', '',
        '| Route | Local success / completed | Pauses >=0.5s / >=1s | Max pause s | Scan jobs | Deadline failures | Max scan ms |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:text.append(f'| {r["case_id"]} | {r["local_successes"]}/{r["local_completed"]} | '
        f'{r["pauses_ge_05s"]}/{r["pauses_ge_1s"]} | {fmt(r["maximum_pause_s"])} | '
        f'{r["scanner_jobs"]} | {r["scanner_deadline_failures"]} | {r["maximum_scan_ms"]:.3f} |')
    text += ['', f'Total scans:{summary["scanner_jobs"]}; deadline failures:{summary["scanner_deadline_failures"]}; '
        f'native process failures:{summary["native_process_failures"]}. Successful-local-round rate '
        'and measured travel speed are separate. Long failed-route holds remain in pause counts.', '',
        '## Recovery, storage and media delivery', '',
        'Five original disk-gate failures (A04/G05/CU06/D07/S04) contain only entry setup '
        'files and exact pre-simulator tracebacks; the processes exited after about0.03s. '
        'The original misleading early-ledger status is preserved with an evidence-based '
        '[correction receipt](results/recovery/zero_physics_launch_failures01/summary.json). '
        'All failed task directories/receipts remain remote with per-file hashes.', '',
        'The inactive5,288,964,998byte archive was copied to '
        '`/home/sun/vla_exec/relocated_archives/mac_archive_20261012`; all37 files/modes '
        'were verified before freeing the redundant source. The old `/data` path remains '
        'a symlink. [Relocation receipt](results/recovery/archive_relocation.json) records '
        'free space rising from10,550,161,408 to15,839,219,712bytes. No source or gate changed.', '',
        f'All ten real local MP4s total{summary["video_bytes"]:,}bytes; '
        f'the primary compact evidence bundle contains{summary["compact_files"]} files '
        f'totaling{summary["compact_bytes"]:,}bytes. '
        'Each video has matching source-state coverage, full decode, SHA256, first/last '
        'recorded-state and zero-render-physics checks. At least two local frames per route were '
        'visually inspected. See [video index](delivered/README.md), '
        '[return inventory](physical_return/return_inventory.json), '
        '[visual review](results/visual_review.json), [physical table](physical_table.csv) '
        'and [machine-readable summary](physical_summary.json).', '',
        'CM07 uses camera-only revision03 because local review found a pillar '
        'blocking the original terminal view. The near follow camera and wider FOV '
        'restore full-body visibility; scene geometry is unchanged. All2951 source '
        'frame indices/times, physical input hashes and terminal labels match the '
        '[original view](physical_return/CM07/results/camera_revision_verification.json). '
        'Original camera01 and intermediate02 masters/source snapshots remain remote; '
        'the original failed visual sample is retained locally. No physical attempt '
        'was repeated.', '',
        'Heavy raw/archive/build data remains at `gpu5070ti:/home/sun/vla_exec/physical_runs_v283/` '
        'and the private native/benchmark root. Per-case capture snapshot receipts bind '
        'remote archive sizes and hashes. Regenerate media from unchanged captured states '
        'using the locally versioned audit tools; never repeat formal physics for a video.', '',
        'The[physical resource summary](results/physical_resource_summary.json) contains38 '
        'one-minute observations during formal dispatches: no sampled GPU-compute overlap '
        'or resource-gate failure, minimum available RAM25,044,774,912bytes and output '
        'free disk46,489,845,760bytes. This is not continuous exclusivity proof. The '
        '[post-physics full source/install check](results/post_all_physics_source_gate.json) passes.', '',
        'All physical admission gates were retained. After six videos, the recorded-state '
        'dispatcher was resumed with separate rendering admission (all ten physical cases '
        'already closed,8GiB available RAM,2GiB free GPU memory,10GiB disk; nice10). '
        'This permits shared-GPU video work without changing any physical source, '
        'threshold, run or outcome. [Transition](results/render_dispatch_transition.json) '
        'and [render resource probes](results/render_resource_observations.jsonl) retain '
        'the original completed six results and subsequent peer GPU overlap.', '',
        '## Acceptance and limits', '',
        '- AC3/AC4/AC5: all50 starts, fixed profile/version contracts and complete offline gate pass.',
        '- AC1/AC2: component and recorded-input contrasts pass; remaining physical failures '
        'and typed rejection evidence above determine the narrower supported claim.',
        f'- AC6: {"passes the sampled screen" if geometry_clear == 10 and not endpoint_free else "FAILS the declared all-ten sampled geometry / endpoint screen"}. '
        'This version must not be presented as a completed physical repair.',
        '- AC7: ten full-prefix local videos and verified compact evidence delivered.', '',
        'Ten-hertz torso geometry does not certify continuous motion or foot contact. '
        'One attempt per route does not establish statistical reliability. CPU2 is a '
        'shared-host protocol, not exclusive-host timing. Resource observations and '
        'every unsuccessful prefix are preserved. No frozen failed version is rewritten '
        'and no selected baseline is advanced.', '',
        f'Report inputs: physical summary SHA256 `{sha(HERE / "physical_summary.json")}`; '
        f'return inventory SHA256 `{sha(HERE / "physical_return/return_inventory.json")}`.', '']
    report='\n'.join(text)
    for before,after in (('pass0/12','pass 0/12'),('or47/49','or 47/49'),
        ('are1.','are 1.'),('full53-case','full 53-case'),('New98%','New 98%'),
        ('all37','all 37'),('All2951','All 2951'),('The14','The 14'),
        ('found0.','found 0.'),('and0.','and 0.'),('at270.','at 270.'),('at37.','at 37.'),
        ('excursion36.','excursion 36.'),('has7.','has 7.'),('has0.','has 0.'),
        ('about0.','about 0.'),('inactive5,','inactive 5,'),('from10,','from 10,'),
        ('to15,','to 15,'),('total171,','total 171,'),('contains465','contains 465'),
        ('totaling20,','totaling 20,'),('The[physical','The [physical'),('contains38','contains 38'),
        ('RAM25,','RAM 25,'),('disk46,','disk 46,'),('closed,8','closed, 8'),
        ('RAM,2','RAM, 2'),('memory,10','memory, 10'),('radius0.','radius 0.'),
        ('offset0.','offset 0.'),('deadline0.','deadline 0.'),('cap at+','cap at +'),
        ('scans:14881','scans: 14881'),('failures:0','failures: 0')):
        report=report.replace(before,after)
    report=re.sub(r'(\d)(GiB|MiB|bytes|byte|mm|ms|rad|Hz|s|m)\b',r'\1 \2',report)
    report=re.sub(r'\ball50\b','all 50',report)
    (HERE / 'RESULTS.md').write_text(report)
    (VERSION / 'RESULTS.md').write_text('# v283 results\n\n'
        'See the [complete offline and ten-route physical report]'
        '(../../audits/2026-10-19_v283_navigation_geometry/RESULTS.md) and '
        '[ten complete videos](../../audits/2026-10-19_v283_navigation_geometry/delivered/README.md).\n\n'
        f'Offline49/50 legal +3/3 illegal; physical goal/PD{summary["goal_and_pd_passed"]}/10, '
        f'goal/PD plus sampled geometry{summary["goal_pd_and_measured_geometry_clear"]}/10. '
        'Physical acceptance fails. CD12 has no sampled SupportGap, but '
        'D07/S04/CE03 retain negative solid margins; S04 is a regression. '
        'No frozen source/threshold change or baseline adoption.\n')


if __name__ == '__main__':
    main()
