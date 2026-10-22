"""Independent float32 barycentric generation must fit the declared 3-D bound."""
import json,numpy as np
from registered_point_oracle import association,BASE
rng=np.random.default_rng(275);eligible=np.flatnonzero(np.isfinite(association.normal_bound)&(association.normal_bound<1.))
ids=rng.choice(eligible,5000,replace=True);weights=rng.dirichlet(np.ones(3),len(ids)).astype(np.float32)
tri=association.original[ids].astype(np.float32)
points=(weights[:,:,None]*tri).sum(axis=1,dtype=np.float32)
records=np.c_[points,association.original_normals[ids].astype(np.float32)].astype(np.float32)
failures=[];maximum_ratio=0.
for j,(i,r) in enumerate(zip(ids,records)):
    matches=association.matches(r);m=next((m for m in matches if m['face']==int(i)),None)
    if m is None:failures.append(dict(sample=j,face=int(i),record=r.astype(float).tolist()))
    else:maximum_ratio=max(maximum_ratio,m['distance']/m['error_bound'])
receipt=dict(samples=5000,failures=failures,max_distance_over_bound=maximum_ratio,seed=275,
    generation='float32 coefficient casts,3products+2adds on original source triangles',planning_calls=0,physics_steps=0)
(BASE/'source_point_diagnosis_v275/precision_controls.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(dict(samples=5000,failed=len(failures),max_distance_over_bound=maximum_ratio)),flush=True)
assert not failures
