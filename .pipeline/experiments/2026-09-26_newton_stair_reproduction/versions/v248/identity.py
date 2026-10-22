from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify_sources():
 p=HERE.parent/'v241/launch.py';spec=importlib.util.spec_from_file_location('original_host_gate',p)
 old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);report=old.verify_sources()
 native=HERE.parent/'v247';manifest=json.loads((native/'manifest.json').read_text())
 for rel,h in manifest['source_files'].items():assert sha(native/rel)==h,rel
 for name in ('source_inventory','installed_files'):
  for rel,h in json.loads((native/'results'/(name+'.json')).read_text()).items():assert sha(BASE/'physical_traversability_v247/native'/rel)==h,rel
 assert sha(BASE/'physical_traversability_v247/native/fixtures/building/native.support')==manifest['static_support_sha256']
 assert sha(BASE/'physical_traversability_v247/native/fixtures/building/terrain247.json')==json.loads((native/'results/fixture_receipt.json').read_text())['terrain_manifest_sha256']
 gate=json.loads((native/'results/offline_gate.json').read_text());assert gate['passed'] and gate['physical_representatives_admitted']==3
 for rel,h in json.loads((HERE/'source_identity.json').read_text())['files'].items():assert sha(HERE/rel)==h,rel
 for rel,h in json.loads((HERE/'results/bridge_installed_files.json').read_text()).items():assert sha(BASE/'physical_traversability_v248/native'/rel)==h,rel
 report.update(native_source_version='v247',execution='v248',native_manifest_sha256=sha(native/'manifest.json'),offline_gate_sha256=sha(native/'results/offline_gate.json'),execution_source_identity=sha(HERE/'source_identity.json'),hard_collision_support_m=.35,sensor_period_s=.1,navigation_active_before_goal_required=True)
 return report
