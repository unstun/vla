from pathlib import Path
import json,re
import numpy as np
from scipy.spatial.transform import Rotation
H=Path(__file__).resolve().parent
text=(H/'dense_prefix.log').read_text();centers=np.unique(np.array([[float(v) for v in m] for m in re.findall(r"\[BLOCKING_CONTRIBUTOR\].*?xyz=\s*([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)",text)]),axis=0)
ground=np.fromfile(H/'dense_inputs/ground.f32',dtype='<f4').reshape(-1,4);origin=ground[:,:2].astype(float).min(0)-.05;cells={}
for r in ground:
 k=tuple(np.floor((r[:2].astype(float)-origin)/.1).astype(int));cells.setdefault(k,[]).append(float(r[2])-.03)
rows=[]
for line,cloud in zip((H/'inputs/poses.txt').read_text().splitlines(),(H/'inputs/clouds.txt').read_text().splitlines()):
 stamp,bf,sf=line.split();s=np.loadtxt(H/'inputs'/sf);pts=np.fromfile(H/'inputs'/cloud,dtype='<f4').reshape(-1,3);world=Rotation.from_quat(s[3:7]).apply(pts)+s[:3]
 for i,c in enumerate(centers):
  hit=world[(np.abs(world-c)<.025000001).all(1)]
  for xyz in hit:
   k=tuple(np.floor((xyz[:2]-origin)/.1).astype(int));heights=cells.get(k,[]);near=min(heights,key=lambda z:abs(z-xyz[2])) if heights else None
   if near is not None and abs(xyz[2]-near)<=.05:continue
   rows.append({'voxel':int(i),'stamp_ns':int(stamp),'xyz':xyz.tolist(),'cell':list(map(int,k)),'nearest':near,'signed_height':None if near is None else float(xyz[2]-near),'neighbors':{str((dx,dy)):cells.get((k[0]+dx,k[1]+dy),[]) for dx,dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]}})
report={'centers':centers.tolist(),'points':rows,'origin':origin.tolist(),'claim':'Diagnostic nearest-height misses, including riser points that may still pass native associated-neighbor classification; not a native classifier clone.'};(H/'dense_raw_hits.json').write_text(json.dumps(report,indent=2)+'\n')
for i,c in enumerate(centers):
 sub=[r for r in rows if r['voxel']==i]
 print(i,c.tolist(),len(sub))
 if sub:print(sub[0])
