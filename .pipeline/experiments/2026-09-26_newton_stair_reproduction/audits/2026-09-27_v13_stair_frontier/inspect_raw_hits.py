from pathlib import Path
import json, numpy as np
from scipy.spatial.transform import Rotation
BASE=Path(__file__).resolve().parents[2]
D=BASE/'audits/2026-09-27_full_building_comparison/inputs'
ground=np.fromfile(D/'ground.f32',dtype='<f4').reshape(-1,4)
ground=ground[np.isfinite(ground).all(1)&(ground[:,3]<=20.)]
res=.1; origin=ground[:,:2].min(0)-res/2
cells={}
for row in ground:
 key=tuple(np.floor((row[:2]-origin)/res).astype(int));cells.setdefault(key,[]).append(float(row[2])-.03)
centers=np.array([[-5.425,4.875,.175],[-5.425,4.825,.225],[-5.425,4.825,.275],[-5.325,3.975,.425],[-5.325,3.975,.375],[-5.775,5.125,.175]])
records=[]
for line,cloudname in zip((D/'poses.txt').read_text().splitlines(),(D/'clouds.txt').read_text().splitlines()):
 stamp,bf,sf=line.split(); s=np.loadtxt(D/sf); points=np.fromfile(D/cloudname,dtype='<f4').reshape(-1,3);world=Rotation.from_quat(s[3:7]).apply(points)+s[:3]
 for i,c in enumerate(centers):
  hits=world[(np.abs(world-c)<.025000001).all(1)]
  for xyz in hits:
   key=tuple(np.floor((xyz[:2]-origin)/res).astype(int));heights=cells.get(key,[]);z0=min(heights,key=lambda x:abs(x-xyz[2])) if heights else None
   if z0 is None or abs(xyz[2]-z0)>.05:
    neighbors={str((dx,dy)):cells.get((key[0]+dx,key[1]+dy),[]) for dx,dy in [(0,0),(1,0),(-1,0),(0,1),(0,-1)]}
    records.append({'voxel':int(i),'stamp_ns':int(stamp),'xyz':xyz.tolist(),'cell':[int(x) for x in key],'nearest_ground':z0,'signed_height':None if z0 is None else float(xyz[2]-z0),'neighbors':neighbors})
out=Path(__file__).resolve().parent/'blocking_raw_hits.json';out.write_text(json.dumps({'centers':centers.tolist(),'origin':origin.tolist(),'points':records},indent=2)+'\n')
for i,c in enumerate(centers):
 rows=[r for r in records if r['voxel']==i];print('voxel',i,'bad_hits',len(rows),'signed_range',min([r['signed_height'] for r in rows if r['signed_height'] is not None],default=None),max([r['signed_height'] for r in rows if r['signed_height'] is not None],default=None));print(rows[:1])
