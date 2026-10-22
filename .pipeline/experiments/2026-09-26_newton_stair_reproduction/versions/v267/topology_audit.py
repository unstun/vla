"""Exact source-edge closure audit, without coordinate welding tolerance."""
from pathlib import Path
import hashlib,json
import numpy as np
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'source_surface_native_v267'
p=BASE/'support_coverage_v134/triangles.f64';h=hashlib.sha256(p.read_bytes()).hexdigest()
assert h=='f3910b7c8106977d1f6e3364c464a9144c7946a0585c8cdcff4346d7add342fc'
t=np.fromfile(p,dtype='<f8').reshape(-1,3,3);vertices,ids=np.unique(t.reshape(-1,3),axis=0,return_inverse=True);faces=ids.reshape(-1,3)
e=np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]);sign=np.sign(e[:,1]-e[:,0]);e=e[sign!=0];sign=sign[sign!=0]
edges,index,counts=np.unique(np.sort(e,axis=1),axis=0,return_inverse=True,return_counts=True)
balance=np.bincount(index,weights=sign,minlength=len(edges)).astype(int);bad=np.flatnonzero(balance)
receipt=dict(source_triangles_sha256=h,triangles=len(t),exact_vertices=len(vertices),unique_edges=len(edges),
    coordinate_rounding_or_tolerance=False,oriented_boundary_edges=len(bad),closed_oriented_chain=len(bad)==0,
    unsigned_edge_valence_counts={str(k):int(v) for k,v in zip(*np.unique(counts,return_counts=True))},
    first_unbalanced_edges=[dict(vertices=vertices[edges[i]].tolist(),signed_balance=int(balance[i]),valence=int(counts[i])) for i in bad[:20]],
    scope='Algebraic oriented closure, not manifoldness or a dynamics certificate',physics_steps=0,planning_calls=0)
(OUT/'topology.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
