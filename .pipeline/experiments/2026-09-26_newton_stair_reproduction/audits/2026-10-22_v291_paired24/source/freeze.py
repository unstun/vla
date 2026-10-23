"""Freeze both native/stance identities, scenarios, paired order and common runtime."""
from common import *
import time,yaml
manifest=BINDING/'campaign_manifest.json';assert not manifest.exists();verify()
preflight=json.loads((CAMPAIGN/'evidence/preflights01.json').read_text());assert preflight['passed'] and len(preflight['rows'])==8
request=json.loads((BINDING/'request.json').read_text());assert len(request['schedule'])==24
parity=[]
for case in ('D07','CD12','S04','A04'):
 a=CAMPAIGN/f'physical_runs/pair24_v290_{case}_r1_preflight01/graph_probe';b=CAMPAIGN/f'physical_runs/pair24_v291_{case}_r1_preflight01/graph_probe'
 for name in ('nav2_params.yaml','nav2_params.scan.yaml'):
  before=(a/name).read_text().replace(str(a),'RUN').replace(a.parent.name,'RUN')
  after=(b/name).read_text().replace(str(b),'RUN').replace(b.parent.name,'RUN')
  assert yaml.safe_load(before)==yaml.safe_load(after),(case,name)
  parity.append(dict(case_id=case,file=name,normalized_equal=True,parent_sha256=sha(a/name),candidate_sha256=sha(b/name)))
files={}
for p in BINDING.rglob('*'):
 if p.is_file() and '__pycache__' not in p.parts:files[str(p)]=sha(p)
parent=json.loads((OLD/'migration/physical_manifest01.json').read_text())
for rel,h in parent['files'].items():assert sha(OLD/rel)==h,rel;files[str(OLD/rel)]=h
for p in [OLD/'migration/physical_manifest01.json',OLD/'source/native_manifest.json',NEW/'source/native_manifest.json',OLD/'cohort/cases_manifest.json',CAMPAIGN/'evidence/preflights01.json']:
 files[str(p)]=sha(p)
cohort=json.loads((OLD/'cohort/cases_manifest.json').read_text());selected=['D07','CD12','S04','A04']+request['holdouts']
for cid in selected:
 record=next(c for c in cohort['cases'] if c['case_id']==cid);p=OLD/'cohort/cases'/cid/'scenario.json';assert sha(p)==record['scenario_sha256'];files[str(p)]=sha(p)
for variant,path in [('v290',VERSIONS/'v216'),('v291',NEW/'source')]:
 activation=json.loads((CAMPAIGN/'evidence'/f'{variant}_activation.json').read_text());assert activation['source_sha256']==sha(path/'stance_hold.py')
 for name in ('activate.py','newton_stance.py','stance_hold.py'):files[str(path/name)]=sha(path/name)
value=dict(schema=1,frozen=True,campaign='paired24-v291-v290',host='ultra9',frozen_utc_s=time.time(),authorized_physical_runs=24,
           request=request,profile_parity=parity,files=files,parent_native_sha256=sha(OLD/'source/native_manifest.json'),
           candidate_native_sha256=sha(NEW/'source/native_manifest.json'),preflight=preflight,
           claim='Frozen common execution binding; native and stance sources unchanged. Four holdouts selected but not run here.')
manifest.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(dict(passed=True,files=len(files),manifest_sha256=sha(manifest),physics_steps=0)))
