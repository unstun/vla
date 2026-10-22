"""Inspect recorded v283 curves/poses; no physics or navigation execution."""
from pathlib import Path
import csv, hashlib, json, math, os, subprocess, zipfile
import numpy as np
from scipy.interpolate import BSpline

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
BASE = Path('/data/sun/vla_mppi_20261009')
OUT = Path('/home/sun/vla_exec/navigation_geometry_v283/candidate_diagnostics')
AUDIT = HERE
OUT.mkdir(parents=True, exist_ok=True)
rows = []
bindings = {}

def stamp(value):
    return value['sec'] + value['nanosec'] * 1e-9

def emit(case, target, role, xyz, yaw, **details):
    rows.append(dict(id=len(rows), case=case, target_time_s=target, role=role,
                     xyz=list(map(float, xyz)), yaw=float(yaw), **details))

for case in ('D07', 'S04'):
    run = f'v283_{case}_attempt01'
    raw = Path('/home/sun/vla_exec/physical_runs_v283') / run / 'runs' / run
    measured = list(csv.DictReader((AUDIT / 'physical' / case / 'results/body_margins.csv').open()))
    bad_support = [r for r in measured if int(r['static_support_verdict']) == 11]
    bad_solid = [r for r in measured if float(r['native_source_solid_margin_m']) < 0]
    targets = {float(r['time_s']) for r in bad_support}
    if bad_solid:
        targets.update((float(bad_solid[0]['time_s']),
                        float(min(bad_solid, key=lambda r: float(r['native_source_solid_margin_m']))['time_s'])))
    loose=raw/'artifacts/reactive_observations.jsonl'
    if loose.is_file():data=loose.read_bytes()
    else:
        with zipfile.ZipFile(raw / 'raw_capture.zip') as archive:
            data = archive.read('artifacts/reactive_observations.jsonl')
    bindings[case] = dict(recording=str(raw), observation_sha256=hashlib.sha256(data).hexdigest())
    curves = [r for r in map(json.loads, data.splitlines())
              if r['event'] == 'bspline' and not r['data']['emergency_stop']]
    for target in sorted(targets):
        body = min(measured, key=lambda r: abs(float(r['time_s']) - target))
        xyz = np.array([float(body[k]) for k in ('x', 'y', 'z')])
        yaw = float(body['yaw'])
        emit(case, target, 'measured', xyz, yaw)
        event = max((r for r in curves if r['clock_ns'] * 1e-9 <= target), key=lambda r: r['clock_ns'])
        c = event['data']; points = np.array([[p[k] for k in ('x', 'y', 'z')] for p in c['pos_pts']])
        spline = BSpline(c['knots'], points, c['order'])
        begin, end = c['knots'][c['order']], c['knots'][-c['order']-1]
        phase = np.clip(target - stamp(c['start_time']), begin, end)
        def heading(t):
            p = spline(t); delta = spline(min(t + .8, end)) - p
            if np.dot(delta[:2], delta[:2]) < 1e-4: delta = spline.derivative()(t)
            return math.atan2(delta[1], delta[0]) if np.dot(delta[:2], delta[:2]) > 1e-8 else yaw
        pyaw = heading(phase)
        common = dict(traj_id=c['traj_id'], publication_s=event['clock_ns']*1e-9,
                      start_s=stamp(c['start_time']), duration_s=end-begin,
                      phase_s=float(phase), curve_expired_at_query=bool(target-stamp(c['start_time'])>=end), position_error_m=float(np.linalg.norm(spline(phase)-xyz)),
                      heading_error_rad=math.remainder(yaw-pyaw,2*math.pi))
        emit(case, target, 'planned_at_phase', spline(phase), pyaw, **common)
        emit(case, target, 'measured_with_planned_yaw', xyz, pyaw, **common)
        emit(case, target, 'planned_with_measured_yaw', spline(phase), yaw, **common)
        for t in np.linspace(begin, end, max(2, math.ceil((end-begin)/.01)+1)):
            emit(case, target, 'whole_published_curve', spline(t), heading(t), traj_id=c['traj_id'])

(OUT/'recorded_queries.json').write_text(json.dumps(dict(bindings=bindings, rows=rows,
    claim='Recorded publication reconstruction, not exact asynchronous tracker scheduling'), indent=2)+'\n')
with (OUT/'recorded_queries.txt').open('w') as f:
    for r in rows: f.write(' '.join(map(str,[r['id']]+r['xyz']+[r['yaw']]))+'\n')
binary='/binary/margin_build/body_margin'
shell='source /opt/ros/foxy/setup.bash && source /task/recovery_v188/install/setup.bash && source /task/command_continuity_v206_20261015/install/setup.bash && source /work/install/setup.bash && source /work/fixtures/probe271.env && '
shell+=binary+' /work/fixtures/building/environment225.env 10040917858432847476 /work/fixtures/building/native.support 15212154834549674106 /audit/recorded_queries.txt /audit/recorded_margins.csv "$RAW_FIELD" "$RAW_FNV"'
subprocess.run(['docker','run','--rm','--pull=never','--user',f'{os.getuid()}:{os.getgid()}',
    '--cpus=2','--memory=3g','-v',str(BASE)+':/task:ro',
    '-v','/home/sun/vla_exec/navigation_geometry_v283/native:/work:ro','-v',str(HERE/'physical/A04')+':/binary:ro','-v',str(OUT)+':/audit:rw',
    '--entrypoint','/bin/bash','sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4','-c',shell],check=True)
values=list(csv.DictReader((OUT/'recorded_margins.csv').open()))
assert len(values)==len(rows)
summary=[]
for key in sorted({(r['case'],r['target_time_s']) for r in rows}):
    group=[(r,v) for r,v in zip(rows,values) if (r['case'],r['target_time_s'])==key]
    selected=[dict(**r,margin=v) for r,v in group if r['role']!='whole_published_curve']
    curve=[v for r,v in group if r['role']=='whole_published_curve']
    summary.append(dict(case=key[0],time_s=key[1],poses=selected,
        curve_support_rejections=sum(int(v['static_support_verdict'])!=0 for v in curve),
        curve_solid_min_m=min(float(v['native_source_solid_margin_m']) for v in curve)))
(OUT/'recorded_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
for s in summary:
    row=dict(case=s['case'],time=s['time_s'],curve_support=s['curve_support_rejections'],
        curve_solid=s['curve_solid_min_m'],poses=[(p['role'],p['margin']['static_support_verdict'],p['margin']['native_source_solid_margin_m'],p.get('position_error_m'),p.get('heading_error_rad')) for p in s['poses']])
    print(json.dumps(row),flush=True)
