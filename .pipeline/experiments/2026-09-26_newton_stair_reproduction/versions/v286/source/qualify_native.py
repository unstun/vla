"""Qualify closed native checks and unscored inputs; never count physics here."""
from pathlib import Path
import hashlib,json,os,re,subprocess,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;ROOT=Path('/home/sun/vla_exec/supported_air_refinement_v286')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'native_manifest.json').exists() and not (HERE/'qualification_report.json').exists()
reports=sorted(ROOT.glob('development[0-9][0-9].json'));assert reports
closed=json.loads(reports[-1].read_text());assert closed['stage']=='passed'
for item in closed['checks']:assert item['returncode']==0 and sha(Path(item['log']))==item['sha256']
parent_paths=sorted(ROOT.glob('parent_probe[0-9][0-9].json'));assert parent_paths
parent=json.loads(parent_paths[-1].read_text());assert parent['stage']=='parent_probe_closed'
assert parent['probe_source_sha256']==sha(HERE/'repair_probe.cpp')
assert [r['returncode'] for r in parent['checks']]==[0,1]
for item in parent['checks']:assert sha(Path(item['log']))==item['sha256']
old=Path(parent['checks'][1]['log']).read_text()
latest={r['label']:r for r in closed['checks']}
new=Path(latest['repair']['log']).read_text()
pattern=r'^REPAIR_CHECK ([a-z_]+)=([01])$'
before=dict(re.findall(pattern,old,re.M));after=dict(re.findall(pattern,new,re.M))
assert before.keys()==after.keys() and len(after)==13 and all(v=='1' for v in after.values())
assert sum(v=='0' for v in before.values())==6
for name in ['supported_unknown_air','supported_dynamic_height_air','nearest_endpoint_projection','goal_neighborhood_follows_terrain','refine_excludes_environment','source_buffer_rebound_gradient']:
 assert before[name]=='0' and after[name]=='1'
terrain=Path(latest['terrain']['log']).read_text();continuity=Path(latest['continuity']['log']).read_text()
assert '"stair_directions_passed":2' in terrain and '"tangent_directions_passed":2' in terrain and '"unsupported_refused":1' in terrain
assert '"coupled":4' in continuity and '"phase_advanced":4' in continuity
rows=[]
for label,args in [('contract01',['run_native.py','contract']),('initial_cases01',['development_cases.py'])]:
 path=ROOT/(label+'.log')
 with path.open('x') as log:code=subprocess.run(['python3',str(HERE/args[0])]+args[1:],stdout=log,stderr=subprocess.STDOUT).returncode
 rows.append(dict(label=label,returncode=code,log=str(path),sha256=sha(path)))
 (ROOT/'qualification_progress.json').write_text(json.dumps(rows,indent=2)+'\n')
 assert code==0,(label,code)
contract=(ROOT/'contract01.log').read_text();assert '"feedback_pass":12' in contract and '"local_wall_rejected":0' in contract
cases=[]
for p in sorted((ROOT/'initial_cases01').glob('*/development.json')):
 r=json.loads(p.read_text());assert r['exit_code']==0 and r['metrics']['global_admitted']=='1' and r['metrics']['scan_published']=='1',r
 cases.append(r)
assert len(cases)==10
tests=[]
for base in [ROOT/'native/build/lite3_nav2_plugins/test_results',ROOT/'native/regressions']:
 for path in base.rglob('*.xml'):
  r=ET.parse(path).getroot();assert int(r.get('failures',0))==int(r.get('errors',0))==0,str(path)
  tests.append(dict(path=str(path),tests=int(r.get('tests',0)),sha256=sha(path)))
assert len(tests)>=20
inventory=json.loads((ROOT/'native/source_inventory.json').read_text())
for p in (HERE/'src').rglob('*'):
 if p.is_file():assert sha(p)==inventory[str(p.relative_to(HERE))]
report=dict(passed=True,physics_steps=0,scored_calls=0,parent='v285',parent_manifest_sha256=sha(HERE.parent/'v285/native_manifest.json'),
 source_inventory_sha256=sha(ROOT/'native/source_inventory.json'),development_receipt_sha256=sha(reports[-1]),checks=closed['checks']+rows,
 repair_checks=after,parent_repair_checks=before,repair_checks_passed=13,parent_repair_failures=6,
 terrain_directions_retained=4,scaled_progress_clock_cases=4,tests=tests,test_count=sum(t['tests'] for t in tests),unscored_cases=cases,
 claim='Native qualification and unscored inputs only; all53 offline calls and ten physical attempts remain separate.')
(HERE/'qualification_report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,tests=report['test_count'],repaired_checks=13,unscored_cases=10)))
