"""Append finite original-mesh floors before native scoring; retain old bytes."""
from pathlib import Path
import collections,hashlib,json,math,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np,yaml
from mesh_floor import mesh_floors
BASE=Path('/data/sun/vla_mppi_20261009');SRC=BASE/'generic_mechanisms_v259/native/fixtures/building';DEST=BASE/'generic_mechanisms_v260/native/fixtures/building'
tri_path=BASE/'support_coverage_v134/triangles.f64';tri=np.fromfile(tri_path,dtype='<f8').reshape(-1,3,3)
with (SRC/'native.support').open() as f:header=f.readline().split()
res=float(header[1]);ox=float(header[5]);oy=float(header[6]);tolerance=float(header[8]);body_top=.3+.35
records=mesh_floors(tri,res,ox,oy,body_top);source_rows=[];outputs={}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name in ('surface','physical_floor'):
 p=np.fromfile(SRC/f'{name}.f32',dtype='<f4').reshape(-1,4);old=collections.defaultdict(list)
 for row in p:old[(math.floor((float(row[0])-ox)/res),math.floor((float(row[1])-oy)/res))].append(float(row[2])-.03)
 added=[]
 for ix,iy,z,headroom,standable in records:
  if name=='surface' and not standable:continue
  key=(ix,iy)
  if any(abs(h-z)<=tolerance for h in old[key]):continue
  added.append([ox+(ix+.5)*res,oy+(iy+.5)*res,z+.03,0.]);old[key].append(z)
  if name=='surface':source_rows.append(dict(cell=key,z=z,headroom_m=headroom if math.isfinite(headroom) else None))
 addition=np.asarray(added,dtype='<f4').reshape(-1,4);q=np.r_[p,addition].astype('<f4');assert q[:len(p)].tobytes()==p.tobytes();dest=DEST/f'{name}.f32';dest.write_bytes(q.tobytes());outputs[name]=dict(original_records=len(p),added_records=len(addition),sha256=sha(dest),bytes=dest.stat().st_size)
def fnv(data):
 h=14695981039346656037
 for c in data:h=((h^c)*1099511628211)&((1<<64)-1)
 return str(h)
params=yaml.safe_load((SRC.parent/'environment_candidate228.scan.yaml').read_text())
for section in params.values():
 if not isinstance(section,dict) or 'ros__parameters' not in section:continue
 q=section['ros__parameters'];q['grid_map.physical_floor_source_id']='pct_physical_floor/fnv64/'+fnv((DEST/'physical_floor.f32').read_bytes());q['grid_map.physical_floor_surface_source_id']='pct_tomogram/fnv64/'+fnv((DEST/'surface.f32').read_bytes())
(DEST.parent/'environment_candidate228.scan.yaml').write_text(yaml.safe_dump(params))
receipt=dict(original_newton_triangles=str(tri_path),original_newton_triangles_sha256=sha(tri_path),triangles=len(tri),method='Finite upward triangle intersections at canonical cell centers; source presence includes all recovered heights; selected candidates additionally require actual vertical chassis space. Original selected records remain byte-identical. Native fill/step/gap/solid checks retain all authority.',canonical_resolution_m=res,canonical_origin=[ox,oy],height_association_tolerance_m=tolerance,body_top_from_unchanged_clearance_plus_down_m=body_top,mesh_floor_records=len(records),outputs=outputs,added_selected_records=source_rows)
(DEST/'mesh_floor_source.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items() if k!='added_selected_records'}),flush=True)
