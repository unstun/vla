"""Diagnostic only: SciPy connected components anchored to old selected surfaces.
Edges join adjacent PCT cells within the existing 5 cm ground-association band.
No new ground elevations, free occupancy or obstacle-history clearing is added.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
HERE=Path(__file__).resolve().parent;BASE=HERE.parents[1]
def qualify(selected,raw):
 pairs=cKDTree(raw[:,:3].astype(float)).query_pairs(.150001,output_type='ndarray')
 d=np.abs(raw[pairs[:,0],:3].astype(float)-raw[pairs[:,1],:3].astype(float))
 pairs=pairs[(d[:,:2]<=.100001).all(1)&(d[:,2]<=.05)]
 g=coo_matrix((np.ones(len(pairs),dtype=np.uint8),(pairs[:,0],pairs[:,1])),shape=(len(raw),len(raw))).tocsr()
 n,labels=connected_components(g,directed=False)
 key=lambda p:tuple(p[:3].view(np.uint32))
 old={key(p) for p in selected};seeds=np.array([key(p) in old for p in raw]);assert int(seeds.sum())==len(old)
 anchored=np.unique(labels[seeds]);keep=np.isin(labels,anchored)
 assert keep[seeds].all()
 return raw[keep],{'components':int(n),'anchored_components':len(anchored),'old':len(selected),'raw':len(raw),'connected':int(keep.sum()),'excluded_unanchored':int((~keep).sum())}
def main():
 import importlib.util,sys,pickle
 p=BASE/'runtime_sources/bridge/lite3_sim_bridge/pct_sim_clock_core.py';spec=importlib.util.spec_from_file_location('ground_publisher_connected',p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
 selected=m.selected_ground_points(pickle.loads((BASE/'inputs/new_building.pickle').read_bytes()));raw=np.fromfile(HERE/'qualified_ground.f32',dtype='<f4').reshape(-1,4)
 points,info=qualify(selected,raw);points.tofile(HERE/'connected_ground.f32');info['sha256']=hashlib.sha256((HERE/'connected_ground.f32').read_bytes()).hexdigest();report={'building':info,'synthetic':{}}
 fixtures=BASE/'audits/2026-09-27_pct_ground_negatives'
 for name in json.loads((fixtures/'fixtures.json').read_text())['cases']:
  p=fixtures/name['case'];selected=np.fromfile(p/'ground.f32',dtype='<f4').reshape(-1,4);raw=np.fromfile(p/'qualified_ground.f32',dtype='<f4').reshape(-1,4);points,info=qualify(selected,raw);points.tofile(p/'connected_ground.f32');report['synthetic'][name['case']]=info
 (HERE/'connected_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
