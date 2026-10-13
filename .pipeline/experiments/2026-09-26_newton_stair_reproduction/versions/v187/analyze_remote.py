"""Analyze actual gpu5070ti Newton captures with explicit host/container clock mapping."""
from pathlib import Path
import argparse,csv,hashlib,importlib.util,json,math,re,zipfile
import numpy as np

HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
source=BASE/'versions/v47/analyze_trial.py'
spec=importlib.util.spec_from_file_location('original_planning_round_parser',source)
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)

class Capture:
    def __init__(self,root):self.root=root;self.sources={}
    def read(self,name):
        path=self.root/name
        if path.is_file():data=path.read_bytes()
        else:
            receipt=json.loads((self.root/'raw_capture_manifest.json').read_text())
            with zipfile.ZipFile(self.root/'raw_capture.zip') as z:data=z.read(name)
            item=receipt['members'][name]
            assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
        self.sources[name]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
        return data.decode()
    def json(self,name):return json.loads(self.read(name))
    def rows(self,name):return [json.loads(x) for x in self.read(name).splitlines() if x.strip()]

def analyze(root,output,metrics_only=False):
    capture=Capture(root);text=capture.read('nav2.log')
    class Log:
        def read_text(self):return text
    starts,rounds=core.parse_rounds(Log());assert starts and rounds,'No completed native planning rounds'
    result=capture.json('result.json');points=capture.rows('sensor.jsonl')
    telemetry=capture.rows('telemetry.jsonl');clock=capture.rows('clock_samples.jsonl')
    sync=[r for r in clock if r.get('accepted') and r.get('samples',0)>=500]
    assert sync and len({r['responder'] for r in sync})==1,'No consistent converged clock mapping'
    remote=np.array([r['remote']/1e9 for r in sync]);offset=np.array([r['filtered_offset_ns']/1e9 for r in sync])
    assert np.all(np.diff(remote)>0)
    def local_time(value):return value+float(np.interp(value,remote,offset))
    pace=result['realtime_pacing'];begin=pace['wall_anchor_monotonic_s'];end=begin+pace['wall_elapsed_s']
    host=np.array([r['realtime_pacing']['wall_anchor_monotonic_s']+r['realtime_pacing']['wall_elapsed_s'] for r in telemetry])
    native=np.array([r['physics_time_s'] for r in telemetry])
    assert np.all(np.diff(host)>0) and np.all(np.diff(native)>0),'Non-increasing actual physics clock'
    def simulation(value):return float(np.interp(value,np.r_[begin,host,end],np.r_[pace['native_anchor_s'],native,result['physics_duration_s']]))
    lines=text.splitlines()
    for row in rounds:
        row['host_start_s']=local_time(row['start_wall_s'])
        row['host_finish_s']=local_time(row['start_wall_s']+row['wall_s'])
        row['warm_accepts']=sum('V48_WARM_RESULT accepted=1' in s for s in lines[row['start_line']-1:row['end_line']])
    selected=[r for r in rounds if begin<=r['host_finish_s']<=end]
    attempts=[r for r in starts if begin<=local_time(r['start_wall_s'])<=end]
    successful=sorted(r['host_finish_s'] for r in selected if r['success'])
    command_rows=capture.rows('command_frequencies.jsonl');commands={}
    for row in command_rows:
        stamp=local_time(row['wall_monotonic_s'])
        if begin<=stamp<=end:commands.setdefault(row['topic'],[]).append(stamp)
    xyz=[p['body_sensor']['position'] for p in points];path=[0.]
    pauses=[];pause_start=None;last=None
    for a,b in zip(points,points[1:]):
        path.append(path[-1]+math.dist(a['body_sensor']['position'],b['body_sensor']['position']))
        if not starts[0]['ros_s']<=b['sim_time_s']<=result['physics_duration_s']:continue
        dt=b['sim_time_s']-a['sim_time_s'];low=0<dt<.5 and math.hypot(*b['body_sensor']['linear_world'][:2])<.05
        if low:
            if pause_start is None:pause_start=a['sim_time_s']
            last=b['sim_time_s']
        elif pause_start is not None:
            pauses.append({'start_sim_s':pause_start,'end_sim_s':last,'duration_sim_s':last-pause_start});pause_start=None
    if pause_start is not None:pauses.append({'start_sim_s':pause_start,'end_sim_s':last,'duration_sim_s':last-pause_start})
    metrics={'run':root.name,'host':'gpu5070ti','native_version':'Nav2 Foxy AMD64 native v187 SCAN','integration_version':capture.json('episode_request.json')['integration_version'],
        'requested_physics_end_s':capture.json('episode_request.json')['max_physics_s'],
        'actual_physics_end_s':result['physics_duration_s'],'physics_steps':result['physics_steps'],
        'navigation_sim_duration_s':pace['native_elapsed_s'],'navigation_wall_duration_s':end-begin,
        'actual_rtf':pace['actual_rtf'],'dropped_physics_steps':pace['dropped_physics_steps'],
        'planning':{'attempts':len(attempts),'completed':len(selected),'successful':len(successful),
            'attempt_wall_hz':len(attempts)/(end-begin),'successful_wall_hz':len(successful)/(end-begin),
            'solve_ms':core.distribution([r['wall_s']*1000 for r in selected]),
            'rounds_over_100ms':sum(r['wall_s']>=.1 for r in selected),
            'rounds_over_1000ms':sum(r['wall_s']>=1 for r in selected),
            'warm_accepted_attempts':sum(r['warm_accepts'] for r in selected)},
        'measured_path_m':path[-1],'measured_displacement_m':math.dist(xyz[0],xyz[-1]),
        'final_body_xyz_m':xyz[-1],'maximum_body_z_m':max(p[2] for p in xyz),
        'pauses_over_1s':[p for p in pauses if p['duration_sim_s']>=1],
        'longest_pause_sim_s':max((p['duration_sim_s'] for p in pauses),default=0),
        'emergency_transitions':len(re.findall(r'from .* to EMERGENCY_STOP',text)),
        'current_curve_invalid_events':text.count('remaining_spline_invalid'),
        'optimizer_repair_failures':text.count('A-star failed; aborting optimization'),
        'target_connector_rejections':text.count('reason=target_connector'),
        'controller':{topic:{'samples':len(ts),'wall_hz':core.rate(ts)} for topic,ts in commands.items()},
        'fallen':result.get('fallen',False),'minimum_base_up_z':min(r['base_up_z'] for r in telemetry),
        'terminal':result.get('finish_request'),'backend_gate':result.get('last_backend',{}).get('gate',{}).get('closed_reason'),'stop_flow':result.get('last_backend',{}).get('stop_flow'),'state_copyback_verified':capture.json('state_copyback.json')['verified'],
        'clock_mapping':{'source':'Original converged clock_samples.jsonl; filtered local-minus-remote',
            'samples':len(sync),'median_host_minus_container_s':float(np.median(offset)),
            'maximum_rtt_ms':max(r['rtt_ns'] for r in sync)/1e6},
        'sustained_30hz_validated':False,'full_qualification':False,
        'comparison_boundary':'Actual gpu5070ti CPU Newton plus AMD64 Foxy Nav2. Separate cohort from Mac; no cross-host pooling.',
        'frequency_definition':'Trailing (t-1,t] wall-second counts, actual clock mapped to simulation time',
        'source':capture.sources,'parser_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    output.mkdir(parents=True,exist_ok=True)
    map_rows=[{'revision':int(a),'clouds':int(b),'stamp_s':float(c),'mapping_ms':float(d),'copy_ms':float(e),'reduced':int(f),'max_queue':int(g)} for a,b,c,d,e,f,g in re.findall(r'V82_MAP_SNAPSHOT revision=(\d+) clouds=(\d+) cloud_stamp=([0-9.]+) mapping_ms=([0-9.]+) copy_ms=([0-9.]+) reduced=(\d+) max_queue=(\d+)',text)]
    metrics['mapping']={'snapshots':len(map_rows),'maximum_queued_clouds':max((x['max_queue'] for x in map_rows),default=0),'reduced_clouds':max((x['reduced'] for x in map_rows),default=0),'mapping_ms':core.distribution([x['mapping_ms'] for x in map_rows]),'copy_ms':core.distribution([x['copy_ms'] for x in map_rows]),'claim':'Background map work; these times are not planner-thread blocking or complete round solve latency.'}
    (output/'metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    (output/'max_round.json').write_text(json.dumps(max(selected,key=lambda r:r['wall_s']),indent=2)+'\n')
    with (output/'latency.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['simulation_s','wall_s_host','solve_ms','success','warm_accepts'])
        w.writerows((r['ros_s'],r['host_start_s'],r['wall_s']*1000,int(r['success']),r['warm_accepts']) for r in selected)
    grid=np.arange(begin+1,end,.05);sw=np.array(sorted(local_time(r['start_wall_s']) for r in attempts));cw=np.array(successful)
    hz=np.searchsorted(sw,grid,side='right')-np.searchsorted(sw,grid-1,side='right')
    shz=np.searchsorted(cw,grid,side='right')-np.searchsorted(cw,grid-1,side='right')
    sim=np.array([simulation(x) for x in grid])
    with (output/'frequency.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['simulation_s','wall_s_host','attempts_hz_1wallsecond','successful_hz_1wallsecond'])
        w.writerows(zip(sim,grid,hz,shz))
    if not metrics_only:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(3,1,figsize=(10,9),sharex=True)
        axes[0].plot(sim,hz,color='#97A5B0',lw=.7,label='Attempts');axes[0].plot(sim,shz,color='#126D8C',lw=.9,label='Successful plans')
        axes[0].axhline(30,ls='--',color='#333333');axes[0].set_ylim(0,35);axes[0].set_ylabel('Hz / trailing wall second')
        axes[0].set_title(f"{root.name}: {metrics['planning']['successful_wall_hz']:.2f} successful wall Hz, RTF {pace['actual_rtf']:.3f}");axes[0].legend()
        xs=np.array([r['ros_s'] for r in selected]);ys=np.array([r['wall_s']*1000 for r in selected]);ok=np.array([r['success'] for r in selected]);fast=ys<10
        axes[1].axhspan(.01,10,color='#E1F2E9')
        for mask,c,label in [(ok&fast,'#17815C','Success <10 ms'),(ok&~fast,'#176B94','Success >=10 ms'),(~ok,'#B53B3B','Failed')]:
            axes[1].scatter(xs[mask],ys[mask],s=8,c=c,alpha=.6,label=label)
        axes[1].axhline(1000/30,ls='--',color='#333333',lw=.8);axes[1].set_yscale('log');axes[1].set_ylim(max(.1,ys.min()*.5),max(100,ys.max()*1.3))
        axes[1].set_ylabel('Complete round (ms)');axes[1].set_title(f'Max solve {ys.max():.1f} ms');axes[1].legend()
        axes[2].plot([p['sim_time_s'] for p in points],path,color='#126D8C');axes[2].set_ylabel('Measured path (m)');axes[2].set_xlabel('Actual simulation time (s)')
        axes[2].set_title(f"Path {path[-1]:.2f} m; longest measured low-speed interval {metrics['longest_pause_sim_s']:.2f} s")
        for ax in axes:ax.set_xlim(pace['native_anchor_s'],result['physics_duration_s']);ax.grid(alpha=.2)
        fig.tight_layout();fig.savefig(output/'time_series.png',dpi=150);fig.savefig(output/'time_series.pdf');plt.close(fig)
    (output/'provenance.json').write_text(json.dumps({'capture_root':str(root),'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'clock_domains_mapped':True,'no_simulation_zero_relabel':True,'source':capture.sources},indent=2)+'\n')
    print(json.dumps({k:metrics[k] for k in ('run','actual_physics_end_s','actual_rtf','planning','measured_path_m','pauses_over_1s','emergency_transitions')},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--metrics-only',action='store_true');args=p.parse_args();analyze(args.run_root,args.output,args.metrics_only)
