"""Read original v50 logs; identical seeds do not imply identical map/clock state."""
from pathlib import Path
import collections
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]

def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()

def analyze(run):
    log = BASE / 'runs' / run / 'scan.log'
    rounds = json.loads((BASE / 'versions/v50/analysis' / (run + '_rounds.json')).read_text())
    lines = log.read_text().splitlines()
    results = []
    for row in rounds:
        seen = {}
        applied = 0
        fixed = False
        seeds = []
        warm_reasons = collections.Counter()
        for lineno in range(row['start_line'], row['end_line'] + 1):
            line = lines[lineno - 1]
            match = re.search(r'input_refresh site=(\w+) sensor_poses=(\d+) clouds=(\d+) body_poses=(\d+)', line)
            if match:
                applied += sum(map(int, match.groups()[1:]))
            if 'fixed_height_recovery_attempt' in line:
                fixed = True
            if 'fixed_height_recovery_result' in line:
                fixed = False
            match = re.search(r'V48_WARM_SEED selected=0 reason=(\w+)', line)
            if match:
                warm_reasons[match[1]] += 1
            if 'spline_seed_capture ' not in line:
                continue
            seed = json.loads(line.split('spline_seed_capture ', 1)[1])
            identity = hashlib.sha256(json.dumps(seed, sort_keys=True).encode()).hexdigest()
            key = (identity, fixed)
            previous = seen.get(key)
            seeds.append({'line': lineno, 'seed_sha256': identity, 'fixed_height': fixed,
                          'repeat_of_line': previous['line'] if previous else None,
                          'intervening_logged_input_messages': applied - previous['applied'] if previous else None})
            seen[key] = {'line': lineno, 'applied': applied}
        segment = lines[row['start_line']-1:row['end_line']]
        results.append({'start_line': row['start_line'], 'end_line': row['end_line'],
                        'simulation_s': row['ros_s'], 'wall_ms': row['wall_s'] * 1000,
                        'success': row['success'], 'seeds': seeds,
                        'input_messages_applied': applied, 'warm_rejections': dict(warm_reasons),
                        'blocked_first_controls': sum('First three control points' in x for x in segment),
                        'no_rebound_constraints': sum('rebound_no_valid_new_constraints' in x for x in segment)})
    repeats = [s for r in results for s in r['seeds'] if s['repeat_of_line']]
    return {'run': run, 'scan_log_sha256': sha(log), 'round_count': len(results),
            'seed_count': sum(len(r['seeds']) for r in results),
            'same_seed_and_height_mode_repeats': len(repeats),
            'repeats_with_intervening_inputs': sum(s['intervening_logged_input_messages'] > 0 for s in repeats),
            'repeats_without_logged_inputs': sum(s['intervening_logged_input_messages'] == 0 for s in repeats),
            'warm_rejections': dict(sum((collections.Counter(r['warm_rejections']) for r in results), collections.Counter())),
            'worst_rounds': sorted(results, key=lambda x: x['wall_ms'], reverse=True)[:5]}

if __name__ == '__main__':
    result = {'scope': 'Read-only original-log audit; equal seeds are not a cache-validity proof, and clocks can advance without input messages.',
              'runs': [analyze(r) for r in ('v50_realtime_trial01', 'v50_realtime_trial02')]}
    (HERE / 'retry_summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps([{k: v for k, v in r.items() if k != 'worst_rounds'} for r in result['runs']], indent=2))
