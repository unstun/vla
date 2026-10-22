"""Freeze native source, installed bytes, evaluator and prospectively built cohort."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent;ROOT=Path('/home/sun/vla_exec/supported_air_refinement_v286')
WORK=ROOT/'native';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'native_manifest.json').exists()
inventory=json.loads((WORK/'source_inventory.json').read_text())
for rel,h in inventory.items():assert sha(WORK/rel)==h,rel
for p in (HERE/'src').rglob('*'):
    if p.is_file():assert sha(p)==inventory[str(p.relative_to(HERE))]
tests=[]
for directory in (WORK/'build/lite3_nav2_plugins/test_results',WORK/'regressions'):
    for p in directory.rglob('*.xml'):
        r=ET.parse(p).getroot();assert int(r.get('failures',0))==int(r.get('errors',0))==0,str(p)
        tests.append(dict(path=str(p),tests=int(r.get('tests',0)),sha256=sha(p)))
assert len(tests)>=20
qualification=json.loads((HERE/'qualification_report.json').read_text())
assert qualification['passed'] and qualification['source_inventory_sha256']==sha(WORK/'source_inventory.json')
cohort=ROOT/'cohort';m=json.loads((cohort/'cases_manifest.json').read_text())
assert m['construction_source_sha256']==sha(HERE.parent/'v283/construct_starts.py')
assert m['positive_count']==m['distinct_spatial_pairs']==50 and m['illegal_controls']==3
fixtures={}
for c in m['cases']:
    folder=cohort/'cases'/c['case_id'];f=json.loads((folder/'fixture.json').read_text())
    assert f['physics_steps']==0 and f['max_scan_s']<=.1
    for rel,h in f['files'].items():assert sha(folder/rel)==h,(c['case_id'],rel)
    if c['expected']=='admit':
        a=c['start_admission'];assert int(a['support_verdict'])==0 and min(float(a['edge_margin']),float(a['solid_margin']))>=.10
    fixtures[c['case_id']]=sha(folder/'fixture.json')
results=HERE/'results';results.mkdir(exist_ok=True)
for name in ('cases_manifest.json','start_admission.json'):
    shutil.copy2(cohort/name,HERE/name)
for label,data in [('native_source_inventory',inventory),('installed_files',{str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts}),('native_tests',tests)]:
    (results/(label+'.json')).write_text(json.dumps(data,indent=2)+'\n')
names=['prepare.py','build.py','run_native.py','run_matrix.py','freeze_native.py','geometry_contract_probe.cpp','spawn_margin.cpp','CMakeLists.txt','independent_source_audit.py','construct_starts.py','capture_cases.py','regressions.py','native_regressions.sh','cases_manifest.json','start_admission.json','parent_sources.json','native_changes.json','changes.patch','continuity_probe.cpp','reuse_cohort.py','development_cases.py','terrain_search_probe.cpp','qualification_report.json','qualify_native.py','repair_probe.cpp']
evaluators={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'evaluation/build').iterdir() if p.is_file() and p.name in ('native_probe','geometry_contract_probe','continuity_probe','spawn_margin','terrain_search_probe','repair_probe')}
assert len(evaluators)==6
(results/'evaluator_files.json').write_text(json.dumps(evaluators,indent=2)+'\n')
files={name:sha(HERE/name) for name in names}
files.update({str(p.relative_to(HERE)):sha(p) for p in (HERE/'src').rglob('*') if p.is_file()})
for rel in files:
    target=HERE/'source'/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,target)
manifest=dict(version='v286',parent_native='v285',parent_native_sha256=sha(HERE.parent/'v285/native_manifest.json'),frozen=True,source_files=files,
    evaluator_inventory_sha256=sha(results/'evaluator_files.json'),source_inventory_sha256=sha(results/'native_source_inventory.json'),installed_inventory_sha256=sha(results/'installed_files.json'),
    cohort_sha256=sha(HERE/'cases_manifest.json'),fixtures=fixtures,native_tests_sha256=sha(results/'native_tests.json'),
    physical_cases=m['physical_cases'],hard_radius_m=.35,sensor_period_s=.1,policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',
    native_root=str(WORK),cohort_root=str(cohort),claim='Frozen native/cohort; scored offline and physical outcomes are separate')
parent=json.loads((HERE.parent/'v280/manifest.json').read_text())
for key in ('native_support_fnv64','source_surface_descriptor_sha256'):
    manifest[key]=parent[key]
(HERE/'native_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(native_manifest_sha256=sha(HERE/'native_manifest.json'),tests=sum(t['tests'] for t in tests),cases=len(m['cases']))))
