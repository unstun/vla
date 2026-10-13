"""Trace actual footprint versus controller-commanded spline on closed captures.

This checks only the immutable negative support mask, not live-map occupancy.
Closest spline samples describe geometric tracking error, not execution phase.
"""
from pathlib import Path
import bisect
import hashlib
import json
import math
import subprocess
import sys

import numpy as np
from scipy.interpolate import BSpline
from scipy.spatial import cKDTree

BASE = Path(__file__).resolve().parents[2]
TASK = Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0, str(BASE / 'versions/v175'))
from analyze_remote import Capture


def yaw_wxyz(q):
    w, x, y, z = q
    return math.atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z))


def identity(data):
    return data['generation'], data['traj_id']


def main():
    out = TASK / 'results/v175_gap_entry'
    out.mkdir(exist_ok=False)
    source = Path(__file__).with_name('gap_query.cpp')
    binary = out / 'gap_query'
    subprocess.run(['g++', '-std=c++14', '-O2', '-I',
                    str(TASK / 'recovery_v175/src/plan_env/include'),
                    str(source), '-o', str(binary)], check=True)
    mask = TASK / 'support_coverage_v134/partial.txt'
    assert hashlib.sha256(mask.read_bytes()).hexdigest() == '219d7982eca6c7af94545158ec97fb3b0186ff0f2166f8697d53c0b0726c56d8'
    for attempt in range(1, 6):
        tag = f'v175_full_candidate_attempt{attempt:02d}'
        capture = Capture(TASK / 'trials' / tag / 'runs' / tag)
        states = capture.rows('telemetry.jsonl')
        events = capture.rows('artifacts/reactive_observations.jsonl')
        commands = sorted((r for r in events if r['event'] == 'raw_command'),
                          key=lambda r: r['data']['stamp']['sec'] + r['data']['stamp']['nanosec']/1e9)
        times = [r['data']['stamp']['sec'] + r['data']['stamp']['nanosec']/1e9 for r in commands]
        splines = {}
        for row in events:
            data = row['data']
            if row['event'] != 'bspline' or data.get('emergency_stop'):
                continue
            points = np.array([[p[k] for k in 'xyz'] for p in data['pos_pts']])
            knots = np.array(data['knots']); degree = data['order']
            spline = BSpline(knots, points, degree, extrapolate=False)
            ts = np.linspace(knots[degree], knots[-degree-1], 601)
            sampled = spline(ts)
            ahead = spline(np.minimum(ts + .8, ts[-1])) - sampled
            velocity = spline.derivative()(ts)
            short = (ahead[:, :2]**2).sum(axis=1) < 1e-4
            ahead[short] = velocity[short]
            headings = np.arctan2(ahead[:, 1], ahead[:, 0])
            degenerate = (ahead[:, :2]**2).sum(axis=1) < 1e-4
            splines[identity(data)] = (data, sampled, ts, headings, degenerate, cKDTree(sampled[:, :2]))
        records = []
        queries = []
        for state in states:
            t = state['physics_time_s']; body = state['body_sensor']
            xyz = body['position']; yaw = yaw_wxyz(body['quaternion'])
            record = {'t': t, 'xyz': xyz, 'yaw': yaw, 'command': state['effective_command'],
                      'velocity_world': body['linear_world'], 'phase': state['stance_mode']}
            queries.append([*xyz, yaw]); record['actual_query'] = len(queries)-1
            ci = bisect.bisect_right(times, t)-1
            if ci >= 0:
                command = commands[ci]['data']; record['raw_command_age_s'] = t-times[ci]
                key = identity(command); record['curve_id'] = list(key)
                if key in splines:
                    data, sampled, ts, headings, degenerate, tree = splines[key]
                    distance, index = tree.query(xyz[:2]); target = sampled[index]
                    expected = yaw if degenerate[index] else float(headings[index])
                    record.update(closest_spline_xyz=target.tolist(), closest_spline_phase_s=float(ts[index]),
                                  xy_error_m=float(distance), expected_yaw=expected,
                                  yaw_error_rad=math.atan2(math.sin(yaw-expected), math.cos(yaw-expected)),
                                  reference_heading_degenerate=bool(degenerate[index]),
                                  reverse=bool(data.get('reverse_motion')))
                    for name, p, heading in [('reference', target, expected),
                                             ('actual_at_reference_yaw', xyz, expected),
                                             ('reference_at_actual_yaw', target, yaw)]:
                        queries.append([*p, heading]); record[name+'_query'] = len(queries)-1
            records.append(record)
        stdin = ''.join(' '.join(format(x, '.17g') for x in q)+'\n' for q in queries)
        result = subprocess.run([str(binary), str(mask)], input=stdin, text=True, capture_output=True, check=True)
        flags = [list(map(int, line.split())) for line in result.stdout.splitlines()]
        assert len(flags) == len(queries)
        for record in records:
            for key in list(record):
                if key.endswith('_query'):
                    record[key[:-6]+'_gap'] = flags[record.pop(key)]
        episodes = []; start = None
        for index, row in enumerate(records):
            blocked = any(row['actual_gap'])
            if blocked and start is None: start = index
            if start is not None and (not blocked or index == len(records)-1):
                last = index if blocked else index-1
                episodes.append({'start_s': records[start]['t'], 'end_s': records[last]['t'],
                                 'duration_s': records[last]['t']-records[start]['t'],
                                 'entry': records[start], 'before': records[max(0,start-25):start:5],
                                 'after': records[start:min(last+1,start+51):5]})
                start = None
        report = {'run': tag, 'episodes': episodes,
                  'blocked_states': sum(any(r['actual_gap']) for r in records), 'states': len(records),
                  'source': capture.sources, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  'scope': __doc__}
        (out / f'{tag}.json').write_text(json.dumps(report, indent=2)+'\n')
        (out / f'{tag}.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in records))
        print(json.dumps({'run': tag, 'blocked_states': report['blocked_states'],
                          'episodes': [{'start': e['start_s'], 'end': e['end_s'],
                                        'entry': e['entry']} for e in episodes]}), flush=True)


if __name__ == '__main__':
    main()
