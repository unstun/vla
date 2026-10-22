"""Bind frozen v251 native, frozen v248 bridge and the original sensor/RL chain."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path)
 result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
def verify_sources():
 report=load(HERE.parent/'v248/identity.py','frozen_bridge_chain').verify_sources()
 native=HERE.parent/'v251';frozen=load(native/'run_matrix.py','qualified_native_chain').verify_frozen()
 qualified=json.loads((native/'results/acceptance_receipt.json').read_text())
 assert qualified['passed'] and qualified['first_gpmp_static_pass']==55
 assert qualified['frozen_manifest_sha256']==sha(native/'manifest.json')
 for rel,h in json.loads((HERE/'source_identity.json').read_text())['files'].items():assert sha(HERE/rel)==h,rel
 gate=json.loads((HERE/'results/offline_gate.json').read_text())
 assert gate['passed'] and gate['physical_representatives_admitted']==3
 assert sha(HERE/'results/offline_gate.json')==qualified['input_sha256'][str(BASE/'generic_mechanisms_v251/evaluation/offline_gate.json')]
 report.update(native_source_version='v251',execution='v252',bridge_source_version='v248',
  native_install=str(BASE/'generic_mechanisms_v251/native/install'),native_manifest_sha256=sha(native/'manifest.json'),
  native_qualification_sha256=sha(native/'results/acceptance_receipt.json'),
  execution_source_identity=sha(HERE/'source_identity.json'),hard_collision_support_m=.35,sensor_period_s=.1,
  navigation_active_before_goal_required=True)
 return report
