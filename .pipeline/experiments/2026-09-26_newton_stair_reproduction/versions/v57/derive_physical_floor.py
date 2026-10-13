"""Derive a separate physical-floor input remotely from verified pinned PCT bytes."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,pickle,sys
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
ROOT=Path('/home/sun/vla_exec/vla');assert ROOT.is_dir() and str(Path.cwd()).startswith(str(ROOT)),'Remote execution only'
BASE=ROOT/'.pipeline/experiments/2026-09-26_newton_stair_reproduction';PRODUCTS=BASE/'audits/2026-09-27_dense_static_sampling'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();receipt=json.loads((PRODUCTS/'receipt.json').read_text());raw_receipt=json.loads((PRODUCTS/'raw_receipt.json').read_text())
for name in ('map.pickle','map_float32.npz'):assert sha(PRODUCTS/name)==receipt['files'][name]
assert sha(PRODUCTS/'raw_cost_observation.npz')==raw_receipt['files']['raw_cost_observation.npz']
producer=BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py';frozen=json.loads((BASE/'versions/v52/manifest.json').read_text());assert sha(producer)==frozen['source_files'][str(producer.relative_to(ROOT))]
spec=importlib.util.spec_from_file_location('pinned_pct_producer',producer);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
source=pickle.loads((PRODUCTS/'map.pickle').read_bytes());precise=np.load(PRODUCTS/'map_float32.npz',allow_pickle=False)['data'];raw_cost=np.load(PRODUCTS/'raw_cost_observation.npz',allow_pickle=False)['raw_cost'];assert np.array_equal(precise.astype(np.float16),source['data'],equal_nan=True)
shadow=dict(source);shadow['data']=source['data'].copy();shadow['data'][0]=raw_cost.astype(np.float16)
selected=module.selected_ground_points(shadow,paired_elevations=precise[3]);physical=module.selected_ground_points(shadow,paired_elevations=precise[3],cost_limit=None);data=physical.astype('<f4').tobytes();assert len(physical)==150500 and hashlib.sha256(data).hexdigest()=='20acd5cf1ef156c5bd336b12651efe9a18e9959816905b05178ed44b1a181c96'
assert selected.astype('<f4').tobytes()==(PRODUCTS/'raw_ground.f32').read_bytes(),'Selected <=20 evidence must stay byte-identical'
# The production navigation publisher is separately pinned, with original elevation precision.
nav_source=module.load_pinned_map(BASE/'inputs/new_building.pickle');paired=module.load_paired_elevations(BASE/'inputs/new_building_original_precision.npz',nav_source);navigation=module.selected_ground_points(nav_source,paired_elevations=paired)
nav_file=BASE/'versions/v36/tests/attempt09/v33_stand/converted_inputs/ground.f32'
if nav_file.is_symlink() and str(nav_file.resolve()).startswith('/archive/'):nav_file=BASE/str(nav_file.resolve())[len('/archive/'):]
assert navigation.astype('<f4').tobytes()==nav_file.read_bytes(),'Production navigation bytes must equal original recorded input'
def fnv(data):
    h=14695981039346656037
    for v in data:h=((h^v)*1099511628211)&((1<<64)-1)
    return str(h)
assert not a.output.exists(),'Use a new asset directory';a.output.mkdir(parents=True)
(a.output/'physical_floor.f32').write_bytes(data)
records={'physical_floor.f32':{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'points':len(physical)}}
record={'role':'physical_floor_presence_only','traversal_authority':False,'terrain_return_classification_authority':False,'point_layout':'world x,y,z+0.03,cost; little-endian float32; no Support label','physical_source_id':'pct_physical_floor/fnv64/'+fnv(data),'selected_surface_source_id':'pct_tomogram/fnv64/'+fnv(selected.astype('<f4').tobytes()),'navigation_source_id':'pct_tomogram/fnv64/'+fnv(navigation.astype('<f4').tobytes()),'physical_resolution_m':float(source['resolution']),'physical_origin_x_m':float(physical[:,0].min())-float(source['resolution'])/2,'physical_origin_y_m':float(physical[:,1].min())-float(source['resolution'])/2,'physical_z_offset_m':0.03,'selected_surface_payload_sha256':hashlib.sha256(selected.astype('<f4').tobytes()).hexdigest(),'navigation_payload_sha256':hashlib.sha256(navigation.astype('<f4').tobytes()).hexdigest(),'inputs':{str((PRODUCTS/n).relative_to(ROOT)):sha(PRODUCTS/n) for n in ['map.pickle','map_float32.npz','raw_cost_observation.npz']},'producer':{'path':str(producer.relative_to(ROOT)),'sha256':sha(producer),'call':'selected_ground_points(shadow, paired_elevations=precise[3], cost_limit=None)'},'generator_sha256':sha(Path(__file__)),'host':'gpu5070ti','absolute_root':str(a.output),'files':records,'selected_surface_bytes_unchanged':True,'navigation_bytes_unchanged':True}
(a.output/'provenance.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
