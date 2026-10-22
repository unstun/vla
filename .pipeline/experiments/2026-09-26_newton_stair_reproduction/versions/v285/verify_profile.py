"""Original numerical gates with the explicitly authorized native-map ablation."""
from pathlib import Path
import hashlib,json,yaml
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent/'v233/verify_profile.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify(root):
 source=PARENT.read_text()
 before=' for key in old_pct:assert pct[key]==old_pct[key],(key,pct[key],old_pct[key])'
 assert source.count(before)==1
 source=source.replace(before," for key in old_pct:\n  if key!='map_bundle':assert pct[key]==old_pct[key],(key,pct[key],old_pct[key])")
 ns=dict(__file__=str(PARENT),__name__='original_numerical_profile')
 exec(compile(source,str(PARENT),'exec'),ns);report=ns['verify'](root)
 pct=report['pct'];assert pct['map_bundle']=='/work/fixtures/building/native_original.pct'
 assert pct['static_support_path']=='/work/fixtures/building/native.support'
 manifest=json.loads((HERE/'native_manifest.json').read_text())
 assert pct['static_support_fnv64']==manifest['native_support_fnv64']
 work=Path('/data/sun/vla_mppi_20261009/geometry_physical_v282/fixtures/building')
 inventory=json.loads((HERE.parent/'v280/results/fixture_files.json').read_text())
 assert sha(work/'native_original.pct')==inventory['fixtures/building/native_original.pct']
 assert sha(work/'native.support')==inventory['fixtures/building/native.support']
 receipt=dict(route_sha256=sha(work/'native_original.pct'))
 solid=json.loads((work/'source_surface282.json').read_text())
 native=yaml.safe_load((root/'nav2_params.scan.yaml').read_text())['scan_planner_node']['ros__parameters']
 assert pct['static_solid_path']==native['grid_map.static_solid_path']=='/work/fixtures/source_surface.env'
 assert pct['static_solid_fnv64']==native['grid_map.static_solid_fnv64']==solid['fnv64']
 assert solid['sha256']==sha(work.parent/'source_surface.env')==json.loads((HERE/'native_manifest.json').read_text())['source_surface_descriptor_sha256']
 for name,h in solid['dependencies'].items():assert sha(work.parent/name)==h,name
 report.update(static_solid_sha256=solid['sha256'],static_solid_fnv64=solid['fnv64'])
 report.update(original_numerical_verifier_sha256=sha(PARENT),authorized_native_map_sha256=receipt['route_sha256'],
  static_support_sha256=sha(work/'native.support'),configuration_changes='Restore native cost map; shared physical support; all original numerical gates retained')
 (root/'configuration_gate.json').write_text(json.dumps(report,indent=2)+'\n');return report
