"""Audit saved outputs only; retain as-scored outcomes and require replica parity."""
from pathlib import Path
import collections,csv,hashlib,importlib.util,json,math,subprocess,sys
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'saved_output_audit_v264'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for group,score,fixtures in [('clean',BASE/'mesh_benchmark_v262/scored',BASE/'mesh_benchmark_v262/cases'),('original',BASE/'generic_mechanisms_v261/evaluation/original52_final',BASE/'space_coverage_v257/cases')]:
    for folder in sorted(score.iterdir()):
        if not folder.is_dir() or not (folder/'spline.txt').exists():continue
        cid=folder.name;target=OUT/group/cid
        if not (target/'metrics.txt').exists():
            assert not target.exists()
            with (OUT/(group+'_'+cid+'.log')).open('x') as log:
                subprocess.run([sys.executable,str(HERE/'native.py'),'curve',str(fixtures/cid).replace(str(BASE),'/task',1),str(folder/'spline.txt').replace(str(BASE),'/task',1),'/evaluation/'+group+'/'+cid],stdout=log,stderr=subprocess.STDOUT,check=True)
        old=list(csv.DictReader((folder/'local_samples.csv').open()))
        replica=list(csv.DictReader((target/'replica_samples.csv').open()))
        runtime=list(csv.DictReader((target/'runtime_samples.csv').open()))
        assert len(old)==len(replica)==len(runtime)>0
        keys=('t','x','y','z','yaw','live_verdict','floor_known','edge_margin','native_solid_margin')
        mismatches=[dict(index=i,key=k,before=a[k],after=b[k]) for i,(a,b) in enumerate(zip(old,replica)) for k in keys if float(a[k])!=float(b[k])]
        metrics=dict(line.split('=',1) for line in (target/'metrics.txt').read_text().splitlines() if '=' in line)
        assert metrics['planning_calls']==metrics['physics_steps']=='0'
        bad_old=[r for r in replica if int(r['live_verdict'])];bad_new=[r for r in runtime if int(r['live_verdict'])]
        row=dict(group=group,case_id=cid,samples=len(old),replica_nonidentical_values=len(mismatches),first_mismatches=mismatches[:6],
            old_lookahead_s=.1,runtime_lookahead_s=float(metrics['runtime_lookahead_s']),native_full_curve_status=int(metrics['full_curve_status']),
            replica_rejected_samples=len(bad_old),runtime_rejected_samples=len(bad_new),
            replica_rejects=dict(collections.Counter(r['live_verdict'] for r in bad_old)),runtime_rejects=dict(collections.Counter(r['live_verdict'] for r in bad_new)),
            runtime_edge_margin_min=min(float(r['edge_margin']) for r in runtime),runtime_solid_margin_min=min(float(r['native_solid_margin']) for r in runtime),
            old_rejected_witnesses=bad_old[:6],runtime_rejected_witnesses=bad_new[:6],
            input_spline_sha256=sha(folder/'spline.txt'),input_sample_sha256=sha(folder/'local_samples.csv'),
            replica_samples_sha256=sha(target/'replica_samples.csv'),runtime_samples_sha256=sha(target/'runtime_samples.csv'),planning_calls=0,physics_steps=0)
        rows.append(row);(target/'comparison.json').write_text(json.dumps(row,indent=2)+'\n')
        (OUT/'curve_progress.json').write_text(json.dumps(rows,indent=2)+'\n')
        print(json.dumps({k:row[k] for k in ('group','case_id','replica_nonidentical_values','replica_rejected_samples','runtime_rejected_samples')}),flush=True)
receipt=dict(cases=len(rows),replica_nonidentical_values=sum(r['replica_nonidentical_values'] for r in rows),
    runtime_rejected_samples=sum(r['runtime_rejected_samples'] for r in rows),planning_calls=0,physics_steps=0,rows=rows,
    scope='Saved outputs, re-applied original paired scans. A correction is qualified only where the old0.1s view reproduces exactly; no scored gate overwritten')
(OUT/'curve_audit.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='rows'}),flush=True)
