from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');V=HERE.parent/'v247'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
remote=BASE/'physical_traversability_v247/evaluation'
gate=json.loads((remote/'offline_gate.json').read_text());selection=json.loads((remote/'selection.json').read_text())
assert gate['passed'] and selection['physical_admission_passed'] and len(selection['selected'])==3
for name in ('offline_gate.json','selection.json','matrix_table.csv','matrix_summary.json'):
 shutil.copy2(remote/name,V/'results'/name)
shutil.copy2(remote/'support/native.support',BASE/'physical_traversability_v247/native/fixtures/building/native.support')
shutil.copy2(remote/'selection.json',HERE/'selection.json')
for item in selection['selected']:
 source=BASE/'generalization_v242/cases'/item['case_id']/'scenario.json'
 assert sha(source)==item['scenario_sha256'];p=HERE/'scenarios'/source.parent.name;p=p.with_suffix('.json');p.parent.mkdir(exist_ok=True);shutil.copy2(source,p)
files={str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and p.relative_to(HERE).parts[0] not in ('results','source','__pycache__') and p.name not in ('manifest.json','source_identity.json','RESULTS.md') and '__pycache__' not in p.parts}
(HERE/'source_identity.json').write_text(json.dumps(dict(version='v248',native='v247',files=files,native_manifest_sha256=sha(V/'manifest.json'),offline_gate_sha256=sha(V/'results/offline_gate.json')),indent=2)+'\n')
print(json.dumps(selection),flush=True)
