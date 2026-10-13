"""Inspect preserved v147 outcomes and direct failure signals without replay."""
from collections import Counter
from pathlib import Path
import json
import re
import sys
import time

from run_repeats import BASE, TASK, sha, save

sys.path.insert(0, str(BASE / 'versions/v147'))
from analyze_remote import Capture

OUTPUT = TASK / 'results/full_route_repeat_triage_20261012'
ATTEMPTS = (2, 3, 4, 8, 9)
MARKERS = ('Failed to make progress', 'SCAN output revoked', 'Ran out of pool',
           'Unable to handle the initial or end point', 'Target is occupied',
           'First three control points are in obstacles', 'The robot is inside an obstacle',
           'rebound_no_valid_new_constraints', 'initial_spline_collision',
           'reactive_stair_seed_search_failed', 'fixed_height_recovery_result',
           'remaining_spline_invalid', 'Obstacle discovered; emergency stop',
           'native_replan_exhausted')


def stamp(line):
    match = re.search(r'\[(\d{10}\.\d+)\]', line)
    return float(match.group(1)) if match else None


def main():
    assert Path(__file__).resolve().is_relative_to(TASK / 'repo')
    OUTPUT.mkdir(exist_ok=False)
    receipt_path = TASK / 'results/recovery_v147/candidate_receipt.json'
    receipt = json.loads(receipt_path.read_text())
    source_snippets = {}
    for relative, terms in {
        'path_searching/include/path_searching/dyn_a_star.h': ('Ran out of pool',),
        'plan_manage/src/planner_manager.cpp': ('initGridMap(grid_map_',),
        'scan_nav2_controller/src/controller.cpp': ('scan_safety_rejected', 'scan_trajectory_missing'),
    }.items():
        path = TASK / 'recovery_v147/src' / relative
        digest = sha(path)
        assert digest == receipt['files']['/task/' + str(path.relative_to(TASK))]
        lines = path.read_text().splitlines()
        source_snippets[relative] = {'sha256': digest, 'sections': [
            {'line': i + 1, 'text': '\n'.join(lines[max(0, i - 3):i + 4])}
            for i, line in enumerate(lines) if any(term in line for term in terms)]}
    rows = []
    for attempt in ATTEMPTS:
        tag = f'v147_full_candidate_attempt{attempt:02d}'
        root = TASK / 'trials' / tag / 'runs' / tag
        analysis = TASK / 'results/recording_v147' / tag
        capture = Capture(root)
        log = capture.read('nav2.log')
        lines = log.splitlines()
        metrics = json.loads((analysis / 'metrics.json').read_text())
        original = json.loads((analysis / 'outcome.json').read_text())
        assert original['execution_exit'] == 0 and original['retention'] == 'completed'
        assert metrics['state_copyback_verified']
        assert capture.sources['nav2.log'] == metrics['source']['nav2.log']
        revocations = []
        for i, line in enumerate(lines):
            match = re.search(r'SCAN output revoked reason=(\S+) trajectory=(\d+)', line)
            if match:
                revocations.append({'line': i + 1, 'unix_s': stamp(line),
                                    'reason': match.group(1), 'trajectory': int(match.group(2))})
        aborts = [i for i, line in enumerate(lines)
                  if '[follow_path] [ActionServer] Aborting handle.' in line]
        windows = []
        for i in aborts:
            end = stamp(lines[i])
            assert end is not None
            selected = []
            for j in range(i - 1, -1, -1):
                when = stamp(lines[j])
                if when is not None and when < end - 0.5:
                    break
                if any(marker in lines[j] for marker in MARKERS) or '[ERROR]' in lines[j]:
                    selected.append({'line': j + 1, 'text': lines[j][:1200],
                                     'truncated': len(lines[j]) > 1200})
            windows.append({'abort_line': i + 1, 'unix_s': end,
                            'matching_lines': len(selected),
                            'last_signals': list(reversed(selected[:20]))})
        row = {'run': tag, 'terminal': metrics['terminal']['backend_terminal_status'],
               'path_m': metrics['measured_path_m'], 'last_body_xyz_m': metrics['final_body_xyz_m'],
               'longest_pause_s': metrics['longest_pause_sim_s'],
               'revocations': revocations, 'revoke_counts': dict(Counter(r['reason'] for r in revocations)),
               'follow_path_aborts': len(aborts),
               'marker_counts': {marker: log.count(marker) for marker in MARKERS},
               'final_abort_window': windows[-1] if windows else None,
               'nav2_log': capture.sources['nav2.log'],
               'outcome_sha256': sha(analysis / 'outcome.json'),
               'metrics_sha256': sha(analysis / 'metrics.json')}
        save(OUTPUT / (tag + '.json'), {'summary': row, 'all_abort_windows': windows})
        rows.append(row)
        print(json.dumps({'run': tag, 'terminal': row['terminal'], 'revocations': row['revoke_counts']}), flush=True)
    result = {'stage': 'experiment + analysis', 'host': 'gpu5070ti', 'version': 'v147',
              'rows': rows, 'source_snippets': source_snippets,
              'receipt_sha256': sha(receipt_path), 'analyzer_sha256': sha(Path(__file__)),
              'created_unix_s': time.time(),
              'claim': 'Recorded failure triggers and verified source meanings only. No replay-based root cause, repair, simulator run or changed navigation threshold.'}
    save(OUTPUT / 'RESULT.json', result)
    files = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)}
             for p in sorted(OUTPUT.iterdir()) if p.is_file()}
    assert sum(r['bytes'] for r in files.values()) < 1024**2
    save(OUTPUT / 'return_manifest.json', {'root': str(OUTPUT), 'files': files})


if __name__ == '__main__':
    main()
