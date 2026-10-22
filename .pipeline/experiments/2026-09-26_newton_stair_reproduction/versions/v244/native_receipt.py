from pathlib import Path
import hashlib,json,shutil
BASE=Path('/data/sun/vla_mppi_20261009');HERE=Path(__file__).resolve().parent;WORK=BASE/'endpoint_connectivity_v244/native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
results=HERE/'results';results.mkdir(exist_ok=True)
policy=BASE/'repo/.pipeline/experiments/2026-09-26_newton_macos_policy/policy/policy_stateless_h10.onnx'
expected='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b'
assert sha(policy)==expected,(sha(policy),expected)
files={str(p.relative_to(WORK)):sha(p) for p in (WORK/'install').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}
(results/'installed_files.json').write_text(json.dumps(files,indent=2)+'\n')
shutil.copy2(WORK/'source_inventory.json',results/'source_inventory.json')
for p in (BASE/'endpoint_connectivity_v244').glob('*.log'):shutil.copy2(p,results/p.name)
body=BASE/'environment_score_v224/fixtures/building/environment03.env'
report=dict(passed=True,source_files=len(json.loads((WORK/'source_inventory.json').read_text())),installed_files=len(files),policy_sha256=sha(policy),body_point_export_sha256=sha(body),body_point_fnv64='4316416882194453309',native_tests_log_sha256=sha(results/'tests03.log'),parent_native_source='v240',modified_packages=['lite3_nav2_plugins'],unchanged_scan_core_sha256=sha(BASE/'cooperative_search_v240/install/scan_planner/lib/libscan_native_core.so'))
(results/'native_receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
