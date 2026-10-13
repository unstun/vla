"""Summarize real upstream observations without inventing a final result file."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import math
import numpy as np

HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
spec=importlib.util.spec_from_file_location('source_capture',BASE/'audits/2026-10-04_mac_newton/analyze.py')
shared=importlib.util.module_from_spec(spec);spec.loader.exec_module(shared)
spec=importlib.util.spec_from_file_location('upstream_rounds',BASE/'audits/2026-10-04_upstream_runtime/analyze.py')
upstream=importlib.util.module_from_spec(spec);spec.loader.exec_module(upstream)


def analyze(root,output):
    capture=shared.Capture(root);text=capture.read('scan.log')
    class Log:
        def read_text(self):return text
    _,rounds=upstream.parse_upstream(Log());assert rounds
    sensor=capture.rows('sensor.jsonl');pace=capture.json('realtime_pacing.json')
    clock=capture.rows('clock_samples.jsonl');sync=[r for r in clock if r.get('accepted') and r.get('samples',0)>=500]
    assert sync and len({r['responder'] for r in sync})==1
    remote=np.array([r['remote']/1e9 for r in sync]);offset=np.array([r['filtered_offset_ns']/1e9 for r in sync])
    local=lambda t:t+float(np.interp(t,remote,offset))
    begin=pace['wall_anchor_monotonic_s'];end=begin+pace['wall_elapsed_s']
    selected=[r for r in rounds if begin<=local(r['start_wall_s']+r['wall_s'])<=end]
    successful=[r for r in selected if r['success']]
    path=sum(math.dist(a['body_sensor']['position'],b['body_sensor']['position']) for a,b in zip(sensor,sensor[1:]))
    states=capture.json('video_states.json');timed=[r for r in states if 'wall_monotonic_s' in r]
    backend=capture.json('backend_latest.json');copyback=capture.json('state_copyback.json')
    final_present=(root/'result.json').exists()
    metrics={'run':root.name,'integration_version':capture.json('episode_request.json')['integration_version'],'native_version':'v71 upstream ROS2',
        'actual_rtf':pace['actual_rtf'],'recorded_navigation_wall_s':end-begin,
        'last_pacing_native_s':pace['native_anchor_s']+pace['native_elapsed_s'],
        'last_video_native_s':timed[-1]['physics_time_s'],'last_sensor_native_s':sensor[-1]['sim_time_s'],
        'planning':{'completed':len(selected),'successful':len(successful),
            'successful_wall_hz':len(successful)/(end-begin),
            'solve_ms':shared.core.distribution([r['wall_s']*1000 for r in selected]),
            'max_complete_initialization_attempts':max(r['rebound_attempts'] for r in selected),
            'a_star_200ms_limits':text.count('0.2 second time limit exceeded'),
            'optimizer_collision_restarts':text.count('keep optimizing')},
        'measured_path_m':path,'first_body_xyz_m':sensor[0]['body_sensor']['position'],
        'last_body_xyz_m':sensor[-1]['body_sensor']['position'],
        'nonzero_recorded_command_rows':sum(any(abs(x)>1e-5 for x in r['command']) for r in timed),
        'final_gate':backend.get('gate'),'terminal_results':backend.get('terminal_results'),
        'final_result_file_present':final_present,'state_copyback_verified':copyback['verified'],
        'qualification':('Bounded observed recording; no completed stop or navigation claim.' if final_present else
            'Incomplete failed capture: final result absent. Observed planning/motion only; no completed stop or navigation claim.'),
        'frequency_definition':'Successful completed upstream chains per recorded navigation wall second; incomplete recording, no30Hz event scheduler.',
        'source':capture.sources,'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.mkdir(parents=True,exist_ok=False)
    (output/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    (output/'max_round.json').write_text(json.dumps(max(selected,key=lambda r:r['wall_s']),indent=2)+'\n')
    (output/'provenance.json').write_text(json.dumps({'kind':'partial_capture_analysis','root':str(root),
        'final_result_not_synthesized':True,'clock_domains_mapped':True,'source':capture.sources,
        'analyzer_sha256':metrics['analyzer_sha256']},indent=2)+'\n')
    print(json.dumps({k:metrics[k] for k in ('run','planning','measured_path_m','last_video_native_s','state_copyback_verified')},indent=2))
    return metrics


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();analyze(args.run_root,args.output)
