"""Verify one frozen native/bridge/benchmark source chain before each trial."""
from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def verify_sources():
 report=load(HERE.parent/'v248/identity.py','original_bridge_chain').verify_sources()
 if (HERE/'manifest.json').exists():
  frozen=json.loads((HERE/'manifest.json').read_text())
  for rel,h in frozen['source_files'].items():assert sha(HERE/rel)==h,rel

 benchmark=load(HERE.parent/'v281/common.py','qualified_spatial_protocol');benchmark.verify()
 gate=json.loads((BASE/'source_integrated_benchmark_v281/clean50/offline_gate.json').read_text());assert gate['passed']
 selection=json.loads((HERE/'selection.json').read_text());assert selection['physical_admission_passed'] and len(selection['selected'])==10
 assert sha(HERE/'selection.json')==sha(BASE/'source_integrated_benchmark_v281/clean50/selection.json')
 for rel,h in json.loads((HERE/'source_identity.json').read_text())['files'].items():assert sha(HERE/rel)==h,rel
 binding=json.loads((HERE/'fixture_binding.json').read_text())
 assert binding['native_manifest_sha256']==sha(HERE.parent/'v280/manifest.json')
 root=BASE/'geometry_physical_v282'
 for rel,h in json.loads((HERE.parent/'v280/results/fixture_files.json').read_text()).items():assert sha(root/rel)==h,rel
 for name,h in binding['new_metadata'].items():assert sha(root/'fixtures/building'/name)==h,name
 report.update(native_source_version='v280',execution='v282',bridge_source_version='v248',
  native_manifest_sha256=sha(HERE.parent/'v280/manifest.json'),benchmark_manifest_sha256=sha(HERE.parent/'v281/manifest.json'),
  execution_source_identity=sha(HERE/'source_identity.json'),hard_collision_support_m=.35,sensor_period_s=.1,explicit_goal_heading=True,
  driver_source_sha256=sha(HERE.parent/'v257/long_route_driver.py'),navigation_active_before_goal_required=True)
 return report
