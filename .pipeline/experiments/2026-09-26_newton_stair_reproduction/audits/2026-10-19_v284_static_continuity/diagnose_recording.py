"""Reconstruct recorded curves at generic stop/clearance witnesses; zero physics."""
from pathlib import Path
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
import numpy as np
from scipy.interpolate import BSpline

HERE = Path(__file__).resolve().parent
VERSION = HERE.parents[1] / 'versions/v284'
BASE = Path('/data/sun/vla_mppi_20261009')
ROOT = Path('/home/sun/vla_exec/static_continuity_v284')
OUT = ROOT / 'recorded_curve_diagnostics'
sys.path.insert(0, str(VERSION.parent / 'v196'))
from analyze_remote import Capture


def main():
    OUT.mkdir(exist_ok=False)
    queries = []
    bindings = {}
    cases = json.loads((VERSION / 'manifest.json').read_text())['physical_cases']

    def emit(case, target, role, xyz, yaw, **details):
        queries.append(dict(id=len(queries), case=case, target_time_s=target,
                            role=role, xyz=list(map(float, xyz)), yaw=float(yaw), **details))

    for case in cases:
        directory = HERE / 'physical' / case / 'results'
        measured = list(csv.DictReader((directory / 'body_margins.csv').open()))
        continuity = json.loads((directory / 'command_continuity.json').read_text())
        window = json.loads((directory / 'window_audit.json').read_text())['windows']['navigation_since_goal_request']
        lo, hi = window['measured']['window_s']
        measured = [r for r in measured if lo <= float(r['time_s']) < hi]
        assert measured
        targets = {float(min(measured, key=lambda r: float(r['native_source_solid_margin_m']))['time_s']), float(measured[-1]['time_s'])}
        for predicate in [lambda r: int(r['static_support_verdict']) == 11,
                          lambda r: float(r['native_source_solid_margin_m']) < 0]:
            found = next((r for r in measured if predicate(r)), None)
            if found:
                targets.add(float(found['time_s']))
        motion = continuity['first_translation_command_s']
        pauses = [r for r in window['measured']['intervals'] if motion is not None and r['end_s'] > motion]
        if pauses:
            pause = max(pauses, key=lambda r: r['end_s'] - max(r['start_s'], motion))
            targets.add(min(pause['end_s'] - .02, max(pause['start_s'], motion) + .5))
        capture = Capture(Path('/home/sun/vla_exec/physical_runs_v284') /
                          f'v284_{case}_attempt01/runs/v284_{case}_attempt01')
        events = capture.rows('artifacts/reactive_observations.jsonl')
        curves = [r for r in events if r['event'] == 'bspline' and not r['data']['emergency_stop']]
        telemetry = capture.rows('telemetry.jsonl')
        bindings[case] = dict(recording=str(capture.root), sources=capture.sources)
        for target in sorted(targets):
            body = min(measured, key=lambda r: abs(float(r['time_s']) - target))
            xyz = np.array([float(body[k]) for k in ('x', 'y', 'z')])
            yaw = float(body['yaw'])
            state = min(telemetry, key=lambda r: abs(r['physics_time_s'] - target))
            emit(case, target, 'measured', xyz, yaw, stance=state.get('stance_mode'),
                 applied_command=state['effective_command'],
                 measured_speed_m_s=math.hypot(*state['body_sensor']['linear_world'][:2]))
            previous = [r for r in curves if r['clock_ns']*1e-9 <= target]
            if not previous:
                continue
            event = max(previous, key=lambda r: r['clock_ns'])
            curve = event['data']
            points = np.array([[p[k] for k in ('x', 'y', 'z')] for p in curve['pos_pts']])
            spline = BSpline(curve['knots'], points, curve['order'])
            begin, end = curve['knots'][curve['order']], curve['knots'][-curve['order']-1]
            start = curve['start_time']['sec'] + curve['start_time']['nanosec']*1e-9
            phase = np.clip(target-start, begin, end)

            def heading(t):
                delta = spline(min(t+.8, end))-spline(t)
                if np.dot(delta[:2], delta[:2]) < 1e-4:
                    delta = spline.derivative()(t)
                return math.atan2(delta[1], delta[0]) if np.dot(delta[:2], delta[:2]) > 1e-8 else yaw

            planned_yaw = heading(phase)
            details = dict(traj_id=curve['traj_id'], publication_s=event['clock_ns']*1e-9,
                           start_s=start, duration_s=end-begin, nominal_phase_s=float(phase),
                           curve_expired_at_query=bool(target-start >= end),
                           nominal_position_error_m=float(np.linalg.norm(spline(phase)-xyz)),
                           nominal_heading_error_rad=math.remainder(yaw-planned_yaw, 2*math.pi))
            emit(case, target, 'planned_at_nominal_phase', spline(phase), planned_yaw, **details)
            emit(case, target, 'measured_with_planned_yaw', xyz, planned_yaw, **details)
            emit(case, target, 'planned_with_measured_yaw', spline(phase), yaw, **details)
            for t in np.linspace(begin, end, max(2, math.ceil((end-begin)/.01)+1)):
                emit(case, target, 'whole_published_curve', spline(t), heading(t), traj_id=curve['traj_id'])

    (OUT/'queries.json').write_text(json.dumps(dict(bindings=bindings, rows=queries), indent=2)+'\n')
    with (OUT/'queries.txt').open('w') as output:
        for row in queries:
            output.write(' '.join(map(str, [row['id']]+row['xyz']+[row['yaw']]))+'\n')
    shell = ('source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && '
             'source /task/command_continuity_v206_20261015/install/setup.bash && '
             'source /work/install/setup.bash && source /work/fixtures/probe271.env && '
             '/binary/margin_build/body_margin /work/fixtures/building/environment225.env '
             '10040917858432847476 /work/fixtures/building/native.support 15212154834549674106 '
             '/audit/queries.txt /audit/margins.csv "$RAW_FIELD" "$RAW_FNV"')
    subprocess.run(['docker', 'run', '--rm', '--pull=never', '--user', f'{os.getuid()}:{os.getgid()}',
                    '--cpus=2', '--memory=3g', '-v', str(BASE)+':/task:ro',
                    '-v', str(ROOT/'native')+':/work:ro',
                    '-v', str(HERE/'physical'/cases[0])+':/binary:ro', '-v', str(OUT)+':/audit:rw',
                    '--entrypoint', '/bin/bash',
                    'sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4',
                    '-c', shell], check=True)
    values = list(csv.DictReader((OUT/'margins.csv').open()))
    assert len(values) == len(queries)
    for case in cases:
        summaries = []
        for target in sorted({r['target_time_s'] for r in queries if r['case'] == case}):
            group = [(r, v) for r, v in zip(queries, values) if r['case'] == case and r['target_time_s'] == target]
            curve = [v for r, v in group if r['role'] == 'whole_published_curve']
            summaries.append(dict(target_time_s=target,
                poses=[dict(**r, native_margin=v) for r, v in group if r['role'] != 'whole_published_curve'],
                curve_support_rejections=sum(int(v['static_support_verdict']) != 0 for v in curve),
                curve_source_solid_min_m=min((float(v['native_source_solid_margin_m']) for v in curve), default=None)))
        record = dict(case=case, physics_steps=0, targets=summaries, input=bindings[case],
                      analysis_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      claim='Nominal elapsed-phase reconstruction of actual published curves; not exact asynchronous internal tracker scheduling or a causal ablation.')
        (HERE/'physical'/case/'results/recorded_curve_diagnosis.json').write_text(json.dumps(record, indent=2)+'\n')
        print(json.dumps(dict(case=case, targets=len(summaries))), flush=True)
    manifest = {p.name: dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                for p in OUT.iterdir() if p.is_file()}
    (HERE/'results/recorded_curve_diagnostics_inventory.json').write_text(json.dumps(dict(
        physics_steps=0, root=str(OUT), files=manifest), indent=2)+'\n')


if __name__ == '__main__':
    main()
