"""Separate logged stop labels from measured causes without changing runtime."""
from pathlib import Path
import collections
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')
OUTPUT = TASK / 'results/step3_repeats'
sys.path.insert(0, str(HERE.parents[1] / 'versions/v127'))
from analyze_remote import Capture


def main():
    summary = json.loads((OUTPUT / 'analysis/summary.json').read_text())
    rows = []
    for trial in summary['rows']:
        tag = trial['run']
        capture = Capture(TASK / 'trials' / tag / 'runs' / tag)
        lines = capture.read('nav2.log').splitlines()
        compact = TASK / 'results/step3_v127/comparison' / tag
        maximum = json.loads((compact / 'max_round.json').read_text())
        window = lines[maximum['start_line'] - 1:maximum['end_line']]
        profiles = []
        outcomes = []
        for line in window:
            for marker, values in [('V50_PROFILE ', profiles), ('V122_PLANNING_OUTCOME ', outcomes)]:
                if marker in line:
                    values.append(json.JSONDecoder().raw_decode(line.split(marker, 1)[1])[0])
        sums = collections.defaultdict(float)
        for profile in profiles:
            for name, value in profile.items():
                sums[name] += value['wall_ms']
        # Existing profiler fields nest; never add all categories as a total.
        events = []
        for event in trial['safety_rejections']:
            fresh = 0 <= event['observation_age'] <= .25 and 0 <= event['proof_age'] <= .1
            events.append({**event, 'fresh_by_recorded_ages': fresh,
                           'classification': 'negative_native_verdict_with_fresh_ages' if fresh and not event['clear']
                           else 'age_limit_exceeded' if not fresh else 'other'})
        important = [(i + 1, line) for i, line in enumerate(lines)
                     if ('[ERROR]' in line and ('[controller_server]:' in line or '[nav2_internal.bt_navigator]:' in line))
                     or '[follow_path] [ActionServer] Aborting handle.' in line
                     or 'SCAN output revoked reason=' in line
                     or 'Exiting EMERGENCY_STOP;' in line]
        metrics = json.loads((compact / 'metrics.json').read_text())
        rows.append({'run': tag, 'variant': trial['variant'], 'outcome_class': trial['outcome_class'],
                     'safety_events': events, 'ordered_events': important,
                     'maximum_round': maximum, 'maximum_round_profile_wall_ms': dict(sums),
                     'maximum_round_outcomes': outcomes,
                     'path_search_pool_errors': sum('Ran out of pool, index=' in line for line in lines),
                     'optimizer_astar_failures': sum('A-star failed; aborting optimization' in line for line in lines),
                     'backend_gate': metrics['backend_gate'], 'stop_flow': metrics['stop_flow'],
                     'source': capture.sources})
    report = {'rows': rows,
              'safety_event_counts': dict(collections.Counter(e['classification'] for r in rows for e in r['safety_events'])),
              'limits': ['The stale error label also covers negative collision/support verdicts.',
                         'Fresh ages do not identify which geometric/support predicate rejected.',
                         'Recorded planner profile fields overlap; categories are not additive.',
                         'Different live trajectories do not isolate a code timing effect.'],
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (OUTPUT / 'diagnosis.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'safety_event_counts': report['safety_event_counts'],
                      'maxima': [{'run': r['run'], 'ms': r['maximum_round']['wall_s'] * 1000,
                                  'success': r['maximum_round']['success'],
                                  'attempts': r['maximum_round']['rebound_attempts'],
                                  'profile_ms': r['maximum_round_profile_wall_ms'],
                                  'stop_flow': r['stop_flow']} for r in rows]}, indent=2))


if __name__ == '__main__':
    main()
