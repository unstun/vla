"""Read actual native callback/recovery sequences; do not infer causes from labels."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0, str(HERE.parents[1] / 'versions/v127'))
from analyze_remote import Capture


def analyze(tag):
    capture = Capture(TASK / 'trials' / tag / 'runs' / tag)
    lines = capture.read('nav2.log').splitlines()
    observations = capture.rows('artifacts/reactive_observations.jsonl')
    unique = set()
    handoffs = []
    for row in observations:
        event, data = row['event'], row['data']
        if event not in ('pct_route', 'scan_admission', 'scan_cancel'):
            continue
        key = (event, data.get('generation'), data.get('consumer'), data.get('status'),
               data.get('message'), data.get('reason'))
        if key in unique:
            continue
        unique.add(key)
        handoffs.append({'event': event, 'clock_ns': row['clock_ns'],
                         'received_monotonic_ns': row['wall_monotonic_ns'],
                         'generation': data.get('generation'), 'consumer': data.get('consumer'),
                         'status': data.get('status'), 'message': data.get('message', data.get('reason'))})
    stops = []
    for i, line in enumerate(lines):
        if 'SCAN output revoked reason=' not in line:
            continue
        reason = line.split('SCAN output revoked reason=', 1)[1].split()[0]
        start = re.search(r'\[(\d+\.\d+)\]', line)
        if not start:
            continue
        stop = {'line': i + 1, 'reason': reason, 'log_wall_s': float(start[1]),
                'follow_path_abort_after_s': None}
        for j in range(i + 1, len(lines)):
            if 'Received a goal, begin computing control effort.' in lines[j]:
                break
            if '[follow_path] [ActionServer] Aborting handle.' in lines[j]:
                stamp = re.search(r'\[(\d+\.\d+)\]', lines[j])
                if stamp:
                    stop.update(follow_path_abort_after_s=float(stamp[1]) - float(start[1]), abort_line=j + 1)
                break
        stops.append(stop)
    errors = [{'line': i + 1, 'message': line} for i, line in enumerate(lines)
              if ('[ERROR]' in line and any(x in line for x in ('[controller_server]:', '[nav2_internal.bt_navigator]:')))
              or 'Target is occupied and no collision-free point' in line]
    return {'run': tag, 'handoffs': handoffs, 'stops': stops, 'errors': errors,
            'raw_capture_sources': capture.sources}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    report = {'runs': [analyze(tag) for tag in args.run],
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'time_scope': 'Abort delays use same controller process log wall timestamps; recorder ROS times are separate.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'runs': len(report['runs']), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
