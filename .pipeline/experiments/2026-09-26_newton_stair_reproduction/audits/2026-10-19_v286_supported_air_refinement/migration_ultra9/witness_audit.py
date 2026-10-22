"""Audit actual refused spline-start XYZ/yaw, not merely nearby measured trunks."""
from pathlib import Path
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys

ROOT = Path('/home/ubuntu/sun/vla_v286_20261020')
MIGRATION = ROOT / 'migration'
EXP = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
AUDIT = EXP / 'audits/2026-10-19_v286_supported_air_refinement'
sys.path[:0] = [str(MIGRATION), str(EXP / 'versions/v196')]
os.environ.setdefault('V286_CASE_ID', 'A04')
from analyze_remote import Capture
from analyze_case import bind_raw_oracle
import numpy as np

def main():
    bind_raw_oracle()
    from registered_point_oracle import activate, margin
    activate()
    cases = json.loads((MIGRATION / 'physical_manifest01.json').read_text())['physical_cases']
    pattern = re.compile(r'initial_spline_collision pos=\(([^)]+)\) yaw=([+0-9.eE-]+) body=\(([^)]+)\).* now=([+0-9.eE-]+)')
    all_rows = []
    for cid in cases:
        caseout = AUDIT / 'physical' / cid
        result = caseout / 'results/initial_collision_witness_audit.json'
        assert not result.exists()
        raw = ROOT / 'physical_runs' / f'v286_{cid}_attempt01' / 'runs' / f'v286_{cid}_attempt01'
        lines = Capture(raw).read('nav2.log').splitlines()
        witnesses = []
        for index, line in enumerate(lines):
            match = pattern.search(line)
            if not match:
                continue
            position = list(map(float, match.group(1).split(',')))
            body = list(map(float, match.group(3).split(',')))
            following = []
            for other in lines[index + 1:index + 17]:
                if 'initial_spline_collision' in other:
                    break
                if 'near_sensor_verdict' in other or 'reactive_collision_blocked' in other:
                    following.append(other)
            diagnostics = [dict(verdict=int(a), voxel=int(b), inflation=int(c)) for text in following
                for a, b, c in re.findall(r'near_sensor_verdict verdict=(\d+) voxel=(\d+).* inflation=(\d+)', text)]
            witnesses.append(dict(position=position, yaw=float(match.group(2)), time_s=float(match.group(4)),
                measured_body=body, distance_to_measured_body_m=math.dist(position, body),
                one_based_log_line=index + 1, logged_diagnostics=diagnostics, diagnostic_lines=following))
        if witnesses:
            source = caseout / 'initial_collision_queries.txt'
            with source.open('x') as stream:
                for row in witnesses:
                    stream.write(' '.join(map(str, [row['time_s'], *row['position'], row['yaw']])) + '\n')
            output = caseout / 'results/initial_collision_native_margins.csv'
            shell = 'source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && source /work/fixtures/probe271.env && '
            shell += '/audit/margin_build/body_margin /work/fixtures/building/environment225.env 10040917858432847476 /work/fixtures/building/native.support 15212154834549674106 /audit/initial_collision_queries.txt /audit/results/initial_collision_native_margins.csv $RAW_FIELD $RAW_FNV'
            command = ['docker', 'run', '--rm', '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}',
                '--cpus=2', '--memory=3g', '-v', str(ROOT / 'native') + ':/work:ro',
                '-v', str(caseout) + ':/audit:rw', '--entrypoint', '/bin/bash',
                'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343', '-c', shell]
            subprocess.run(command, check=True, stdout=subprocess.DEVNULL)
            native = list(csv.DictReader(output.open()))
            assert len(native) == len(witnesses)
            for row, checked in zip(witnesses, native):
                raw_margin, raw_witness = margin(np.array(row['position']), row['yaw'])
                row.update(static_support_verdict=int(checked['static_support_verdict']),
                    source_solid_margin_m=float(checked['native_source_solid_margin_m']), raw_point_margin_m=raw_margin)
                row['static_source_clear'] = row['static_support_verdict'] == 0 and min(row['source_solid_margin_m'], raw_margin) >= 0
                row['static_source_clear_but_observed_hit'] = row['static_source_clear'] and any(
                    d['verdict'] == 7 and d['voxel'] == 2 and d['inflation'] == 1 for d in row['logged_diagnostics'])
        report = dict(case_id=cid, physics_steps=0, actual_initial_collision_queries=len(witnesses),
            exact_query_static_source_clear=sum(r.get('static_source_clear', False) for r in witnesses),
            exact_query_static_source_clear_with_logged_observed_hit=sum(r.get('static_source_clear_but_observed_hit', False) for r in witnesses),
            starts_farther_than_015m_from_logged_measured_body=sum(r['distance_to_measured_body_m'] > .15 for r in witnesses),
            rows=witnesses, source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            claim='Exact refused spline-start XYZ/yaw tested against independent static support/source/raw geometry. An observed-hit conflict identifies a static/live disagreement, not its sensor/registration root cause. Recorded body clearance alone is insufficient.')
        result.write_text(json.dumps(report, indent=2) + '\n')
        all_rows.append({k: v for k, v in report.items() if k != 'rows'})
        print(json.dumps(all_rows[-1]), flush=True)
    (ROOT / 'evidence/initial_collision_witnesses.json').write_text(json.dumps(dict(physics_steps=0, cases=all_rows), indent=2) + '\n')

if __name__ == '__main__':
    main()
