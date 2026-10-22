"""Bind pre-score mesh requests, captured scans and a tested frozen native."""
from pathlib import Path
import hashlib,importlib.util,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'mesh_benchmark_v262'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE/'manifest.json').exists()
spec=importlib.util.spec_from_file_location('native_identity',HERE.parent/'v261/verify_frozen.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native);identity=native.verify()
cases=json.loads((OUT/'cases_manifest.json').read_text())
assert cases['positive_count']==cases['distinct_positive_tuples']==50 and cases['illegal_controls']>=3
assert cases['frozen_before_route_scoring'] and not cases['native_results_read']
assert not (OUT/'scored').exists()
assert sha(HERE/'construct.py')==cases['construction_source_sha256']
fixtures={}
for c in cases['cases']:
    folder=OUT/'cases'/c['case_id'];p=folder/'fixture.json';f=json.loads(p.read_text())
    assert f['physics_steps']==0 and f['max_scan_s']<=.1 and f['captured_state_unchanged']
    assert sha(folder/'scenario.json')==c['scenario_sha256']==f['scenario_sha256']
    assert sha(folder/'endpoints.txt')==c['endpoints_sha256']
    assert len((folder/'endpoints.txt').read_text().split())==8
    for name,h in f['files'].items():assert sha(folder/name)==h,(c['case_id'],name)
    if c['expected']=='admit':assert sha(OUT/'certificates'/(c['case_id']+'.json'))==c['mesh_certificate_sha256']
    fixtures[c['case_id']]=sha(p)
for name in ('cases_manifest.json','component_receipt.json','construction_proposals.json'):
    shutil.copy2(OUT/name,HERE/name)
shutil.copytree(OUT/'certificates',HERE/'results/mesh_certificates')
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('results','source','__pycache__') and p.name not in ('manifest.json','RESULTS.md') and '__pycache__' not in p.parts}
for rel in files:
    p=HERE/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/rel,p)
manifest=dict(version='v262',native='v261',frozen=True,source_files=files,
    native_manifest_sha256=identity['native_manifest_sha256'],cases_manifest_sha256=sha(HERE/'cases_manifest.json'),
    fixtures=fixtures,policy_golden_sha256=sha(OUT/'policy_golden.json'),
    original_mesh_sha256=cases['original_mesh_sha256'],calls_per_case=1,physical_attempts=0,
    hard_radius_m=.35,sensor_period_s=.1,scope='Pre-score benchmark freeze; native full-chain acceptance is separate')
(HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(manifest_sha256=sha(HERE/'manifest.json'),cases=len(fixtures),positive=50)),flush=True)
