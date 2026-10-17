"""Return compact evidence; retain heavy exports and original failed attempts."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET

work=Path('/data/sun/vla_mppi_20261009/environment_score_v224')
out=work/'receipts01'
out.mkdir()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def copy(path,relative=None):
    target=out/(relative or path.relative_to(work))
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(path,target)

for name in ('source_inventory.json','composition.json','saturation_inspection.json'):
    path=work/name
    if path.exists():copy(path)
for pattern in ('probe_attempt*.log','admission_attempt*.log','export_attempt*.log','tools_build*.log','field_oracle*.json'):
    for path in sorted(work.glob(pattern)):copy(path)
for path in sorted((work/'evidence').glob('attempt*/*.log')):copy(path)
for path in sorted((work/'build').glob('*/test_results/*/*.xml')):
    copy(path,Path('test_results')/path.parent.name/path.name)
for name in ('field_probe_output06','admission_output03'):
    for path in sorted((work/name).glob('*.csv')):copy(path)
for name in ('environment_candidate03.yaml','environment_candidate03.scan.yaml',
             'route_endpoints.txt','bench_poses.txt'):
    copy(work/'fixtures'/name)
copy(work/'fixtures/building/environment03.json')

artifacts={}
for pattern in ('fixtures/building/environment*.env','field_probe_output*/*.csv',
                'evidence/attempt*/*.log','install/*/lib/*.so','export_build/*probe'):
    for path in sorted(work.glob(pattern)):
        if path.is_file():artifacts[str(path.relative_to(work))]={'sha256':sha(path),'bytes':path.stat().st_size}
cases=[]
for path in (out/'test_results').rglob('*.xml'):
    for case in ET.parse(path).getroot().iter('testcase'):
        cases.append((case.attrib.get('classname'),case.attrib.get('name')))
(out/'execution_receipt.json').write_text(json.dumps({
    'remote_workspace':str(work),'docker_image':'sha256:5a41a25fb20b6e77ce890974cea27ee59d93533346eaf7df83f56e74303b4bd4',
    'physics_steps':0,'test_case_records':len(cases),'distinct_test_cases':len(set(cases)),
    'compiled_source_inventory_sha256':sha(work/'source_inventory.json'),
    'retained_remote_artifacts':artifacts,
    'admission_probe_scope':'actual PCT plugin against native STATIC_ONLY provider; original reference XYZ endpoints; explicit zero start/goal yaw; not recorded robot execution',
},indent=2)+'\n')
files={str(p.relative_to(out)):{'sha256':sha(p),'bytes':p.stat().st_size}
       for p in sorted(out.rglob('*')) if p.is_file()}
(out/'receipt_inventory.json').write_text(json.dumps(files,indent=2)+'\n')
print(json.dumps({'files':len(files),'bytes':sum(p['bytes'] for p in files.values()),
                 'test_cases':len(cases),'distinct':len(set(cases))}))
