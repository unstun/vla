"""Snapshot closed compact offline/qualification evidence for local return."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=Path('/home/sun/vla_exec/local_search_tracking_v285');V=HERE.parents[1]/'versions/v285'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
complete=json.loads((ROOT/'benchmark/complete.json').read_text());assert complete['all_cases_finished'] and complete['calls']==53
OUT=HERE/'offline';OUT.mkdir(exist_ok=False);files={}
for p in sorted((ROOT/'benchmark').rglob('*')):
    if not p.is_file():continue
    assert p.stat().st_size<=8*1024**2,str(p)
    rel=str(p.relative_to(ROOT/'benchmark'));target=OUT/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
    files[rel]=dict(sha256=sha(p),bytes=p.stat().st_size,remote_path=str(p))
logs=HERE/'results/qualification_logs';logs.mkdir(exist_ok=True);logfiles={}
for p in sorted(ROOT.glob('*.log')):
    if not p.name.startswith(('development','probe_build','terrain','parent_','contract','continuity','unit','regressions','build','prepare','qualify_native','reference_error_counts')):continue
    if p.stat().st_size>8*1024**2:continue
    q=logs/p.name;shutil.copy2(p,q);logfiles[p.name]=dict(sha256=sha(p),bytes=p.stat().st_size,remote_path=str(p))
for row in json.loads((V/'results/native_tests.json').read_text()):
    p=Path(row['path']);q=HERE/'results/native_regressions'/p.relative_to(ROOT/'native');q.parent.mkdir(parents=True,exist_ok=True);assert sha(p)==row['sha256'];shutil.copy2(p,q)
if (ROOT/'all_start_verification/margins.csv').exists():shutil.copy2(ROOT/'all_start_verification/margins.csv',HERE/'all50_start_audit.csv')
report=dict(files=files,qualification_logs=logfiles,closed_scored_calls=53,physics_steps=0,
    native_manifest_sha256=sha(V/'native_manifest.json'),compact_bytes=sum(r['bytes'] for r in files.values()),
    source_sha256=sha(Path(__file__)))
(HERE/'results/offline_return_inventory.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(files=len(files),bytes=report['compact_bytes'],qualification_logs=len(logfiles))))
