"""Regenerate the exact qualified floor bytes from already verified local maps."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,pickle,sys
import numpy as np

HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1];ROOT=BASE.parents[2]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
info=json.loads((HERE/'physical_floor_input.json').read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert all(sha(ROOT/name)==digest for name,digest in info['inputs'].items())
producer=ROOT/info['producer']['path'];assert sha(producer)==info['producer']['sha256']
spec=importlib.util.spec_from_file_location('v68_pinned_floor_producer',producer)
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
products=BASE/'audits/2026-09-27_dense_static_sampling'
source=pickle.loads((products/'map.pickle').read_bytes())
precise=np.load(products/'map_float32.npz',allow_pickle=False)['data']
raw=np.load(products/'raw_cost_observation.npz',allow_pickle=False)['raw_cost']
assert np.array_equal(precise.astype(np.float16),source['data'],equal_nan=True)
shadow=dict(source);shadow['data']=source['data'].copy();shadow['data'][0]=raw.astype(np.float16)
selected=module.selected_ground_points(shadow,paired_elevations=precise[3])
assert selected.astype('<f4').tobytes()==(products/'raw_ground.f32').read_bytes()
physical=module.selected_ground_points(shadow,paired_elevations=precise[3],cost_limit=None)
data=physical.astype('<f4').tobytes();assert len(physical)==150500
assert hashlib.sha256(data).hexdigest()==info['files']['physical_floor.f32']['sha256']
assert not a.output.exists();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_bytes(data)
a.output.with_suffix('.provenance.json').write_text(json.dumps({
    'host':'Mac','role':info['role'],'traversal_authority':False,
    'terrain_return_classification_authority':False,'path':str(a.output),
    'sha256':sha(a.output),'bytes':len(data),'points':len(physical),
    'inputs':info['inputs'],'producer':info['producer'],'selected_surface_unchanged':True,
    'generator_sha256':sha(Path(__file__)),
},indent=2)+'\n')
print('V68_EXACT_PHYSICAL_INPUT_PASS',len(data),sha(a.output))
