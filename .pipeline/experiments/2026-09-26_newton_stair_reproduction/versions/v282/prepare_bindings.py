"""Qualified native bytes with refreshed physical publisher metadata only."""
from pathlib import Path
import hashlib,importlib.util,json,os,shutil
HERE=Path(__file__).resolve().parent;BASE=Path('/data/sun/vla_mppi_20261009')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def fnv(data):
    h=14695981039346656037
    for byte in data:h=((h^byte)*1099511628211)&0xffffffffffffffff
    return str(h)
spec=importlib.util.spec_from_file_location('qualified_benchmark',HERE.parent/'v281/common.py')
bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench);bench.verify()
gate=json.loads((BASE/'source_integrated_benchmark_v281/clean50/offline_gate.json').read_text());assert gate['passed']
source=BASE/'source_physical_integration_v280/native/fixtures';dest=BASE/'geometry_physical_v282/fixtures'
if not dest.exists():shutil.copytree(source,dest,copy_function=os.link)
inventory=json.loads((HERE.parent/'v280/results/fixture_files.json').read_text())
for rel,h in inventory.items():assert sha(dest.parent/rel)==h,rel
folder=dest/'building'
terrain=json.loads((folder/'terrain247.json').read_text())
for role,entry in terrain['clouds'].items():
    p=folder/entry['file'];data=p.read_bytes();entry.update(bytes=len(data),points=len(data)//16,sha256=sha(p),source_id=('pct_physical_floor' if role=='physical_floor' else 'pct_tomogram')+'/fnv64/'+fnv(data))
terrain['inherited_terrain247_provenance']=dict(terrain['provenance'])
terrain['provenance']['physical_floor']=terrain['clouds']['physical_floor']['sha256']
terrain['provenance'].update(original_terrain247_sha256=sha(folder/'terrain247.json'),
    mesh_floor_source_sha256=sha(folder/'mesh_floor_source.json'),
    actual_native_support_sha256=sha(folder/'native.support'),actual_native_support_fnv64='15212154834549674106')
terrain['binding_note']='Metadata refreshed for actual finite original-mesh floor augmentation; geometry bytes equal frozen v280. Original metadata retained.'
p=folder/'terrain282.json';p.write_text(json.dumps(terrain,indent=2)+'\n')
environment=json.loads((folder/'environment247.json').read_text())
environment.update(terrain_manifest_sha256=sha(p),original_environment_metadata_sha256=sha(folder/'environment247.json'),atlas_content_unchanged=True,
    binding_note='ENV225 bytes and scores unchanged; metadata binds the current physical publisher manifest, not an atlas regeneration.')
(folder/'environment282.json').write_text(json.dumps(environment,indent=2)+'\n')
# Add a separate source descriptor manifest; keep frozen voxel metadata intact.
field=dest/'source_surface.env'
assert sha(field)==json.loads((HERE.parent/'v280/manifest.json').read_text())['source_surface_descriptor_sha256']
source_metadata=dict(format='SURFACE271B',file='../source_surface.env',sha256=sha(field),fnv64=fnv(field.read_bytes()),
    native_version='v280',radius_m=.35,offset_m=.18,up_m=.55,down_m=.35,body_clearance_m=.3,
    dependencies={name:sha(dest/name) for name in ('source_triangles.f64','source_volumes.txt')},
    old_voxel_control_file='static_solids.env',old_voxel_control_sha256=sha(folder/'static_solids.env'))
(folder/'source_surface282.json').write_text(json.dumps(source_metadata,indent=2)+'\n')
receipt=dict(native_manifest_sha256=sha(HERE.parent/'v280/manifest.json'),fixture_inventory_sha256=sha(HERE.parent/'v280/results/fixture_files.json'),
    geometry_equal_frozen_native=True,new_metadata={name:sha(folder/name) for name in ('terrain282.json','environment282.json','source_surface282.json')},
    hard_radius_m=.35,sensor_period_s=.1,policy_sha256='7030ba4704ab1761e777ba2e268bb6070a1b245b9891bb6dc3c255414996581b')
(HERE/'fixture_binding.json').write_text(json.dumps(receipt,indent=2)+'\n')
selection=json.loads((BASE/'source_integrated_benchmark_v281/clean50/selection.json').read_text());assert selection['physical_admission_passed']
for name in ('selection.json','offline_gate.json'):
    p=BASE/'source_integrated_benchmark_v281/clean50'/name;d=HERE/('results' if name=='offline_gate.json' else '')/name;d.parent.mkdir(exist_ok=True);shutil.copy2(p,d)
for selected in selection['selected']:
    p=BASE/'mesh_benchmark_v262/cases'/selected['case_id']/'scenario.json';assert sha(p)==selected['scenario_sha256']
    d=HERE/'scenarios'/p.parent.name;d=d.with_suffix('.json');d.parent.mkdir(exist_ok=True);shutil.copy2(p,d)
print(json.dumps(receipt),flush=True)
