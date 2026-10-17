"""Check generated execution settings against the actual v219 physics run."""
from pathlib import Path
import hashlib,json,sys,yaml
REMOTE=Path('/data/sun/vla_mppi_20261009')
EXPECTED_POLICY='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root):
 baseline=REMOTE/'trials/v219_linux_full_attempt01/runs/v219_linux_full_attempt01'
 assert (root/'planner.yaml').read_bytes()==(baseline/'planner.yaml').read_bytes()
 p=yaml.safe_load((root/'nav2_params.scan.yaml').read_text())['scan_planner_node']['ros__parameters']
 expected={'grid_map.double_cylinder_radius':.35,'grid_map.double_cylinder_offset':.18,
 'grid_map.obstacles_inflation_z_up':.55,'grid_map.obstacles_inflation_z_down':.35,
 'grid_map.reactive_body_clearance':.3,'optimization.lambda_environment':1.}
 for k,v in expected.items():assert p[k]==v,(k,p.get(k),v)
 params=yaml.safe_load((root/'nav2_params.yaml').read_text())
 old=yaml.safe_load((baseline/'nav2_params.yaml').read_text())
 pct=params['planner_server']['ros__parameters']['PCT'];old_pct=old['planner_server']['ros__parameters']['PCT']
 for key in old_pct:assert pct[key]==old_pct[key],(key,pct[key],old_pct[key])
 assert pct['reference_height']==.3 and pct['shared_traversability'] is True
 assert pct['environmental_path']==p['grid_map.environmental_path'] and pct['environmental_fnv64']==p['grid_map.environmental_fnv64']
 assert p['grid_map.environmental_fnv64']=='10040917858432847476'
 env=REMOTE/'callback_failure_v232/fixtures/building/environment225.env'
 assert sha(env)=='7ec06542ef9e2451fe63e89a3baf24d225aa3efcbe5ea025c287eb1b67bbdd84'
 policy=REMOTE/'repo/.pipeline/experiments/2026-09-26_newton_macos_policy/policy/policy_stateless_h10.onnx'
 assert sha(policy)==EXPECTED_POLICY
 # Paths name each run; scalar controller/goal/freshness values must remain equal.
 current=params['controller_server']['ros__parameters'];reference=old['controller_server']['ros__parameters']
 def flatten(value,prefix=''):
  result={}
  for k,v in value.items():
   key=prefix+k
   if isinstance(v,dict):result.update(flatten(v,key+'.'))
   else:result[key]=v
  return result
 old_flat=flatten(reference);new_flat=flatten(current)
 keys=[k for k in old_flat if any(t in k for t in ('tolerance','max_vel','max_speed','timeout','frequency','age','starvation'))]
 for k in keys:assert new_flat[k]==old_flat[k],(k,new_flat[k],old_flat[k])
 report={'passed':True,'native_shape_and_scoring':expected,'pct':pct,'controller_gates':{k:new_flat[k] for k in keys},
 'policy_sha256':sha(policy),'environment_sha256':sha(env),'baseline_planner_sha256':sha(baseline/'planner.yaml'),
 'generated_native_sha256':sha(root/'nav2_params.scan.yaml'),'generated_nav2_sha256':sha(root/'nav2_params.yaml'),'physics_steps':0}
 (root/'configuration_gate.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':print(json.dumps(verify(Path(sys.argv[1])),indent=2))
