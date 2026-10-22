"""Unscored implementation checks; keep every revision's logs distinct."""
from pathlib import Path
import hashlib,json,os,subprocess,time
HERE=Path(__file__).resolve().parent;VERSION=HERE.parents[1]/'versions/v286'
ROOT=Path('/home/sun/vla_exec/supported_air_refinement_v286')
tag=os.environ.get('V286_DEVELOP_ID','01')
assert len(tag)==2 and tag.isdigit() and not (VERSION/'native_manifest.json').exists()
receipt=ROOT/f'development{tag}.json';assert not receipt.exists()
steps=[('prepare',['prepare.py']),('build',['build.py']),('probe_build',['run_native.py','build']),
    ('repair',['run_native.py','repair']),('terrain',['run_native.py','terrain']),
    ('continuity',['run_native.py','continuity']),('unit',['run_native.py','unit']),('regressions',['regressions.py'])]
row=dict(pid=os.getpid(),started_utc_s=time.time(),stage='running',physics_steps=0,checks=[])
reuse=os.environ.get('V286_REUSE_BUILD_ID')
if reuse:
    assert len(reuse)==2 and reuse.isdigit()
    previous=json.loads((ROOT/f'development{reuse}.json').read_text())
    inventory=json.loads((ROOT/'native/source_inventory.json').read_text())
    for source in (VERSION/'src').rglob('*'):
        if source.is_file():
            rel=str(source.relative_to(VERSION));expected=inventory[rel]
            assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
            assert hashlib.sha256((ROOT/'native'/rel).read_bytes()).hexdigest()==expected
    for label in ['prepare','build']:
        entry=next(r for r in previous['checks'] if r['label']==label)
        assert entry['returncode']==0 and hashlib.sha256(Path(entry['log']).read_bytes()).hexdigest()==entry['sha256']
        row['checks'].append(dict(entry,reused_from=f'development{reuse}'))
    steps=steps[2:]
row['source_inventory_sha256']=hashlib.sha256((ROOT/'native/source_inventory.json').read_bytes()).hexdigest()
receipt.write_text(json.dumps(row,indent=2)+'\n')
for label,args in steps:
    log=ROOT/f'{label}_development{tag}.log'
    with log.open('x') as stream:
        code=subprocess.run(['python3',str(VERSION/args[0])]+args[1:],stdout=stream,stderr=subprocess.STDOUT).returncode
    row['checks'].append(dict(label=label,returncode=code,log=str(log),sha256=hashlib.sha256(log.read_bytes()).hexdigest()))
    receipt.write_text(json.dumps(row,indent=2)+'\n')
    if code!=0:break
row.update(stage='passed' if len(row['checks'])==8 and code==0 else 'failed',finished_utc_s=time.time())
receipt.write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps(row))
