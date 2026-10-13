"""Read-only inspection of pinned PCT products; write compact planning evidence."""
from pathlib import Path
import hashlib, importlib.util, json, pickle, sys
import numpy as np
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = ROOT/'.pipeline/experiments/2026-09-26_newton_stair_reproduction'
PRODUCTS = BASE/'audits/2026-09-27_dense_static_sampling'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
receipt = json.loads((PRODUCTS/'receipt.json').read_text())
raw_receipt = json.loads((PRODUCTS/'raw_receipt.json').read_text())
for name in ('map.pickle','map_float32.npz'):
    assert sha(PRODUCTS/name) == receipt['files'][name]
assert sha(PRODUCTS/'raw_cost_observation.npz') == raw_receipt['files']['raw_cost_observation.npz']
source = pickle.loads((PRODUCTS/'map.pickle').read_bytes())
precise = np.load(PRODUCTS/'map_float32.npz', allow_pickle=False)['data']
raw_cost = np.load(PRODUCTS/'raw_cost_observation.npz', allow_pickle=False)['raw_cost']
assert np.array_equal(precise.astype(np.float16), source['data'], equal_nan=True)
publisher_path = BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py'
frozen = json.loads((BASE/'versions/v52/manifest.json').read_text())
assert sha(publisher_path) == frozen['source_files'][str(publisher_path.relative_to(ROOT))]
spec = importlib.util.spec_from_file_location('pinned_pct_publisher', publisher_path)
module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
shadow = dict(source); shadow['data'] = source['data'].copy(); shadow['data'][0] = raw_cost.astype(np.float16)
selected = module.selected_ground_points(shadow, paired_elevations=precise[3])
physical = module.selected_ground_points(shadow, paired_elevations=precise[3], cost_limit=None)
queries = [('front',7.6261033725,-4.1288647524),('drop0',7.45468530655,-3.68681144714),('drop1',7.55468530655,-3.68681144714)]
rows = []
for name,x,y in queries:
    index = np.rint((np.array([x,y])-source['center'])/source['resolution']).astype(int)+np.array(source['data'].shape[2:])//2
    ix,iy = index.tolist(); xy=(index-np.array(source['data'].shape[2:])//2)*source['resolution']+source['center']
    def cell_points(points):
        mask=(abs(points[:,0]-xy[0])<1e-4)&(abs(points[:,1]-xy[1])<1e-4)
        return [dict(elevation_m=float(p[2]-.03),traversal_cost=float(p[3])) for p in points[mask]]
    rows.append(dict(name=name,query_xy=[x,y],index=[ix,iy],cell_xy=xy.tolist(),
        selected_evidence=cell_points(selected),physical_floor_presence=cell_points(physical),
        finite_layers=[dict(layer=i,ground_m=float(precise[3,i,ix,iy]),raw_cost=float(raw_cost[i,ix,iy]))
                       for i in range(len(raw_cost)) if np.isfinite(precise[3,i,ix,iy])]))
for r in rows[1:]:
    assert not any(abs(p['elevation_m']-1.583031)<.01 for p in r['selected_evidence'])
    assert any(abs(p['elevation_m']-1.583031)<.01 and p['traversal_cost']==50 for p in r['physical_floor_presence'])
output = dict(scope='Read-only planning evidence; no physical geometry, cost threshold, native support or runtime publisher changed',
    inputs={str((PRODUCTS/n).relative_to(ROOT)):sha(PRODUCTS/n) for n in ('map.pickle','map_float32.npz','raw_cost_observation.npz')},
    producer_sha256=sha(publisher_path),inspector_sha256=sha(Path(__file__)),
    selected_points=len(selected),physical_points=len(physical),queries=rows,
    physical_payload_candidate_sha256=hashlib.sha256(physical.astype('<f4').tobytes()).hexdigest(),
    physical_payload_candidate_bytes=int(physical.nbytes),payload_written=False)
(HERE/'pct_layers.json').write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps(dict(verified=True,selected_points=len(selected),physical_points=len(physical),
    input_role_gap='Cost-50 neighboring floors exist but are omitted from <=20 selected evidence',bulk_payload_written=False)))
