"""Join diagnostic output to the original completed-round boundaries."""
from pathlib import Path
import argparse
import json

from analyze_remote import Capture, core


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    capture = Capture(args.run_root)
    text = capture.read('nav2.log')
    class Log:
        def read_text(self):
            return text
    _, rounds = core.parse_rounds(Log())
    if not rounds:
        raise ValueError('No completed native rounds')
    lines = text.splitlines()
    failed, coverage = [], 0
    for number, row in enumerate(rounds, 1):
        records = [json.loads(line.split('V122_PLANNING_OUTCOME ', 1)[1])
                   for line in lines[row['start_line']-1:row['end_line']]
                   if 'V122_PLANNING_OUTCOME ' in line]
        if len(records) != 1:
            raise ValueError(f'Round {number}: expected one diagnostic, got {len(records)}')
        diagnostic = records[0]
        if diagnostic['success'] != row['success']:
            raise ValueError(f'Round {number}: original result disagreement')
        if sum(diagnostic['counts'].values()) != diagnostic['rejections']:
            raise ValueError(f'Round {number}: rejection count mismatch')
        coverage += 1
        if not row['success']:
            if diagnostic['rejections'] == 0:
                raise ValueError(f'Round {number}: unclassified failure')
            failed.append({'round': number, 'solve_ms': row['wall_s']*1000, **diagnostic})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        'passed': True, 'rounds': len(rounds), 'classified': coverage,
        'failed_rounds': failed, 'source': capture.sources,
        'interpretation': 'Rejected target candidates within a successful round are not failed planning rounds. '
                          'Observation age is context, not proof of the root cause.'}, indent=2)+'\n')
    print(json.dumps({'classified': coverage, 'failed_rounds': len(failed)}))


if __name__ == '__main__':
    main()
