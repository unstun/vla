"""Final unscored qualification, before the one complete scored cohort."""
from pathlib import Path
import hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
ROOT=Path('/home/sun/vla_exec/local_search_tracking_v285')
assert not (HERE/'native_manifest.json').exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for label,args in [('prepare03',['prepare.py']),('build03',['build.py']),('probe_build08',['run_native.py','build']),
                   ('terrain06',['run_native.py','terrain']),('contract02',['run_native.py','contract']),
                   ('continuity02',['run_native.py','continuity']),('unit02',['run_native.py','unit']),
                   ('regressions02',['regressions.py']),('development_cases02',['development_cases.py'])]:
    with (ROOT/(label+'.log')).open('x') as f:
        code=subprocess.run([sys.executable,str(HERE/args[0])]+args[1:],stdout=f,stderr=subprocess.STDOUT).returncode
    rows.append(dict(label=label,returncode=code,log_sha256=sha(ROOT/(label+'.log'))))
    (ROOT/'qualification_progress.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps(rows[-1]),flush=True)
    assert code==0,(label,code)
terrain=(ROOT/'terrain06.log').read_text();old=(ROOT/'parent_terrain05.log').read_text()
assert '"stair_directions_passed":2' in terrain and '"tangent_directions_passed":2' in terrain and '"unsupported_refused":1' in terrain
assert 'Ran out of pool' not in terrain and 'Ran out of pool' in old and '"stair_directions_passed":0' in old
assert '"phase_advanced":0' in (ROOT/'parent_continuity01.log').read_text()
assert '"coupled":4' in (ROOT/'continuity02.log').read_text() and '"phase_advanced":4' in (ROOT/'continuity02.log').read_text()
tests=[]
for base in [ROOT/'native/build/lite3_nav2_plugins/test_results',ROOT/'native/regressions']:
    for p in base.rglob('*.xml'):
        r=ET.parse(p).getroot();assert int(r.get('failures',0))==int(r.get('errors',0))==0,str(p)
        tests.append(dict(path=str(p),tests=int(r.get('tests',0)),sha256=sha(p)))
assert len(tests)>=20
cases=[]
for p in sorted((ROOT/'development02').glob('*/development.json')):
    row=json.loads(p.read_text());assert row['exit_code']==0 and row['metrics']['global_admitted']=='1' and row['metrics']['scan_published']=='1',row
    cases.append(row)
assert len(cases)==10
inventory=json.loads((ROOT/'native/source_inventory.json').read_text())
for p in (HERE/'src').rglob('*'):
    if p.is_file():assert sha(p)==inventory[str(p.relative_to(HERE))]
report=dict(passed=True,physics_steps=0,scored_calls=0,checks=rows,native_source_inventory_sha256=sha(ROOT/'native/source_inventory.json'),
            tests=tests,test_count=sum(r['tests'] for r in tests),stair_and_corner_directions=4,
            parent_stair_and_corner_directions=0,parent_pool_exhaustion_reproduced=True,
            positive_scaled_phase_and_translation=True,unsupported_layer_refused=True,unscored_cases=cases,
            parent_native_manifest_sha256=sha(HERE.parent/'v284/native_manifest.json'),
            claim='Native and unscored qualification only; complete scored benchmark and actual physical outcomes are separate')
(HERE/'qualification_report.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(passed=True,tests=report['test_count'],unscored_cases=10)))
