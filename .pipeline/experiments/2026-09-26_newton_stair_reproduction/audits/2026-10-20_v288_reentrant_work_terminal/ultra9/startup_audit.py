"""Audit original factory video-state poses, separately from later10Hz sensors."""
from pathlib import Path
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import numpy as np

ROOT = Path('/home/ubuntu/sun/vla_v288_20261020')
EXP = ROOT / 'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction'
AUDIT = EXP / 'audits/2026-10-20_v288_reentrant_work_terminal'
os.environ.setdefault('V288_CASE_ID', 'A04')
sys.path[:0] = [str(ROOT / 'migration'), str(EXP / 'versions/v196')]
from analyze_remote import Capture
from analyze_case import bind_raw_oracle

def main():
    bind_raw_oracle()
    from registered_point_oracle import activate, margin
    activate()
    cohort = json.loads((ROOT / 'cohort/cases_manifest.json').read_text())
    output = ROOT / 'startup_return'
    output.mkdir(exist_ok=False)
    reports = []
    for cid in cohort['physical_cases']:
        folder = AUDIT / 'physical' / cid
        raw = ROOT / 'physical_runs' / f'v288_{cid}_attempt01' / 'runs' / f'v288_{cid}_attempt01'
        capture = Capture(raw)
        rows = capture.json('factory_video_states.json')
        assert rows and rows[0]['physics_time_s'] == 0 and rows[0]['physics_steps'] == 0
        query = folder / 'startup_poses.txt'
        headings = []
        with query.open('x') as stream:
            for row in rows:
                x, y, z, w = row['joint_q'][3:7]
                yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
                headings.append(yaw)
                stream.write(' '.join(map(str, [row['physics_time_s'], *row['joint_q'][:3], yaw])) + '\n')
        shell = 'source /opt/ros/foxy/setup.bash && source /work/install/setup.bash && source /work/fixtures/probe271.env && '
        shell += '/audit/margin_build/body_margin /work/fixtures/building/environment225.env 10040917858432847476 /work/fixtures/building/native.support 15212154834549674106 /audit/startup_poses.txt /audit/results/startup_native_margins.csv $RAW_FIELD $RAW_FNV && '
        shell += '/audit/margin_build/edge_diagnostic /audit/startup_poses.txt > /audit/results/startup_support_margins.jsonl'
        subprocess.run(['docker', 'run', '--rm', '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}',
            '--cpus=2', '--memory=3g', '-v', str(ROOT / 'native') + ':/work:ro', '-v', str(folder) + ':/audit:rw',
            '--entrypoint', '/bin/bash', 'sha256:ec85ad5a21dc2b3441523571d2dc583f22bf08121390081ca780f78e15332343', '-c', shell],
            stdout=subprocess.DEVNULL, check=True)
        native = list(csv.DictReader((folder / 'results/startup_native_margins.csv').open()))
        support = [json.loads(line) for line in (folder / 'results/startup_support_margins.jsonl').read_text().splitlines()]
        assert len(native) == len(support) == len(rows)
        values = [margin(np.array(row['joint_q'][:3]), yaw)[0] for row, yaw in zip(rows, headings)]
        start = next(c for c in cohort['cases'] if c['case_id'] == cid)['start']['ground']
        minimum_gap = min(r['support_gap_extra_margin_m'] for r in support)
        minimum_source = min(float(r['native_source_solid_margin_m']) for r in native)
        report = dict(case_id=cid, physics_steps=0, original_factory_frames=len(rows),
            start_s=rows[0]['physics_time_s'], end_s=rows[-1]['physics_time_s'],
            maximum_recorded_PD_xy_drift_m=max(math.dist(row['joint_q'][:2], start[:2]) for row in rows),
            minimum_support_gap_extra_margin_m=minimum_gap, minimum_source_solid_margin_m=minimum_source,
            minimum_raw_point_margin_m=min(values),
            sampled_factory_envelope_clear=min(minimum_gap, minimum_source, min(values)) >= 0,
            static_verdict_counts={str(v): sum(int(r['static_support_verdict']) == v for r in native)
                for v in sorted({int(r['static_support_verdict']) for r in native})},
            source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            factory_states_sha256=hashlib.sha256(capture.read('factory_video_states.json').encode()).hexdigest(),
            claim='Original factoryvideo poses, including zero-time crouch. Geometric margins kept separate from nominal0.3m standing-height verdict; no new physics or interpolated states.')
        (output / (cid + '.json')).write_text(json.dumps(report, indent=2) + '\n')
        reports.append(report)
        print(json.dumps(report), flush=True)
    (output / 'summary.json').write_text(json.dumps(dict(physics_steps=0, cases=reports,
        audited_factory_frames=sum(r['original_factory_frames'] for r in reports),
        scope='Factory video-state stream; later10Hz sensor stream is independently audited'), indent=2) + '\n')

if __name__ == '__main__':
    main()
