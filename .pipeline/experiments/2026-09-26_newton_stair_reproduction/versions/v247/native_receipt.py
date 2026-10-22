"""Collect only compact build/test/config identities; no build cache return."""
from pathlib import Path
import hashlib,json,shutil,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'physical_traversability_v247/native';OUT=BASE/'physical_traversability_v247/evaluation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
results=HERE/'results';results.mkdir(exist_ok=True)
for rel,h in json.loads((WORK/'source_inventory.json').read_text()).items():assert sha(WORK/rel)==h,rel
for p in (HERE/'src').rglob('*'):
 if p.is_file():assert sha(p)==sha(WORK/p.relative_to(HERE)),str(p)
files={str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and p.suffix!='.pyc' and '__pycache__' not in p.parts}
(results/'installed_files.json').write_text(json.dumps(files,indent=2)+'\n')
shutil.copy2(WORK/'source_inventory.json',results/'source_inventory.json');shutil.copy2(WORK/'fixture_receipt.json',results/'fixture_receipt.json')
reg=results/'regressions';reg.mkdir(exist_ok=True)
count=0
for p in (WORK/'regressions').glob('*.xml'):
 root=ET.parse(p).getroot();assert int(root.get('failures',0))==0 and int(root.get('errors',0))==0,p
 count+=int(root.get('tests',0));shutil.copy2(p,reg/p.name)
assert len(list(reg.glob('*.xml')))>=12
unit=results/'pct_unit';unit.mkdir(exist_ok=True)
for p in (WORK/'build/lite3_nav2_plugins/test_results').rglob('*.xml'):
 root=ET.parse(p).getroot();assert int(root.get('failures',0))==0 and int(root.get('errors',0))==0,p
 shutil.copy2(p,unit/p.name)
assert len(list(unit.glob('*.xml')))>=6

for p in BASE.glob('v247_*.log'):shutil.copy2(p,results/p.name)
shutil.copy2(OUT/'support/metrics.txt',results/'support_metrics.txt')
parity=dict(line.split('=',1) for line in (OUT/'support/metrics.txt').read_text().splitlines() if '=' in line)
assert int(parity['parity_queries'])>=10000 and parity['old_typed_mismatch']=='0' and parity['field_admission_mismatch']=='0'
historical=json.loads((OUT/'historical02/summary.json').read_text());assert historical['end_to_end_pass']
shutil.copy2(OUT/'historical02/summary.json',results/'historical_summary.json')
report=dict(passed=True,parent='v240',source_files=len(json.loads((WORK/'source_inventory.json').read_text())),installed_files=len(files),native_regression_test_cases=count,
 support_parity=parity,static_support_sha256=sha(OUT/'support/native.support'),static_support_fnv64=parity['snapshot_fnv64'],
 native_support_location=str(OUT/'support/native.support'),historical_chain_passed=True,
 policy_sha256=sha(BASE/'repo/.pipeline/experiments/2026-09-26_newton_macos_policy/policy/policy_stateless_h10.onnx'),
 hard_radius_m=.35,cylinder_offset_m=.18,sensor_period_s=.1,physical_steps=0)
(results/'native_receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
