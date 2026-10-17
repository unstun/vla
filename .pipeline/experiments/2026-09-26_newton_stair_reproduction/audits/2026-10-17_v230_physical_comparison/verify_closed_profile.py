"""Check actual captured configuration, rather than relying on graph preflight alone."""
from pathlib import Path
import hashlib,json,yaml
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';RECEIPTS=OUT/'execution_receipts'
expected=json.loads((RECEIPTS/'configuration_gate.json').read_text())
native=yaml.safe_load((RECEIPTS/'nav2_params.scan.yaml').read_text())['scan_planner_node']['ros__parameters']
nav2=yaml.safe_load((RECEIPTS/'nav2_params.yaml').read_text())
for k,v in expected['native_shape_and_scoring'].items():assert native[k]==v,(k,native[k],v)
pct=nav2['planner_server']['ros__parameters']['PCT']
assert pct==expected['pct']
def flatten(value,prefix=''):
 result={}
 for k,v in value.items():
  key=prefix+k
  if isinstance(v,dict):result.update(flatten(v,key+'.'))
  else:result[key]=v
 return result
flat=flatten(nav2['controller_server']['ros__parameters'])
for k,v in expected['controller_gates'].items():assert flat[k]==v,(k,flat[k],v)
assert hashlib.sha256((RECEIPTS/'planner.yaml').read_bytes()).hexdigest()==expected['baseline_planner_sha256']
report={'passed':True,'context':'Actual closed physical-run capture compared with the SHA-bound preflight/original-v219 profile; no new physics.',
 'source_configuration':{n:hashlib.sha256((RECEIPTS/n).read_bytes()).hexdigest() for n in ('nav2_params.yaml','nav2_params.scan.yaml','planner.yaml')},
 'native_shape_and_scoring':expected['native_shape_and_scoring'],'pct':pct,'controller_gates':expected['controller_gates'],
 'validator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(OUT/'actual_profile_equivalence.json').write_text(json.dumps(report,indent=2)+'\n')
print('ACTUAL_CAPTURE_PROFILE_EQUIVALENCE passed')
