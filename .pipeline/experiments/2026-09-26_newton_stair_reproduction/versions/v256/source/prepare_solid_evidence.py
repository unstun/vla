"""Correct pure upward material labels from the original PCD; geometry unchanged.

The legacy soft export's nearest-overlying-floor ranges can retain a horizontal
floor voxel as an ambiguous solid near stairs. Never promote that annotation
artifact into a hard wall. All source points in a voxel must face upward before
its actual sampled height range supplements the original below-floor volume association. Mixed,
vertical, downward and unclassified material is retained byte for byte.
"""
from pathlib import Path
import hashlib,json,math
import numpy as np
BASE=Path('/data/sun/vla_mppi_20261009');ROOT=BASE/'generic_mechanisms_v256';WORK=ROOT/'native'
old=BASE/'environment_score_v224/fixtures/building/environment03.env'
pcd=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/inputs/static_background/building2_9.pcd'
output=WORK/'fixtures/building/static_solids.env';receipt=WORK/'fixtures/building/static_solids.json'
assert not output.exists() and not receipt.exists()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with pcd.open('rb') as f:
 while True:
  line=f.readline()
  if line.startswith(b'DATA '):break
 assert line.split()[1]==b'binary'
 points=np.fromfile(f,dtype='<f4').reshape(-1,6)
assert np.isfinite(points).all()
key=np.floor(points[:,:3].astype(float)/.05).astype(np.int64)
keys,inverse=np.unique(key,axis=0,return_inverse=True)
# Only removes float32 normal-roundoff at nominally vertical faces. This is
# not a terrain slope or clearance threshold; every upward incline remains.
epsilon=float(32*np.finfo(np.float32).eps)
up=np.ones(len(keys),dtype=bool);np.logical_and.at(up,inverse,points[:,5]>epsilon)
low=np.full(len(keys),np.inf);high=-low.copy();np.minimum.at(low,inverse,points[:,2]);np.maximum.at(high,inverse,points[:,2])
lookup={tuple(k):(bool(u),float(lo),float(hi)) for k,u,lo,hi in zip(keys,up,low,high)}
changed=0;retained=0;total=0;records=[];changed_examples=[]
with old.open() as src,output.open('x') as dst:
 header=src.readline();dst.write(header.replace('ENV224B','SOLID256B',1));floor_header=src.readline();dst.write(floor_header)
 for _ in range(int(floor_header.split()[1])):dst.write(src.readline())
 count=src.readline();dst.write(count)
 for line in src:
  total+=1;parts=line.split();xyz=tuple(float(v) for v in parts[:3]);k=tuple(math.floor(v/.05) for v in xyz)
  # Every old solid voxel must map back to original source points.
  assert k in lookup,k
  pure,lo,hi=lookup[k]
  if pure:
   dst.write(line.rstrip()+f' {lo:.17g} {hi:.17g}\n');changed+=1
   if len(changed_examples)<12:changed_examples.append(dict(voxel_xyz=xyz,original_volume_association=parts[3:],additional_upward_surface_z=[lo,hi]))
  else:dst.write(line.rstrip()+' -1e100 -1e100\n');retained+=1

assert total==int(count.split()[1])
payload=output.read_bytes();fnv=14695981039346656037
for b in payload:fnv=((fnv^b)*1099511628211)&((1<<64)-1)
metadata=dict(format='SOLID256B',file=output.name,sha256=sha(output),fnv64=str(fnv),original_export=str(old),original_export_sha256=sha(old),original_pcd=str(pcd),original_pcd_sha256=sha(pcd),original_voxel_count=total,unchanged_voxel_geometry=True,unchanged_floor_channel=True,unchanged_original_volume_associations=True,pure_upward_surface_associations=changed,retained_other_records=retained,upward_normal_roundoff_epsilon=epsilon,changed_examples=changed_examples,classification='A voxel is same-floor material when its original below-floor volume association OR its additional pure-upward actual-source height band matches the queried floor. Original positions and association intervals are preserved; no previously valid material exemption is revoked. Mixed/vertical/downward voxels get no new exemption. Existing .26 m queried-floor rule and .35 m body geometry unchanged.',voxel_half_m=.025)
receipt.write_text(json.dumps(metadata,indent=2)+'\n')
env=WORK/'fixtures/probe225.env';lines=env.read_text().splitlines();kept=[s for s in lines if not s.startswith('export RAW_FIELD=') and not s.startswith('export RAW_FNV=')];kept+=['export RAW_FIELD=/work/fixtures/building/static_solids.env','export RAW_FNV='+str(fnv)];env.write_text('\n'.join(kept)+'\n')
print(json.dumps(metadata,indent=2),flush=True)
