"""Pre-score geometric endpoint candidates; no route solver selection."""
from pathlib import Path
import json, math, shutil
import numpy as np

BASE=Path('/data/sun/vla_mppi_20261009')
OUT=BASE/'generalization_v242/discovery'
# Semantic anchors selected from pinned floor/PCD overview. Native pose screening
# chooses first nearest valid candidate, never fastest route or largest margin.
ANCHORS={
 'A01_s':(-5.5,7.4,0,-math.pi/2),'A01_g':(6.5,5.5,1,0),
 'A02_s':(-6.4,6.8,0,-math.pi/4),'A02_g':(5.3,4.5,1,0),
 'A03_s':(-4.5,7.1,0,-3*math.pi/4),'A03_g':(4.5,3.2,1,0),
 'A04_s':(-2.5,7.2,0,math.pi),'A04_g':(6.1,2.3,1,0),
 'G05_s':(-5.4,8.0,0,-math.pi/2),'G05_g':(-1.0,1.5,1,0),
 'G06_s':(-1.0,7.3,0,-2.3),'G06_g':(5.2,-5.0,1,0),
 'G07_s':(4.0,7.4,0,-2.8),'G07_g':(-4.0,-3.8,1,0),
 'B08_s':(2.0,7.4,0,-2.8),'B08_g':(-6.0,-3.0,1,0),
 'B09_s':(6.5,-4.5,1,math.pi/4),'B09_g':(7.7,-3.6,1,0),
 'R10_s':(6.3,4.5,1,math.pi/2),'R10_g':(-5.5,7.2,0,0),
 'R11_s':(-1.0,2.5,1,0),'R11_g':(-3.0,7.5,0,0),
 'R12_s':(-4.5,-3.5,1,math.pi/4),'R12_g':(1.0,7.6,0,0),
}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'selection_ledger.json').exists():
        history=OUT/'history01';history.mkdir(exist_ok=False)
        for name in ('candidates.json','poses.txt','selection_ledger.json'):
            shutil.copy2(OUT/name,history/name)
        shutil.copytree(OUT/'native',history/'native')
    floor=np.fromfile(BASE/'callback_failure_v232/fixtures/building/physical_floor.f32',dtype='<f4').reshape(-1,4)
    # Surface export has a declared +.03m map offset. Scenario ground removes it.
    offsets=sorted([(dx,dy) for dx in (-.4,-.2,0,.2,.4) for dy in (-.4,-.2,0,.2,.4)],
        key=lambda p:(p[0]*p[0]+p[1]*p[1],p))
    rows=[]
    for key,(x,y,level,yaw) in ANCHORS.items():
        z=.05804443359375 if level==0 else 4.5330305099487305
        pool=floor[np.abs(floor[:,2]-(z+.03))<.08]
        for rank,(dx,dy) in enumerate(offsets):
            index=np.argmin((pool[:,0]-x-dx)**2+(pool[:,1]-y-dy)**2)
            p=pool[index,:3].astype(float);p[2]-=.03
            rows.append(dict(id=f'{key}_{rank:02d}',anchor=key,rank=rank,ground=p.tolist(),yaw=yaw))
    (OUT/'candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
    (OUT/'poses.txt').write_text(''.join(f"{r['id']} "+' '.join(map(str,r['ground'][:2]+[r['ground'][2]+.3,r['yaw']]))+'\n' for r in rows))
    print(f'{len(rows)} geometric candidates; no route scoring')

if __name__=='__main__':main()
