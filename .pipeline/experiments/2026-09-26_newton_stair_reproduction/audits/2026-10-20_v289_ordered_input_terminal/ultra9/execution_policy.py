"""Require the complete strict offline gate before authorized physical execution."""
from pathlib import Path
import hashlib,json,sys
HERE=Path('/home/ubuntu/sun/vla_v289_20261020/repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v289')
ROOT=Path('/home/ubuntu/sun/vla_v289_20261020')
BENCH=ROOT/'benchmark'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def evaluate():
    native=json.loads((HERE/'native_manifest.json').read_text())
    gate=json.loads((BENCH/'offline_gate.json').read_text())
    matrix=json.loads((BENCH/'matrix_summary.json').read_text())
    complete=json.loads((BENCH/'complete.json').read_text())
    ledger=json.loads((BENCH/'native_ledger.json').read_text())
    audits=json.loads((BENCH/'audit_ledger.json').read_text())
    calls=matrix['calls']; selected=native['physical_cases']
    checks=dict(
        fixed_contract=native['hard_radius_m']==.35 and native['sensor_period_s']==.1,
        complete=complete['all_cases_finished'] and complete['calls']==53,
        native_bound=complete['native_manifest_sha256']==sha(HERE/'native_manifest.json'),
        all_native_calls_finished=len(ledger)==53 and len({r['case_id'] for r in ledger})==53 and all(r['state']=='finished' for r in ledger),
        all_audits_finished=len(audits)==53 and all(r['exit_code']==0 for r in audits),
        complete_matrix=len(calls)==53 and matrix['gate']==gate,
        legal_rate=gate['positive_total']==50 and gate['positive_passed']>=48,
        illegal_controls=gate['illegal_controls']==3 and gate['illegal_correct_rejections']==3,
        source_route_safe=gate['zero_admitted_negative_raw_margin'],
        source_local_safe=gate['zero_published_negative_raw_margin'],
        first_gpmp_rate=gate['first_gpmp_rate_admitted']>=.9,
        selected_ten_pass=len(selected)==10 and all(any(r['case_id']==cid and r['end_to_end_pass'] for r in calls) for cid in selected),
    )
    return dict(checks=checks,non_timing_passed=all(checks.values()),
        benchmark_acceptance_passed=gate['passed'],global_median_s=gate['global_median_s'],
        timing_acceptance_passed=gate['global_median_s']<=1.5,
        hard_radius_m=.35,scanner_period_s=.1,
        bindings={name:sha(BENCH/name) for name in ['offline_gate.json','matrix_summary.json','complete.json','native_ledger.json','audit_ledger.json','selection.json']},
        native_manifest_sha256=sha(HERE/'native_manifest.json'))

def verify():
    current=evaluate();review=json.loads((HERE/'execution_review.json').read_text())
    assert review['offline_evaluation']==current,'Offline evidence or admission review changed'
    assert current['non_timing_passed'],current['checks']
    assert current['benchmark_acceptance_passed'] and current['timing_acceptance_passed']
    assert review['physical_execution_authorized'] and review['authorized_attempts_per_case']==1
    return review

if __name__=='__main__':
    if '--record' in sys.argv:
        p=HERE/'execution_review.json';assert not p.exists()
        evaluated=evaluate();assert evaluated['non_timing_passed'] and evaluated['benchmark_acceptance_passed'] and evaluated['timing_acceptance_passed'],evaluated
        review=dict(offline_evaluation=evaluated,physical_execution_authorized=True,authorized_attempts_per_case=1,
            scope='User requested v289: strict complete offline gate followed by ten single physical attempts.')
        p.write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(verify(),indent=2))
