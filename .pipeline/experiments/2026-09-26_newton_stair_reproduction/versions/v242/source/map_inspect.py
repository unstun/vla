"""Compact map view for case construction, not planning or admission."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

BASE = Path('/data/sun/vla_mppi_20261009')
FIX = BASE/'callback_failure_v232/fixtures/building'
OUT = BASE/'generalization_v242/discovery'

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    floor = np.fromfile(FIX/'physical_floor.f32', dtype='<f4').reshape(-1,4)
    raw_path=BASE/'environment_score_v224/fixtures/building/environment03.env'
    with raw_path.open() as stream:
        stream.readline();n=int(stream.readline().split()[1])
        for _ in range(n):stream.readline()
        n=int(stream.readline().split()[1])
        raw=np.array([list(map(float,stream.readline().split())) for _ in range(n)])
    report = dict(floor_sha256=hashlib.sha256((FIX/'physical_floor.f32').read_bytes()).hexdigest(),
        bounds=[floor[:,:3].min(0).tolist(),floor[:,:3].max(0).tolist()])
    values, counts = np.unique(np.round(floor[:,2],2),return_counts=True)
    report['height_modes'] = sorted(zip(values.tolist(),counts.tolist()),key=lambda r:-r[1])[:30]
    image = Image.new('RGB',(1300,750),'white');draw=ImageDraw.Draw(image)
    for panel,(low,high,title) in enumerate(((-.1,.3,'Downstairs'),(4.4,4.9,'Upstairs'))):
        ox=20+panel*650;oy=50;scale=28
        def xy(x,y):return (ox+(x+9)*scale,oy+(10-y)*scale)
        for x in range(-8,11):
            draw.line([xy(x,-10),xy(x,9)],fill='#eeeeee');draw.text(xy(x,9.7),str(x),fill='black')
        for y in range(-9,10):
            draw.line([xy(-8,y),xy(11,y)],fill='#eeeeee');draw.text(xy(-8.9,y),str(y),fill='black')
        for p in floor[(floor[:,2]>=low)&(floor[:,2]<=high)]:
            u,v=xy(*p[:2]);draw.rectangle((u-1,v-1,u+1,v+1),fill='#b8d5e9')
        level=.05804443359375 if panel==0 else 4.5330305099487305
        # Actual original PCD points in the torso's vertical band; no inflation.
        for p in raw[(raw[:,2]>=level+.10)&(raw[:,2]<=level+.85)]:
            u,v=xy(*p[:2]);draw.point((u,v),fill='#333333')
        draw.text((ox,15),title+' (world metres; physical floor blue)',fill='black')
    image.save(OUT/'floor_overview.png')
    (OUT/'map_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
