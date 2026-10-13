"""Read verified upstream captures with the existing Mac clock/motion analyzer."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
PARENT=BASE/'audits/2026-10-04_mac_newton/analyze.py'
spec=importlib.util.spec_from_file_location('verified_mac_capture_analysis',PARENT)
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)


def parse_upstream(path):
    rows=[];last_line=1
    pattern=re.compile(r'V71_UPSTREAM_ROUND sequence=(\d+) sim=([\d.]+) start_wall=([\d.]+) wall_ms=([\d.]+) attempts=(\d+) success=(\d+)')
    for i,line in enumerate(path.read_text().splitlines(),1):
        m=pattern.search(line)
        if not m:continue
        sequence,simulation,wall,ms,attempts,success=m.groups()
        assert int(attempts)>0 and 0<=float(ms)
        rows.append({'sequence':int(sequence),'start_line':last_line,'end_line':i,
            'ros_s':float(simulation),'start_wall_s':float(wall),'wall_s':float(ms)/1000,
            'rebound_attempts':int(attempts),'success':bool(int(success)),
            'completed':True,'prefix_proposals':0,'fixed_height_attempts':0,
            'warm_accepts':0,'skipped_slots':None})
        last_line=i+1
    assert all(b['sequence']>a['sequence'] and b['start_wall_s']>=a['start_wall_s']
        for a,b in zip(rows,rows[1:])), 'Upstream observer round ordering invalid'
    return rows,rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    parent.core.parse_rounds=parse_upstream
    parent.analyze(args.run_root,args.output)
    capture=parent.Capture(args.run_root);scan=capture.read('scan.log')
    class Log:
        def read_text(self):return scan
    _,rounds=parse_upstream(Log())
    metrics=json.loads((args.output/'metrics.json').read_text())
    metrics['native_version']='v71 upstream ROS2 planning probe'
    metrics['upstream_repository']='https://github.com/yagami-light7/PCT-SCAN-ROS2'
    metrics['upstream_commit']='1cf45a1c12ca785ce533293302be09d51daf0ccb'
    metrics['planning'].update(complete_attempt_distribution=parent.core.distribution([r['rebound_attempts'] for r in rounds]),
        complete_attempt_counts=dict(Counter(str(r['rebound_attempts']) for r in rounds)),
        a_star_200ms_limits=scan.count('0.2 second time limit exceeded'),
        optimizer_collision_restarts=scan.count('keep optimizing'),
        scheduling='Original upstream event/distance-driven FSM; no 30Hz periodic scheduler added',
        incomplete_rounds='Observer reports completed chains; an unfinished chain at shutdown is not counted')
    metrics['comparison_boundary']='Same Mac/amd64 image, Building, factory, policy, route, sensors, controller and backend as v70. Independent evolving trajectories and upstream planning/terrain/scheduling rules differ. Not a causal same-input speedup or an original ROS1 procedure reproduction.'
    metrics['parser_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (args.output/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    baseline=json.loads((BASE/'versions/v70/analysis/metrics.json').read_text())
    comparison={'upstream':metrics,'current_v70':baseline,
        'max_latency_reduction_claim':None,
        'causal_same_input_speedup_validated':False,
        'full_route_upstream_30hz_validated':False,
        'boundary':metrics['comparison_boundary']}
    (HERE/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    provenance=json.loads((args.output/'provenance.json').read_text())
    provenance.update(analyzer_sha256=metrics['parser_sha256'],
        shared_analyzer_sha256=hashlib.sha256(PARENT.read_bytes()).hexdigest(),
        parser='V71_UPSTREAM_ROUND wraps original reference/new-trajectory chains; no extra recovery or clock changes')
    (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps({'run':metrics['run'],'planning':metrics['planning'],
        'path_m':metrics['measured_path_m'],'physics_end_s':metrics['actual_physics_end_s']},indent=2))


if __name__=='__main__':main()
