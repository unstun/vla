#!/usr/bin/env python3
"""Audit the native original/candidate comparison from returned raw artifacts."""

import hashlib
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def inspect(run_id):
    run = ROOT / 'runs' / run_id
    artifacts = run / 'returned_artifacts'
    expected = load(artifacts / 'artifact_hashes.json')
    actual = {str(p.relative_to(artifacts)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in artifacts.rglob('*') if p.is_file() and p.name != 'artifact_hashes.json'}
    rows = []
    for case in load(artifacts / 'cases_result.json'):
        path = artifacts / (case['id'] + '_' + str(case['repeat']) + '.log')
        text = path.read_text(errors='replace')
        stages = {}
        for line in text.splitlines():
            if '[DEBUG-scan-0916]' not in line:
                continue
            fields = dict(re.findall(r'([a-z_]+)=([^\s]+)', line))
            stage = fields.pop('stage')
            stages[stage] = {key: float(value) for key, value in fields.items()}
        rows.append({**case, 'native_success': 'REBOUND_REPLAN_RESULT success=true' in text,
                     'stages': stages, 'actual_limits_recorded':
                     'manager.max_acc=0.500000000' in text and 'optimization.acc_tolerance=1.000000000' in text})
    result = load(artifacts / 'result.json')
    return {'run_id': run_id, 'returned_hashes_match': expected == actual,
            'artifact_count': len(actual), 'source_gate': result['source_gate'],
            'scan_source_unchanged': result['scan_source_unchanged'],
            'package_source_unchanged': result['package_source_unchanged'],
            'owned_container_absent': result['owned_container_absent'],
            'rows': rows}


def main():
    original = inspect('native_original_20260916T180500Z')
    candidate = inspect('native_true_end_20260916T180700Z')
    before = {tuple(r[k] for k in ('id', 'repeat')): r for r in original['rows']}
    after = {tuple(r[k] for k in ('id', 'repeat')): r for r in candidate['rows']}
    checks = {
        'same_cases_and_commands': before.keys() == after.keys() and all(before[k]['command'] == after[k]['command'] for k in before),
        'original_failure_reproduced_three_times': sum(r['id'] == 'failed_run_resume' and r['returncode'] == 2 and not r['native_success'] for r in before.values()) == 3,
        'original_other_cases_pass': all(r['returncode'] == 0 and r['native_success'] for r in before.values() if r['id'] != 'failed_run_resume'),
        'candidate_all_twelve_pass': len(after) == 12 and all(r['returncode'] == 0 and r['native_success'] for r in after.values()),
        'limits_unchanged': all(r['actual_limits_recorded'] for r in [*before.values(), *after.values()]),
        'candidate_sampled_max_acc_within_original_gate': all(r['stages']['refined']['max_acc'] <= 1.5 for r in after.values()),
        'source_and_artifact_integrity': all(run['returned_hashes_match'] and run['source_gate']['all_match'] and run['scan_source_unchanged'] and run['package_source_unchanged'] for run in (original, candidate)),
        'containers_released': original['owned_container_absent'] and candidate['owned_container_absent'],
    }
    a = (ROOT / 'sources/original_instrumented/planner_manager.cpp').read_text()
    b = (ROOT / 'sources/true_end_acceleration/planner_manager.cpp').read_text()
    checks['single_behavior_line_changed'] = a.replace('start_end_derivatives.push_back(gl_traj.evaluateAcc(t));', 'start_end_derivatives.push_back(gl_traj.evaluateAcc(time));', 1) == b
    report = {'passed': all(checks.values()), 'checks': checks, 'original': original, 'candidate': candidate,
              'claim': 'Endpoint-acceleration construction causes this native candidate rejection. Diagnostic candidate verified; no patched Isaac navigation run or production source adoption.'}
    (ROOT / 'comparison.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'passed': report['passed'], 'checks': checks}, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
