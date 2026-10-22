from pathlib import Path
import json,hashlib,xml.etree.ElementTree as ET
R=Path('/home/ubuntu/sun/vla_v288_20261020');V=R/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/versions/v288';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ['build09_closed.json','current_geometry01.json','trace_probe02.json','bridge248_01.json']:assert json.loads((R/'evidence'/name).read_text())['passed'],name
assert json.loads((R/'evidence/components10.json').read_text())['stage']=='passed'
inv=json.loads((V/'source_inventory.json').read_text())
for rel,h in inv.items():assert sha(R/'native'/rel)==sha(V/rel)==h,rel
cohort=json.loads((R/'cohort/cases_manifest.json').read_text());fixtures={}
for c in cohort['cases']:
 folder=R/'cohort/cases'/c['case_id'];f=json.loads((folder/'fixture.json').read_text());assert f['physics_steps']==0 and f['max_scan_s']<=.1
 for rel,h in f['files'].items():assert sha(folder/rel)==h,(c['case_id'],rel)
 fixtures[c['case_id']]=sha(folder/'fixture.json')
tests=[]
for folder in [R/'native/build/lite3_nav2_plugins/test_results',R/'native/regressions']:
 for p in sorted(folder.rglob('*.xml')):
  x=ET.parse(p).getroot();assert int(x.get('failures',0))==int(x.get('errors',0))==0,str(p)
  tests.append(dict(path=str(p.relative_to(R)),tests=int(x.get('tests',0)),sha256=sha(p)))
assert len(tests)==20 and sum(t['tests'] for t in tests)==178
out=dict(source_inventory_sha256=sha(V/'source_inventory.json'),tests=tests,fixtures=fixtures,cohort_sha256=sha(R/'cohort/cases_manifest.json'),physical_cases=cohort['physical_cases'],
 installed={str(p.relative_to(R/'native')):sha(p) for p in sorted((R/'native/install').rglob('*')) if p.is_file() and '__pycache__' not in p.parts},
 evaluators={str(p.relative_to(R)):sha(p) for p in (R/'evaluation03/build').iterdir() if p.is_file() and p.name in ['native_probe','geometry_contract_probe','continuity_probe','spawn_margin','terrain_search_probe','repair_probe','field_probe','work_probe']},
 evidence={name:sha(R/'evidence'/name) for name in ['build09_closed.json','components10.json','trace_probe02.json','current_geometry01.json','bridge248_01.json']})
assert len(out['evaluators'])==8
(R/'evidence/freeze_inputs03.json').write_text(json.dumps(out,indent=2)+'\n');print('Qualified source/install/evaluator inputs ready')
