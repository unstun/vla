"""Freeze the qualified v289 sources, single installation and unchanged cohort."""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/ubuntu/sun/vla_v289_20261020')
WORK=ROOT/'native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,indent=2)+'\n')

assert not (HERE/'native_manifest.json').exists()
inventory=json.loads((HERE/'source_inventory.json').read_text())
assert inventory==json.loads((WORK/'source_inventory.json').read_text())
for rel,digest in inventory.items():
    assert sha(HERE/rel)==sha(WORK/rel)==digest,rel
receipts={}
for name in ('build04_closed.json','components03.json','body_order_control01.json',
             'health_group_control03.json','current_geometry01.json','native_binding01.json','single_install_preflight01.json'):
    path=ROOT/'evidence'/name
    value=json.loads(path.read_text())
    assert value.get('passed',value.get('stage')=='passed'),name
    receipts[name]=sha(path)
# The parent must fail the intended assertions, rather than fail to compile.
for label in ('parent','candidate'):
    xml=ET.parse(ROOT/'body_order_control'/(label+'.xml')).getroot()
    assert int(xml.get('tests',0))==4
    assert int(xml.get('errors',0))==0
    assert (int(xml.get('failures',0))>0)==(label=='parent')

excluded={'cpplint.xunit.xml','uncrustify.xunit.xml','xmllint.xunit.xml'}
tests=[]
paths=list((WORK/'build').glob('*/test_results/*/*.xml'))+list((WORK/'regressions').glob('*.xml'))
for path in sorted(paths):
    if path.parent.name=='nav2_controller' and path.name in excluded:continue
    xml=ET.parse(path).getroot()
    assert not list(xml.iter('failure')) and not list(xml.iter('error')),str(path)
    tests.append(dict(path=str(path.relative_to(ROOT)),tests=len(list(xml.iter('testcase'))),sha256=sha(path)))
for name in ('test_body_time_buffer','test_replan_fsm_Safety','test_uniform_bspline',
             'test_controller','test_tracking_behavior','test_navigation_readiness'):
    assert any(name in row['path'] for row in tests),name

cohort=ROOT/'cohort'
m=json.loads((cohort/'cases_manifest.json').read_text())
assert m['positive_count']==m['distinct_spatial_pairs']==50 and m['illegal_controls']==3
fixtures={}
for case in m['cases']:
    folder=cohort/'cases'/case['case_id'];fixture=json.loads((folder/'fixture.json').read_text())
    assert fixture['physics_steps']==0 and fixture['max_scan_s']<=.1
    for rel,digest in fixture['files'].items():assert sha(folder/rel)==digest
    fixtures[case['case_id']]=sha(folder/'fixture.json')
results=HERE/'results'
installed={str(p.relative_to(WORK)):sha(p) for p in sorted((WORK/'install').rglob('*'))
           if p.is_file() and '__pycache__' not in p.parts}
evaluators={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'evaluation03/build').iterdir()
            if p.is_file() and p.name in ('native_probe','geometry_contract_probe','continuity_probe',
                'spawn_margin','terrain_search_probe','repair_probe','field_probe','work_probe')}
assert len(evaluators)==8
for name,value in (('installed_files',installed),('evaluator_files',evaluators),('native_tests',tests)):
    save(results/(name+'.json'),value)
save(HERE/'qualification_report.json',dict(passed=True,source_inventory_sha256=sha(HERE/'source_inventory.json'),
    receipts=receipts,test_records=len(tests),recorded_test_executions=sum(t['tests'] for t in tests),
    excluded_inherited_checks=sorted(excluded),physics_steps=0,
    claim='Functional package tests/probes; original Nav2 style/XML lint failures retained separately. Not physical acceptance.'))
files=dict(inventory)
for p in HERE.iterdir():
    if p.is_file() and p.name!='native_manifest.json':files[p.name]=sha(p)
parent=json.loads((HERE.parent/'v288/native_manifest.json').read_text())
manifest=dict(version='v289',parent_native='v288',parent_native_sha256=sha(HERE.parent/'v288/native_manifest.json'),
    frozen=True,source_files=files,source_inventory_sha256=sha(HERE/'source_inventory.json'),
    installed_inventory_sha256=sha(results/'installed_files.json'),evaluator_inventory_sha256=sha(results/'evaluator_files.json'),
    native_tests_sha256=sha(results/'native_tests.json'),cohort_sha256=sha(cohort/'cases_manifest.json'),
    fixtures=fixtures,physical_cases=m['physical_cases'],hard_radius_m=.35,sensor_period_s=.1,
    policy_sha256=parent['policy_sha256'],native_root=str(WORK),cohort_root=str(cohort),
    native_support_fnv64=parent['native_support_fnv64'],source_surface_descriptor_sha256=parent['source_surface_descriptor_sha256'],
    claim='Qualified single native/bridge prefix. Strict53 timing/geometry and ten physical outcomes remain separate.')
save(HERE/'native_manifest.json',manifest)
print(json.dumps(dict(frozen=True,source_files=len(files),tests=sum(t['tests'] for t in tests),manifest_sha256=sha(HERE/'native_manifest.json'))))
