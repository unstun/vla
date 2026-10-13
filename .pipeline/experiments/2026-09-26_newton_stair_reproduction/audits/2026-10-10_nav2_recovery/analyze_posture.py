"""Separate measured posture failure from route/stop handshake failures."""
from pathlib import Path
import hashlib
import json
import math
import sys

HERE = Path(__file__).resolve().parent
TASK = Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0, str(HERE.parents[1] / 'versions/v127'))
from analyze_remote import Capture


def main():
    output = TASK / 'results/recovery_v131_repeats/analysis/posture.json'
    assert not output.exists()
    selected = {'v131_candidate_attempt05': [38.0,38.5,38.8,38.95,38.97,39.0,39.09],
                'v131_candidate_attempt06': [32.,33.,35.,37.5,42.,54.,62.]}
    cases = []
    for tag, times in selected.items():
        capture = Capture(TASK / 'trials' / tag / 'runs' / tag)
        rows = capture.rows('telemetry.jsonl')
        points = []
        for time_s in times:
            r = min(rows, key=lambda r: abs(r['physics_time_s']-time_s))
            body = r['body_sensor']; w,x,y,z = body['quaternion']
            tilt = math.degrees(math.acos(max(-1., min(1., 1-2*(x*x+y*y)))))
            points.append({'physics_time_s': r['physics_time_s'], 'position': body['position'],
                           'body_tilt_deg': tilt, 'stance_mode': r['stance_mode'],
                           'effective_command': r['effective_command'], 'command_reason': r['command_reason']})
        logs = capture.read('nav2.log').splitlines()
        notes = [line for line in logs if 'SCAN evidence rejected now=' in line or 'SCAN output revoked reason=' in line]
        collisions = [line for line in logs if 'initial_spline_collision' in line]
        cases.append({'run': tag, 'points': points, 'controller_stops': notes,
                      'initial_collision_count': len(collisions), 'collision_examples': collisions[:2]+collisions[-2:],
                      'source': capture.sources})
    report = {'cases': cases, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'limits': ['Measured tilt precedes the first moving-owner stop in the fallen trial; this is chronology, not proof of the originating dynamics cause.',
                         'The nonfallen trial keeps tilted STAND_SETTLING posture while native cold-trajectory starts are rejected; the exact geometric predicate is not identified here.',
                         'No policy, controller gains, footprint or acceptance thresholds were changed.']}
    output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'runs': len(cases), 'output': str(output)}))


if __name__ == '__main__':
    main()
