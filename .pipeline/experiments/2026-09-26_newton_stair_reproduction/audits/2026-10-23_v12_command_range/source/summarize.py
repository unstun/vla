"""Verify frozen extraction and write compact tables; never reads remote data."""
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from audit import MAIN_BANDS, FINE_BANDS, empty_band, finish_band


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize():
    frozen = json.loads((ROOT / 'frozen.json').read_text())
    for name, identity in frozen['files'].items():
        assert sha(ROOT / name) == identity['sha256'], name
    receipt = json.loads((ROOT / 'results/extract01.receipt.json').read_text())
    assert receipt['returncode'] == 0
    assert sha(ROOT / 'results/extract01.jsonl') == receipt['extract01.jsonl']['sha256']
    records = [json.loads(s) for s in (ROOT / 'results/extract01.jsonl').read_text().splitlines()]
    request = json.loads((ROOT / 'request.json').read_text())
    runs = [r for r in records if r['type'] == 'run']
    assert records[0]['type'] == 'header' and records[-1]['type'] == 'complete'
    assert records[0]['frozen_sha256'] == sha(ROOT / 'frozen.json')
    assert records[0]['source_sha256'] == frozen['files']['source/audit.py']['sha256']
    assert [r['run'] for r in runs] == [r['run'] for r in request['runs']]
    assert len(runs) == records[-1]['count'] == 34
    assert records[0]['host'] == 'ubun' and records[0]['nice'] == 19
    source_n = source_bytes = 0
    band_rows, yaw_rows, run_rows = [], [], []
    for r in runs:
        for s in r['sources'].values():
            assert s['matches_historical'] and s['stable_read'], r['run']
            source_n += 1
            source_bytes += s['bytes']
        a = r['analysis']
        if a['status'] != 'ok':
            continue
        total = a['duration_s']
        assert math.isclose(sum(b['duration_s'] for b in a['bands'].values()), total, abs_tol=1e-8)
        assert math.isclose(sum(b['duration_s'] for b in a['fine_bands'].values()), total, abs_tol=1e-8)
        assert math.isclose(a['low_inclusive_share'] + a['high_inclusive_share'],
                            1 - a['bands']['zero']['share_all'] + a['bands']['exact_0p2']['share_all'], abs_tol=1e-10)
        intervals = a['pure_yaw_intervals']
        assert math.isclose(sum(x['duration_s'] for x in intervals), a['pure_yaw_total_s'], abs_tol=1e-9)
        assert max((x['duration_s'] for x in intervals), default=0.) == a['pure_yaw_longest_s']
        assert a['pure_yaw_total_s'] <= a['bands']['zero']['duration_s'] + 1e-9
        for q in intervals:
            assert a['start_s'] <= q['start_s'] <= q['end_s'] <= a['end_s']
            assert q['max_xy_displacement_cm'] >= q['net_xy_displacement_cm'] - 1e-9
            yaw_rows.append(dict(run=r['run'], **q))
        for kind in ('bands', 'fine_bands'):
            for name, values in a[kind].items():
                band_rows.append(dict(run=r['run'], window_kind=a['window_kind'], kind=kind, band=name, **values))
        run_rows.append(dict(run=r['run'], cohort=r['cohort'], variant=r['variant'], case_id=r['case_id'],
                            repeat=r['repeat'], historical_scanner_failure=bool(r['historical_outcome']['scanner_deadline_failures']),
                            **{k:a[k] for k in ['window_kind','start_s','end_s','duration_s','low_inclusive_share',
                               'high_inclusive_share','low_share_nonzero','pure_yaw_total_s','pure_yaw_longest_s',
                               'pure_yaw_max_displacement_cm','terminal_weighted_rows','sample_gaps_over_0p04_s']}))
    groups = []
    for window in ('goal_circle', 'fallback_before_first_zero'):
        for cohort, variant in [('original10','v290'), ('paired24','v290'), ('paired24','v291')]:
            selected = [r for r in runs if r['cohort']==cohort and r['variant']==variant and r['analysis'].get('window_kind')==window]
            total = sum(r['analysis']['duration_s'] for r in selected)
            aggregate = {}
            for kind, names in [('bands', MAIN_BANDS), ('fine_bands', FINE_BANDS)]:
                aggregate[kind] = {}
                for name in names:
                    accumulator = empty_band()
                    for r in selected:
                        for key in accumulator:
                            accumulator[key] += r['analysis'][kind][name][key]
                    aggregate[kind][name] = finish_band(accumulator, total)
            nonzero = total - aggregate['bands']['zero']['duration_s']
            low = aggregate['bands']['below_0p2']['duration_s'] + aggregate['bands']['exact_0p2']['duration_s']
            groups.append(dict(window_kind=window,cohort=cohort,variant=variant,run_count=len(selected),duration_s=total,
                               nonzero_duration_s=nonzero,low_nonzero_share=low/nonzero if nonzero else None,**aggregate))
    summary = dict(runs=run_rows,groups=groups,run_count=len(runs),missing_runs=[],
                   unavailable_runs=[r['run'] for r in runs if r['analysis']['status']!='ok'],
                   window_counts=dict(Counter(r['analysis'].get('window_kind','unavailable') for r in runs)),
                   verified_source_files=source_n,verified_source_bytes=source_bytes,
                   total_telemetry_rows=sum(r['telemetry_rows'] for r in runs),
                   pure_yaw_interval_count=len(yaw_rows),pure_yaw_total_s=sum(q['duration_s'] for q in yaw_rows),
                   pure_yaw_max_heading_deg=max((abs(q['heading_change_rad'])*180/math.pi for q in yaw_rows),default=None),
                   extraction_sha256=sha(ROOT/'results/extract01.jsonl'),frozen_sha256=sha(ROOT/'frozen.json'),
                   new_physics_steps=0)
    for name, value in [('summary.json',summary), ('bands.json',band_rows), ('pure_yaw_intervals.json',yaw_rows)]:
        (ROOT/'results'/name).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    for name, values in [('runs.csv',run_rows),('bands.csv',band_rows),('pure_yaw_intervals.csv',yaw_rows)]:
        with (ROOT/'results'/name).open('w') as f:
            writer=csv.DictWriter(f,fieldnames=list(values[0]));writer.writeheader();writer.writerows(values)
    verification=dict(passed=not summary['unavailable_runs'],checks={
        'frozen_source_unchanged':True,'exact_34_run_order':True,'all_source_hashes_match':True,
        'duration_partition':True,'inclusive_overlap':True,'pure_yaw_intervals_reconcile':True,
        'all_failures_retained':True,'zero_new_physics':True},
        source_files=source_n,source_bytes=source_bytes,extract_wall_s=records[-1]['wall_seconds'],
        launcher_wall_s=receipt['ended_epoch_s']-receipt['started_epoch_s'],
        script_sha256=sha(Path(__file__)),extraction_sha256=summary['extraction_sha256'])
    (ROOT/'results/verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ['run_count','window_counts','verified_source_files','verified_source_bytes',
                                          'total_telemetry_rows','pure_yaw_interval_count','pure_yaw_total_s','pure_yaw_max_heading_deg']},indent=2))


if __name__ == '__main__':
    summarize()
