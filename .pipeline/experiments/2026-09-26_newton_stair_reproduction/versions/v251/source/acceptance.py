"""Qualify frozen offline artifacts separately from the source/build receipt."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
WORK=BASE/'generic_mechanisms_v251/native';OUT=BASE/'generic_mechanisms_v251/evaluation'
spec=importlib.util.spec_from_file_location('matrix',HERE/'run_matrix.py')
matrix=importlib.util.module_from_spec(spec);spec.loader.exec_module(matrix);frozen=matrix.verify_frozen()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected={'controller':44,'environmental_cost':10,'executor_shutdown':1,'map_shell':1,
 'motion_exchange':8,'reference_path_utils':6,'shared_support':6,'static_support':1,
 'terminal_completion':9,'tracking_behavior':8,'tracking_parity':1,'uniform_bspline':2}
tests={};returned=HERE/'results/regressions';returned.mkdir(exist_ok=True)
for name,count in expected.items():
 p=WORK/'regressions'/('test_'+name+'.xml');root=ET.parse(p).getroot()
 assert int(root.get('tests',0))==count and int(root.get('failures',0))==0 and int(root.get('errors',0))==0,p
 tests[name]=count;shutil.copy2(p,returned/p.name)
 for ext in ('.log',):shutil.copy2(p.with_suffix(ext),returned/p.with_suffix(ext).name)
metrics={}
for line in (OUT/'support/metrics.txt').read_text().splitlines():
 if '=' in line:
  key,value=line.split('=',1);metrics[key]=value
for key,value in {'snapshot_cells':'110484','snapshot_fnv64':'1404261889151999461',
 'parity_queries':'10855','old_typed_mismatch':'0','field_admission_mismatch':'0'}.items():assert metrics[key]==value,(key,metrics.get(key))
historical=json.loads((OUT/'historical02/summary.json').read_text())
assert historical['end_to_end_pass'] and historical['first_gpmp_static_pass'] and historical['goal_max_error_m']<1e-5
summary=json.loads((OUT/'matrix_summary.json').read_text());calls=summary['calls']
assert len(calls)==60 and len(summary['by_case'])==12
assert all(item['denominator']==5 for item in summary['by_case'])
first=sum(item['first_gpmp_static_pass'] for item in calls)
assert first==55 and summary['passed_calls']>=50,(first,summary['passed_calls'])
assert all(not item['graph_fallback_attempted'] for item in calls if item['global_admitted'])
assert json.loads((OUT/'offline_gate.json').read_text())['passed']
replay=BASE/'generic_mechanisms_v249/g07_final01/frame02'
g07=json.loads((replay/'summary.json').read_text());gate=json.loads((replay/'final_gate.json').read_text())
assert g07['applied_published_scans']==910 and g07['physics_steps']==0
assert g07['map_digest']=='9ab177f8bb390a816810917626dd3e6e12e3cca97d9d7a8c8f663d914039c748'
assert gate['planned']==1 and gate['final_curve_status']==0 and gate['stale_ready']==0 and gate['stale_verdict']!=0
contract=json.loads((BASE/'generic_mechanisms_v251/gap_contract/summary.json').read_text())
assert contract['hard_domain_mismatches']==0 and contract['queries']==40000
inputs=[OUT/'matrix_summary.json',OUT/'offline_gate.json',OUT/'historical02/summary.json',
 OUT/'support/metrics.txt',replay/'summary.json',replay/'final_gate.json',
 BASE/'generic_mechanisms_v251/gap_contract/summary.json']
receipt=dict(version='v251',frozen_manifest_sha256=sha(HERE/'manifest.json'),passed=True,
 native_tests=tests,native_test_cases=sum(tests.values()),support_parity=metrics,
 scored_calls=60,first_gpmp_static_pass=first,end_to_end_pass=summary['passed_calls'],
 historical_first_gpmp=True,g07_saved_window_local_curve_clear=True,stale_negative_preserved=True,
 hard_radius_m=.35,sensor_period_s=.1,physics_steps=0,
 input_sha256={str(p):sha(p) for p in inputs},
 claim='Offline component admission and saved-window reconstruction; no new physical or scheduling validation')
(HERE/'results/acceptance_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt),flush=True)
