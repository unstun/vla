"""Verify one frozen native/bridge/benchmark source chain before each trial."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def verify_sources():
 report=load(HERE.parent/'v248/identity.py','original_bridge_chain').verify_sources()
 benchmark=load(HERE.parent/'v262/run_matrix.py','qualified_spatial_protocol');benchmark.verify()
 gate=json.loads((HERE.parent/'v262/results/offline_gate.json').read_text());assert gate['passed']
 selection=json.loads((HERE/'selection.json').read_text());assert selection['physical_admission_passed'] and len(selection['selected'])==10
 assert sha(HERE/'selection.json')==sha(HERE.parent/'v262/results/selection.json')
 for rel,h in json.loads((HERE/'source_identity.json').read_text())['files'].items():assert sha(HERE/rel)==h,rel
 binding=json.loads((HERE/'fixture_binding.json').read_text())
 assert binding['native_manifest_sha256']==sha(HERE.parent/'v261/manifest.json')
 root=BASE/'geometry_physical_v263'
 for rel,h in json.loads((HERE.parent/'v261/results/fixture_files.json').read_text()).items():assert sha(root/rel)==h,rel
 for name,h in binding['new_metadata'].items():assert sha(root/'fixtures/building'/name)==h,name
 report.update(native_source_version='v261',execution='v263',bridge_source_version='v248',
  native_manifest_sha256=sha(HERE.parent/'v261/manifest.json'),benchmark_manifest_sha256=sha(HERE.parent/'v262/manifest.json'),
  execution_source_identity=sha(HERE/'source_identity.json'),hard_collision_support_m=.35,sensor_period_s=.1,explicit_goal_heading=True,
  driver_source_sha256=sha(HERE.parent/'v257/long_route_driver.py'),navigation_active_before_goal_required=True)
 return report
