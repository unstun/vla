"""Audit actual gateway stop-proof publications before replacement owners."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0, str(HERE.parents[1] / 'versions/v127'))
from analyze_remote import Capture

IDENTITY = ('run_id', 'epoch', 'request_id', 'goal_id', 'route_id',
            'command_id', 'generation', 'map_epoch', 'map_revision')


def analyze(tag):
    capture = Capture(TASK / 'trials' / tag / 'runs' / tag)
    rows = capture.rows('artifacts/reactive_observations.jsonl')
    routes = {}
    for i, row in enumerate(rows):
        if row['event'] == 'pct_route':
            routes.setdefault(row['data']['generation'], (i, row))
    entries = []
    ordered = sorted(routes)
    for previous, current in zip(ordered, ordered[1:]):
        start_index, old = routes[previous]
        end_index, new = routes[current]
        relevant = rows[start_index:end_index]
        cancels = [r for r in relevant if r['event'] == 'scan_cancel' and
                   all(r['data'].get(k) == old['data'].get(k) for k in IDENTITY)]
        proofs = [r for r in relevant if r['event'] == 'measured_stop_proof' and
                  all(r['data']['admission'].get(k) == old['data'].get(k) for k in IDENTITY)]
        qualified = []
        for proof in proofs:
            admission = proof['data']['admission']
            stamp = proof['data']['stamp']['sec'] * 10**9 + proof['data']['stamp']['nanosec']
            before = [c for c in cancels if c['wall_monotonic_ns'] < proof['wall_monotonic_ns']]
            if (before and admission['hold_confirmed'] and admission['measured_stillness_confirmed']
                    and admission['status'] == 'stopped' and admission['consumer'] == 'controller'
                    and admission['message'] == 'causal_applied_stop_window'
                    and stamp >= before[0]['clock_ns']):
                qualified.append((proof, before[0], stamp))
        result = {'old_generation': previous, 'new_generation': current,
                  'matching_proofs': len(proofs), 'qualified_proofs_before_new_route': len(qualified),
                  'passed': bool(qualified)}
        if qualified:
            proof, cancel, stamp = qualified[0]
            result.update(proof_source_ns=stamp,
                          cancel_to_proof_wall_s=(proof['wall_monotonic_ns']-cancel['wall_monotonic_ns'])/1e9,
                          proof_to_new_route_wall_s=(new['wall_monotonic_ns']-proof['wall_monotonic_ns'])/1e9,
                          identity={k: old['data'][k] for k in IDENTITY})
        entries.append(result)
    return {'run': tag, 'replacement_owners': len(entries), 'entries': entries,
            'all_replacements_have_recorded_proof': all(r['passed'] for r in entries),
            'source': capture.sources}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    result = {'runs': [analyze(tag) for tag in args.run],
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Actual recorded gateway proof identity/flags/source stamp and recorder order. Original applied-window implementation and component regressions remain separate evidence; this does not reconstruct exact gateway sample polling.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'runs': len(result['runs']), 'replacements': sum(r['replacement_owners'] for r in result['runs']),
                      'all_passed': all(r['all_replacements_have_recorded_proof'] for r in result['runs'])}))


if __name__ == '__main__':
    main()
