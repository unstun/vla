"""Original-map endpoint/heading coverage, with no inferred route lines."""
from pathlib import Path
import json
import numpy as np
from PIL import Image,ImageDraw
BASE=Path('/data/sun/vla_mppi_20261009');OUT=BASE/'space_coverage_v257';manifest=json.loads((OUT/'cases_manifest.json').read_text())
floor=np.fromfile(BASE/'callback_failure_v232/fixtures/building/physical_floor.f32',dtype='<f4').reshape(-1,4).astype(float);floor[:,2]-=.03
pcd=BASE/'repo/.pipeline/experiments/2026-09-26_newton_stair_reproduction/inputs/static_background/building2_9.pcd'
with pcd.open('rb') as f:
 while not f.readline().startswith(b'DATA '):pass
 cloud=np.fromfile(f,dtype='<f4').reshape(-1,6)
image=Image.new('RGB',(1840,1880),'white');d=ImageDraw.Draw(image);colors=dict(ascent='#1d4ed8',descent='#dc2626',intermediate='#15803d',same_floor='#a65e00',boundary='#7c3aed')
for panel,(level,title) in enumerate(((.058,'Ground floor'),(1.558,'Intermediate floor / lower turns'),(3.058,'Intermediate floor / upper turns'),(4.533,'Upper floor'))):
 ox=30+(panel%2)*920;oy=70+(panel//2)*910;scale=40
 def xy(x,y):return (ox+(x+8)*scale,oy+(9-y)*scale)
 for x in range(-8,12):d.line([xy(x,-10),xy(x,9)],fill='#eeeeee');d.text(xy(x,9.6),str(x),fill='black')
 for y in range(-10,10):d.line([xy(-8,y),xy(11,y)],fill='#eeeeee');d.text(xy(-8.6,y),str(y),fill='black')
 for p in floor[abs(floor[:,2]-level)<.09]:
  x,y=xy(*p[:2]);d.rectangle((x-1,y-1,x+1,y+1),fill='#d5e3ed')
 walls=cloud[(abs(cloud[:,5])<.3)&(cloud[:,2]>level+.05)&(cloud[:,2]<level+.8)]
 pixels=np.unique(np.round(walls[:,:2]*40).astype(int),axis=0)
 for p in pixels:
  x,y=xy(*(p/40));d.point((x,y),fill='#707070')
 for c in manifest['cases']:
  for which in ('start','goal'):
   p=c[which];x,y,z=p['ground']
   if abs(z-level)>=.1:continue
   u,v=xy(x,y);color=colors[c['stratum']];yaw=p['yaw'];tip=xy(x+.28*np.cos(yaw),y+.28*np.sin(yaw));d.line([(u,v),tip],fill=color,width=2)
   if which=='start':d.ellipse((u-4,v-4,u+4,v+4),fill=color)
   else:d.polygon([(u,v-5),(u-5,v+4),(u+5,v+4)],fill=color)
   label=c['case_id']+('S' if which=='start' else 'G')+('!' if c['expected']=='reject' and which=='goal' else '')
   d.text((u+5,v-8 if which=='start' else v+3),label,fill=color)
 d.text((ox,oy-45),title+f' (ground Z ~ {level:.3f} m)',fill='black')
d.text((30,1810),'52 distinct start positions + 52 distinct goals. Circles: start; triangles: goal; short lines: requested headings. !: predeclared illegal control.',fill='black')
d.text((30,1830),'Blue: ascent; red: descent; green: intermediate; brown: same-floor constrictions; purple: boundary/control. No route lines are implied.',fill='black')
d.text((30,1850),'Original physical floor and original PCD vertical normals shown for context; actual admission uses installed native support + solid geometry.',fill='black')
image.save(OUT/'coverage.png')
