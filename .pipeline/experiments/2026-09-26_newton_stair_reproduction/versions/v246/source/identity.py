from pathlib import Path
import hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009');WORK=BASE/'endpoint_connectivity_v244/native'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify_sources():
 p=HERE.parent/'v241/launch.py';spec=importlib.util.spec_from_file_location('v241_parent_gate',p);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
 report=old.verify_sources()
 frozen=HERE.parent/'v244';manifest=json.loads((frozen/'manifest.json').read_text())
 for rel,h in manifest['source_files'].items():assert sha(frozen/rel)==h,rel
 for group in ('source_inventory','installed_files'):
  for rel,h in json.loads((frozen/'results'/(group+'.json')).read_text()).items():assert sha(WORK/rel)==h,rel
 gate=json.loads((HERE.parent/'v245/results/protocol_offline_gate.json').read_text());assert gate['passed'] and gate['physical_representatives_admitted']==3
 for rel,h in json.loads((HERE/'source_identity.json').read_text())['files'].items():assert sha(HERE/rel)==h,rel
 report.update(native_source_version='v244',execution='v246',v244_manifest_sha256=sha(frozen/'manifest.json'),v244_offline_gate_sha256=sha(HERE.parent/'v245/results/protocol_offline_gate.json'),execution_source_identity=sha(HERE/'source_identity.json'),native_install=str(WORK/'install'),unchanged_scan_core='v240',hard_collision_support_m=.35,sensor_period_s=.1)
 return report
