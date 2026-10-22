"""One derived audit per saved admitted case after freezing this treatment."""
from pathlib import Path
import concurrent.futures,hashlib,json,os,subprocess,sys
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_point_volume_audit_v276'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((HERE/'manifest.json').read_text())
for rel,h in frozen['files'].items():assert sha(HERE/rel)==h,rel
binding=json.loads((HERE/'results/input_binding.json').read_text())
for rel,h in binding['external_files'].items():assert sha(HERE.parent/rel)==h,rel
for row in binding['saved_inputs'].values():assert sha(Path(row['remote_path']))==row['sha256']
assert not (OUT/'replay_started.json').exists()
(OUT/'replay_started.json').write_text(json.dumps(dict(manifest_sha256=sha(HERE/'manifest.json'),planning_calls=0,physics_steps=0))+'\n')
items=[]
for cohort in ['original52','clean50']:
    old=json.loads((BASE/'source_benchmark_v273'/cohort/'matrix_summary.json').read_text())
    items.extend((cohort,r['case_id']) for r in old['calls'] if r['global_admitted'])
assert len(items)==86

def run(item):
    cohort,cid=item;log=OUT/(cohort+'_'+cid+'_audit01.log')
    with log.open('x') as f:code=subprocess.run(['/home/sun/vla_exec/envs/newton_worker/bin/python',str(HERE/'audit_saved.py'),cohort,cid],stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')).returncode
    p=OUT/'audited'/cohort/cid/'audit.json';r=json.loads(p.read_text()) if p.exists() else {}
    return dict(cohort=cohort,case_id=cid,exit_code=code,global_margin=r.get('route_margins',{}).get('minimum_raw_margin'),local_margin=r.get('local_samples_checked',{}).get('minimum_raw_margin'))
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    for future in concurrent.futures.as_completed([pool.submit(run,item) for item in items]):
        row=future.result();rows.append(row);(OUT/'replay_progress.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True)
(OUT/'replay_complete.json').write_text(json.dumps(dict(cases=len(rows),failures=sum(r['exit_code']!=0 for r in rows),rows=rows,planning_calls=0,physics_steps=0),indent=2)+'\n')
assert all(r['exit_code']==0 for r in rows)
for row in binding['saved_inputs'].values():assert sha(Path(row['remote_path']))==row['sha256']
