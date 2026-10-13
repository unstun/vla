"""Verify closed runs, exact native installs, and the compact return allowlist."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

TASK=Path('/data/sun/vla_mppi_20261009')
HERE=Path(__file__).resolve().parent
VERSION=HERE.parents[1]/'versions/v126'
RESULT=TASK/'results/step2_v126'
def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(4*1024**2),b''):digest.update(chunk)
    return digest.hexdigest()
subprocess.run([sys.executable,str(VERSION/'freeze_host.py'),'verify'],check=True)
count={}
for variant in ('baseline','candidate'):
    receipt=json.loads((RESULT/f'{variant}_receipt.json').read_text())
    for name,expected in receipt['files'].items():
        assert sha(TASK/Path(name).relative_to('/task'))==expected,name
    count[variant]=len(receipt['files'])
containers=subprocess.check_output(['docker','ps','--filter','name=v126-','--format','{{.Names}}'],text=True).strip()
assert not containers,containers
active=[]
for path in Path('/proc').glob('[0-9]*/cmdline'):
    try:cmd=path.read_bytes().replace(b'\0',b' ').decode(errors='replace')
    except OSError:continue
    if any(tag in cmd for tag in ('v126_baseline_attempt01','v126_candidate_attempt01')):active.append(cmd)
assert not active,active
mapping={}
for name in ('baseline_receipt.json','candidate_receipt.json','build.log','build.sh','build_request.json',
             'host_tests.log','host_tests02.log','native_graph_preflight.json','output_ownership_test.json'):
    mapping['component/'+name]=RESULT/name
for p in (RESULT/'contracts02').iterdir():
    if p.is_file() and p.suffix in ('.json','.log'):mapping['component/contracts/'+p.name]=p
mapping['component/early_retry_compile.log']=RESULT/'contracts01/retry.log'
mapping['postmortem.json']=RESULT/'postmortem.json'
for p in (RESULT/'comparison').rglob('*'):
    if p.is_file() and p.suffix in ('.json','.csv','.log'):
        mapping['physical/'+str(p.relative_to(RESULT/'comparison'))]=p
record={'passed':True,'host':'gpu5070ti','source_pairs':2833,'runtime_inputs':618,
        'native_receipt_files':count,'owned_containers':[],'owned_trial_processes':[],
        'files':{name:{'remote':str(path),'bytes':path.stat().st_size,'sha256':sha(path)}
                 for name,path in mapping.items()}}
record['total_return_bytes']=sum(x['bytes'] for x in record['files'].values())
(RESULT/'closeout_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k!='files'}))
