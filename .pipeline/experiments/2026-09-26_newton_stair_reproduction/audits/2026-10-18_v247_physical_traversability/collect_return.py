"""Compact allowlisted return: reports and three QA images, never raw/cache."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
HERE=Path(__file__).resolve().parent;EXP=HERE.parents[1];BASE=Path('/data/sun/vla_mppi_20261009')
tag=os.environ.get('RETURN_ID','01');assert tag.isdigit() and len(tag)==2
OUT=BASE/'generalization_v248'/('local_return'+tag);OUT.mkdir(exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
origins={}
def copy(p,rel):
 q=OUT/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q);origins[rel]=str(p)
def save(rel,value):
 p=OUT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2)+'\n')
summary=[]
for label,version,cid,rid in [('A02','v248','A02','04'),('G07','v248','G07','01'),('R11','v248','R11','01'),('historical_v246_A02','v246','A02','01')]:
 case=HERE/'physical'/label;results=case/'results';run=f'{version}_{cid}_attempt01'
 render=BASE/'trials'/run/f'video_{version}_render{rid}/runs/full01'
 for p in results.rglob('*'):
  if p.is_file():copy(p,'physical/'+label+'/results/'+str(p.relative_to(results)))
 for p in case.glob('*.py'):copy(p,'physical/'+label+'/'+p.name)
 for n in ('source_identity.json','quality.json'):
  if (case/n).exists():copy(case/n,'physical/'+label+'/'+n)
 for n in ('delivery_verification.json','video_verification.json','host_port_verification.json','display_measurements.json'):
  copy(render/n,'physical/'+label+'/verification/'+n)
 for p in render.glob('*.png'):copy(p,'visuals/'+label+'/'+p.name)
 outcome=json.loads((results/'outcome.json').read_text());window=json.loads((results/'window_audit.json').read_text());w=window['windows'].get('navigation_since_goal_request',dict(measured=dict(count_ge_05s=None,count_ge_1s=None),edge_margin=dict(minimum_m=None),native_static_support=dict(samples=0,not_available=True),successful_rounds=None,completed_rounds=None));pd=json.loads((results/'terminal_pd_hold.json').read_text());scan=json.loads((results/'scanner_timing_summary.json').read_text())
 summary.append(dict(case_id=label,run=run,terminal=outcome['terminal_status'],full_route_passed=outcome['full_route_gate_passed'],physics_end_s=outcome['physics_duration_s'],pause_ge05=w['measured']['count_ge_05s'],pause_ge1=w['measured']['count_ge_1s'],minimum_env_extra_edge_m=w['edge_margin']['minimum_m'],native_static_support=w['native_static_support'],successful_local_rounds=w['successful_rounds'],completed_local_rounds=w['completed_rounds'],terminal_pd=pd,scan=scan,video=json.loads((results/'local_video_delivery.json').read_text())))
 save('physical/'+label+'/verification/native_binding_clarification.json',dict(actual_navigation='v247 PCT+SCAN' if version=='v248' else 'v244 PCT / v240 SCAN',execution=version,locomotion='v216',original_host_verification_sha256=sha(render/'host_port_verification.json'),note='Inherited host-port verifier may retain its v240 descriptive string. Actual frozen native identity is owned by execution source/install/configuration receipts; video title and outcome use the actual treatment. Original metadata is preserved verbatim, not rewritten.'))
for name in ('resource_before_physics.json','live_planner_library_maps.json','physical_batch.json','postprocess_batch01.json'):
 p=BASE/'generalization_v248'/name
 if p.exists():copy(p,'results/'+name)
for name in ('summary.json','requests.json','stdout.log'):
 copy(BASE/'generalization_v248/measured_start_replay01'/name,'results/measured_start_replay/'+name)
for name in ('summary.json','build_and_run.log'):
 copy(BASE/'generalization_v248/raw_pose_audit01'/name,'results/raw_pose_audit/'+name)
for pattern in ('v248_*postprocess*.log','v248_*physical_attempt01.log','v246_A02_postprocess01.log','v248_measured_start_replay01.log','v248_raw_pose_audit01.log'):
 for p in BASE.glob(pattern):copy(p,'results/logs/'+p.name)
save('results/physical_summary.json',dict(cases=summary,authorized_new_physical_attempts=3,actual_new_physical_attempts=3,retries=0,prior_failure_video_is_not_a_new_run=True,protocol='RL, requested scenarios,0.35m hard support/collision and0.1s sensor/deadline unchanged'))
save('results/remote_status_after.json',dict(checked_ns=time.time_ns(),containers=subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}'],text=True),gpu=subprocess.check_output(['nvidia-smi','--query-gpu=memory.used,utilization.gpu','--format=csv,noheader'],text=True),disk_free_bytes=shutil.disk_usage(BASE).free))
files={str(p.relative_to(OUT)):dict(bytes=p.stat().st_size,sha256=sha(p),remote_source=origins.get(str(p.relative_to(OUT)),'generated compact report')) for p in OUT.rglob('*') if p.is_file()}
assert not any(any(s in p for s in ('CMakeFiles','/build/','.npz','sensor.jsonl','telemetry.jsonl','raw_capture.zip')) for p in files)
save('return_manifest.json',dict(host='gpu5070ti',remote_root=str(OUT),files=files,total_bytes=sum(r['bytes'] for r in files.values()),claim='Allowlisted compact reports/QA only. Complete MP4s separately returned as regular files; bulk original capture and build products stay on gpu5070ti.'))
print(json.dumps(dict(return_root=str(OUT),files=len(files),bytes=sum(r['bytes'] for r in files.values()))),flush=True)
