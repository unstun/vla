"""Recover missing upward source planes before tomogram cost/slice reduction.

This is source evidence, not an unknown-support waiver. Existing selected
records stay byte-identical; the unchanged native fill/drop/step/body predicates
decide admission. A 5 cm grouping pitch is the original solid-source voxel
resolution, not another robot clearance or physical transition tolerance.
"""
from pathlib import Path
import collections,hashlib,json,math,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np
BASE=Path('/data/sun/vla_mppi_20261009');SRC=BASE/'generic_mechanisms_v259/native/fixtures/building'
DEST=BASE/'generic_mechanisms_v260/native/fixtures/building';DEST.mkdir(parents=True,exist_ok=True)
PCD=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/inputs/static_background/building2_9.pcd'
from upward_floor import upward_planes
data=PCD.read_bytes();marker=b'DATA binary\n';raw=np.frombuffer(data[data.index(marker)+len(marker):],dtype='<f4').reshape(-1,6)
with (SRC/'native.support').open() as f:header=f.readline().split()
res=float(header[1]);ox=float(header[5]);oy=float(header[6]);tolerance=float(header[8])
with (SRC/'static_solids.env').open() as f:voxel=2*float(f.readline().split()[-1])
planes=upward_planes(raw,res,ox,oy,voxel)
surface=np.fromfile(SRC/'surface.f32',dtype='<f4').reshape(-1,4);presence=np.fromfile(SRC/'physical_floor.f32',dtype='<f4').reshape(-1,4)
old=collections.defaultdict(list)
for p in surface:
 key=(math.floor((float(p[0])-ox)/res),math.floor((float(p[1])-oy)/res));old[key].append(float(p[2])-.03)
added=[];source_rows=[]
for ix,iy,z,count in planes:
 key=(int(ix),int(iy))
 if any(abs(h-z)<=tolerance for h in old[key]):continue
 added.append([ox+(ix+.5)*res,oy+(iy+.5)*res,z+.03,0.])
 old[key].append(float(z));source_rows.append(dict(cell=key,z=float(z),upward_source_returns=int(count)))
addition=np.array(added,dtype='<f4').reshape(-1,4)
for name,p in [('surface',surface),('physical_floor',presence)]:
 q=np.r_[p,addition].astype('<f4');assert q[:len(p)].tobytes()==p.tobytes();(DEST/f'{name}.f32').write_bytes(q.tobytes())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=dict(source_pcd_sha256=sha(PCD),source_normal_predicate='finite normal.Z > 32*float32_epsilon',
 method='Project original upward planes to canonical cell centers; group at original5cm source-voxel resolution; append only absent heights beyond unchanged native height-association tolerance',
 res=res,ox=ox,oy=oy,source_voxel_m=voxel,unchanged_height_association_tolerance_m=tolerance,
 original_source_returns=len(raw),source_upward_plane_records=len(planes),added_records=len(addition),
 original_selected_records_preserved=True,admission='unchanged guarded fill + ETH step + SupportGapMask + solid shape; no traversal authority is granted by source extraction alone',
 outputs={f'{name}.f32':dict(sha256=sha(DEST/f'{name}.f32'),bytes=(DEST/f'{name}.f32').stat().st_size) for name in ('surface','physical_floor')},added_source_records=source_rows)
def fnv(data):
 h=14695981039346656037
 for c in data:h=((h^c)*1099511628211)&((1<<64)-1)
 return str(h)
import yaml
params=yaml.safe_load((SRC.parent/'environment_candidate228.scan.yaml').read_text())
for section in params.values():
 if not isinstance(section,dict) or 'ros__parameters' not in section:continue
 q=section['ros__parameters']
 q['grid_map.physical_floor_source_id']='pct_physical_floor/fnv64/'+fnv((DEST/'physical_floor.f32').read_bytes())
 q['grid_map.physical_floor_surface_source_id']='pct_tomogram/fnv64/'+fnv((DEST/'surface.f32').read_bytes())
(DEST.parent/'environment_candidate228.scan.yaml').write_text(yaml.safe_dump(params))
(DEST/'upward_floor_source.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='added_source_records'}))

import shutil
snapshot=BASE/'generic_mechanisms_v260/candidate_export03/support/native.support'
assert snapshot.is_file()
shutil.copy2(snapshot,DEST/'native.support')
assert fnv((DEST/'native.support').read_bytes())=='13393923501932284827'
