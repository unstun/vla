from pathlib import Path
import json,hashlib
E=Path('.pipeline/experiments/2026-09-26_newton_stair_reproduction');V=E/'versions/v288';H=E/'audits/2026-10-20_v288_reentrant_work_terminal/ultra9';R='/home/ubuntu/sun/vla_v288_20261020';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (V/'native_manifest.json').exists()
f=json.loads((H/'evidence/freeze_inputs03.json').read_text());assert f['source_inventory_sha256']==sha(V/'source_inventory.json')
assert sum(t['tests'] for t in f['tests'])==178
results=V/'results';results.mkdir(exist_ok=False)
for n,d in [('installed_files',f['installed']),('evaluator_files',f['evaluators']),('native_tests',f['tests'])]:
 (results/(n+'.json')).write_text(json.dumps(d,indent=2)+'\n')
qualification=dict(version='v288',native_qualified=True,physics_steps=0,native_executions=178,env_checks=8,repair_checks=20,terrain_cases=4,tracking_clock_cases=4,fatal_signal_cases=5,work_entry_stress_calls=1000,legal_starts=50,source_inventory_sha256=sha(V/'source_inventory.json'),evidence=f['evidence'],claim='Native qualification; scored53 and ten physical outcomes separate')
(V/'qualification_report.json').write_text(json.dumps(qualification,indent=2)+'\n')
files={str(p.relative_to(V)):sha(p) for p in sorted(V.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
manifest=dict(version='v288',parent_native='v287',parent_native_sha256=sha(E/'versions/v287/native_manifest.json'),frozen=True,source_files=files,source_inventory_sha256=sha(V/'source_inventory.json'),
 cohort_sha256=f['cohort_sha256'],fixtures=f['fixtures'],physical_cases=f['physical_cases'],hard_radius_m=.35,sensor_period_s=.1,
 policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b',native_root=R+'/native',cohort_root=R+'/cohort',
 native_support_fnv64='15212154834549674106',source_surface_descriptor_sha256='7791fb6ee67a5128eb65bb93b3dc8fd7e9955e09ba4673c145f4a0a0b969535c',
 evaluator_inventory_sha256=sha(results/'evaluator_files.json'),installed_inventory_sha256=sha(results/'installed_files.json'),claim='Frozen v288 native/cohort; offline and physical acceptance must be reported separately')
geometry=json.loads((E/'versions/v286/native_manifest.json').read_text())
for key in ('native_support_fnv64','source_surface_descriptor_sha256'):manifest[key]=geometry[key]
(V/'native_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(frozen=True,files=len(files),manifest_sha256=sha(V/'native_manifest.json'),native_executions=178)))
