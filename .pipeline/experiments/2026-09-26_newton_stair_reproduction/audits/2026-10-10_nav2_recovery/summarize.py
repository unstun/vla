"""Analyze all predeclared repeats; preserve per-run events and small-sample limits."""
from pathlib import Path
import collections
import csv
import hashlib
import json
import math
import re
import statistics
import sys

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
TASK=Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0,str(BASE/'versions/v128'))
from analyze_remote import Capture
from analyze_events import analyze as analyze_recovery
OUTPUT=TASK/'results/recovery_v128_repeats/analysis'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def fisher(a,b,c,d):
    n=a+b+c+d; col=a+c; n1=a+b
    def probability(k):return math.comb(col,k)*math.comb(n-col,n1-k)/math.comb(n,n1)
    observed=probability(a)
    return min(1.,sum(probability(k) for k in range(max(0,n1-(n-col)),min(n1,col)+1)
                      if probability(k)<=observed+1e-14))

def wilson(success,n):
    z=1.959963984540054;p=success/n;den=1+z*z/n
    center=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,center-half),min(1,center+half)]

def main():
    assert HERE.is_relative_to(TASK/'repo')
    progress=json.loads((TASK/'results/recovery_v128_repeats/progress.json').read_text())
    assert progress['state']=='completed' and len(progress['completed'])==12,'Do not summarize an unfinished batch as complete'
    OUTPUT.mkdir(exist_ok=False)
    events=[];rows=[];sources={};recovery=[]
    for trial in progress['completed']:
        tag=trial['tag'];recovery.append(analyze_recovery(tag));root=TASK/'trials'/tag/'runs'/tag
        compact=TASK/'results/recovery_v128/comparison'/tag
        outcome=json.loads((compact/'outcome.json').read_text());m=outcome['metrics']
        assert outcome['retention']=='completed' and m['state_copyback_verified'] and outcome['execution_exit']==0
        capture=Capture(root);text=capture.read('nav2.log');lines=text.splitlines()
        cloud_records=json.loads((root/'sensor_manifest.json').read_text())
        scan_audit=[json.loads(line) for line in (root/'bridge_scan_audit.jsonl').read_text().splitlines() if line.strip()]
        rejection=[];causes=collections.Counter();timing=[];controller_errors=[];revocations=[]
        for number,line in enumerate(lines,1):
            if '[ERROR]' in line and '] [controller_server]:' in line:
                controller_errors.append({'line':number,'message':line})
            if 'SCAN output revoked reason=' in line:
                revocations.append({'line':number,'reason':line.split('SCAN output revoked reason=',1)[1].split()[0]})
            if 'nominal_replan frequency_hz=' in line:
                wall=re.search(r'\[(\d+\.\d+)\]',line);sim=re.search(r'ros_s=([\d.]+)',line)
                if wall and sim:timing.append((float(wall[1]),float(sim[1])))
            marker=next((key for key in ('scan_safety_evidence_stale','scan_trajectory_missing',
                'Failed to make progress','Navigation failed','heartbeat_stale','odom_stale') if key in line),None)
            if marker:
                causes[marker]+=1
                events.append({'run':tag,'line':number,'cause':marker,'message':line})
            if 'SCAN evidence rejected now=' in line:
                fields={key:float(value) for key,value in re.findall(r'(now|observation_stamp|observation_age|proof_age|active|clear)=([-\d.]+)',line)}
                if fields:
                    nearest=min(cloud_records,key=lambda r:abs(r['sim_time_s']-fields['now']))
                    fields.update(line=number,body_xyz=nearest['body_sensor']['position'],
                                  nearest_pose_delta_s=nearest['sim_time_s']-fields['now'])
                    rejection.append(fields)
        finish=m.get('terminal') or {}
        arrived=finish.get('backend_terminal_status')=='FINISHED' and finish.get('note')=='native arrival and measured PD hold'
        row={'run':tag,'order':trial['index'],'variant':trial['variant'],'arrived':arrived,
             'terminal':finish.get('backend_terminal_status'),'fallen':m['fallen'],
             'outcome_class':'arrived' if arrived else ('fall' if m['fallen'] else ('action_failed' if finish.get('backend_terminal_status')=='FAILED' else 'not_finished')),
             'follow_path_aborts':sum('[follow_path]' in line and 'Aborting handle' in line for line in lines),
             'path_m':m['measured_path_m'],'final_xyz':m['final_body_xyz_m'],
             'end_sim_s':m['actual_physics_end_s'],'navigation_duration_s':m['navigation_sim_duration_s'],
             'longest_pause_s':m['longest_pause_sim_s'],'pauses':m['pauses_over_1s'],
             'solve_ms':m['planning']['solve_ms'],'over_60ms':m['planning']['over_60ms'],
             'failed_rounds':m['planning']['completed']-m['planning']['successful'],
             'completed_rounds':m['planning']['completed'],'emergency_transitions':m['emergency_transitions'],
             'actual_rtf':m['actual_rtf'],'mapping':m['mapping'],'causes':dict(causes),
             'safety_rejections':rejection,'controller_errors':controller_errors,'revocations':revocations,
             'recovery':recovery[-1],
             'sensor_count':len(cloud_records),
             'scan_audit_outcomes':dict(collections.Counter(r['outcome'] for r in scan_audit)),
             'max_sensor_compute_ms':max(r['sensor']['wall_s'] for r in cloud_records)*1000,
             'max_scan_publication_delay_s':max(r['published_at_physics_s']-r['sim_time_s'] for r in cloud_records),
             'preflight':json.loads((TASK/'results/recovery_v128_repeats'/f'{tag}_preflight.json').read_text())}
        rows.append(row);sources[tag]={'capture':capture.sources,'outcome_sha256':sha(compact/'outcome.json'),
             'sensor_manifest_sha256':sha(root/'sensor_manifest.json'),'bridge_audit_sha256':sha(root/'bridge_scan_audit.jsonl')}
    groups={name:[r for r in rows if r['variant']==name] for name in ('baseline','candidate')}
    stats={}
    for name,group in groups.items():
        n=len(group);s=sum(r['arrived'] for r in group);assert n==6
        stats[name]={'trials':n,'arrivals':s,'failures':n-s,'arrival_wilson_95':wilson(s,n),
            'stale_label_runs':sum(bool(r['causes'].get('scan_safety_evidence_stale')) for r in group),
            'progress_failure_runs':sum(bool(r['causes'].get('Failed to make progress')) for r in group),
            'median_p95_ms':statistics.median(r['solve_ms']['p95'] for r in group),
            'median_p99_ms':statistics.median(r['solve_ms']['p99'] for r in group),
            'median_maximum_ms':statistics.median(r['solve_ms']['maximum'] for r in group),
            'median_longest_pause_s':statistics.median(r['longest_pause_s'] for r in group),
            'falls':sum(r['fallen'] for r in group),
            'negative_safety_abort_delays_ms':[e['follow_path_abort_after_s']*1000 for r in group for e in r['recovery']['stops'] if e['reason']=='scan_safety_rejected' and e['follow_path_abort_after_s'] is not None],
            'fsm_rejected_routes':sum(e['status']=='rejected' and e['consumer']=='fsm' for r in group for e in r['recovery']['handoffs']),
            'expired_observation_events':sum(e['observation_age']>.25 for r in group for e in r['safety_rejections'])}
    old,new=stats['baseline'],stats['candidate']
    result={'protocol':'ABBA / BAAB / ABBA, six fresh trials per arm, no navigation-failure early stopping',
            'versions':{'baseline':'v114','candidate':'v128'},'host':'gpu5070ti','statistics':stats,
            'fisher_two_sided_p':fisher(old['arrivals'],old['failures'],new['arrivals'],new['failures']),
            'rows':rows,'source':sources,'script_sha256':sha(Path(__file__)),'recovery_analyzer_sha256':sha(HERE/'analyze_events.py'),
            'limits':['Non-significant count difference is not proof of equivalence.',
                      'Six trials per arm give broad success-rate uncertainty.',
                      'Recorded curves can be replayed exactly; reconstructed maps do not restore original DDS batching/live revisions.',
                      'No navigation code or threshold changed; no Jetson/hardware validation.']}
    (OUTPUT/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    (OUTPUT/'events.json').write_text(json.dumps(events,indent=2)+'\n')
    with (OUTPUT/'trials.csv').open('w') as stream:
        writer=csv.writer(stream);writer.writerow(['order','run','variant','arrived','path_m','end_sim_s','p95_ms','p99_ms','max_ms','longest_pause_s','stale_rejection_events','progress_failures'])
        for r in rows:writer.writerow([r['order'],r['run'],r['variant'],int(r['arrived']),r['path_m'],r['end_sim_s'],r['solve_ms']['p95'],r['solve_ms']['p99'],r['solve_ms']['maximum'],r['longest_pause_s'],len(r['safety_rejections']),r['causes'].get('Failed to make progress',0)])
    print(json.dumps({'statistics':stats,'fisher_two_sided_p':result['fisher_two_sided_p'],'output':str(OUTPUT)}),flush=True)
if __name__=='__main__':main()
