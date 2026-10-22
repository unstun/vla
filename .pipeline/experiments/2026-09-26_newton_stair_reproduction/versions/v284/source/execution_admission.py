"""Keep benchmark acceptance separate from explicitly authorized timing review."""
from pathlib import Path
import hashlib,json,sys
HERE=Path(__file__).resolve().parent
ROOT=Path('/home/sun/vla_exec/static_continuity_v284')
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
    decision=json.loads((HERE/'results/user_timing_decision.json').read_text())
    assert review['user_decision_sha256']==sha(HERE/'results/user_timing_decision.json')
    assert decision['user_reply']=='继续十条，耗时记未达标'
    assert decision['global_median_s']==current['global_median_s']
    assert decision['timing_acceptance_passed']==current['timing_acceptance_passed']
    assert decision['ten_single_attempts_authorized_if_geometry_passes']
    assert not decision['native_changes_authorized_after_freeze']
    assert decision['hard_radius_m']==.35 and decision['scanner_period_s']==.1
    assert review['physical_execution_authorized'] and review['authorized_attempts_per_case']==1
    return review

if __name__=='__main__':
    if '--record-authorized-timing-exception' in sys.argv:
        p=HERE/'execution_review.json';assert not p.exists()
        evaluated=evaluate();assert evaluated['non_timing_passed'],evaluated
        decision=HERE/'results/user_timing_decision.json'
        review=dict(offline_evaluation=evaluated,user_decision_sha256=sha(decision),
            physical_execution_authorized=True,authorized_attempts_per_case=1,
            scope='User authorized ten single attempts with timing failure retained. No geometry, radius, period, or benchmark acceptance waiver.')
        p.write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(verify(),indent=2))
