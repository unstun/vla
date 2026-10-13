"""Verify subcell floor holes in the existing static samples; no navigation edits."""
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
BASE=HERE.parents[1]
TASK=Path('/data/sun/vla_mppi_20261009')
sys.path.insert(0,str(BASE/'scripts'))
from scene_assets import building_mesh

def main():
    out=TASK/'results/v133_posture/floor01'
    out.mkdir(parents=True,exist_ok=False)
    geometry=json.loads((TASK/'results/v133_posture/geometry01/geometry.json').read_text())
    source=BASE/'audits/2026-09-27_dense_static_sampling/augmented_points.npy'
    pts=np.load(source,mmap_mode='r')
    samples=pts[(pts[:,0]>7)&(pts[:,0]<8.2)&(pts[:,1]>5.3)&(pts[:,1]<6.5)&(pts[:,2]>4.48)&(pts[:,2]<4.57)]
    tree=cKDTree(samples[:,:2])
    witnesses=[]
    for s in geometry['samples']:
        foot=s['feet'][0]
        d,i=tree.query(foot['xyz'][:2])
        witnesses.append({'time_s':s['time_s'],'FL_xyz':foot['xyz'],
            'nearest_surface_sample_xy_distance_m':float(d),'nearest_surface_sample':samples[i].tolist()})
    vertices,faces,_=building_mesh();tri=vertices[faces]
    area=tri[(tri[:,:,0].max(1)>7.2)&(tri[:,:,0].min(1)<8.2)&(tri[:,:,1].max(1)>5.5)&
             (tri[:,:,1].min(1)<6.5)&(tri[:,:,2].min(1)>4.45)&(tri[:,:,2].max(1)<4.57)]
    image=Image.new('RGB',(1100,1050),'white');draw=ImageDraw.Draw(image)
    def xy(p):return (int(70+(p[0]-7.2)*950),int(980-(p[1]-5.5)*950))
    for face in area:draw.polygon([xy(p) for p in face],fill='#d5dfe6',outline='#9aaebc')
    draw.rectangle((0,0,1100,45),fill='white');draw.text((30,12),'v133 failed run: original floor triangles and recorded feet; white = no floor at z 4.45..4.57m',fill='black')
    for index,color in [(1,'blue'),(3,'orange'),(5,'red')]:
        s=geometry['samples'][index]
        for f in s['feet']:
            x,y=xy(f['xyz']);draw.ellipse((x-5,y-5,x+5,y+5),fill=color)
            draw.text((x+7,y),f['leg']+' '+format(s['time_s'],'.2f'),fill=color)
    for x in np.arange(7.2,8.21,.1):
        a=xy((x,5.5));draw.text((a[0],995),format(x,'.1f'),fill='black')
    for y in np.arange(5.5,6.51,.1):
        a=xy((7.2,y));draw.text((10,a[1]),format(y,'.1f'),fill='black')
    image.save(out/'floor.png')
    report={'witnesses':witnesses,'points_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'geometry_sha256':hashlib.sha256((TASK/'results/v133_posture/geometry01/geometry.json').read_bytes()).hexdigest(),
        'claim':'Diagnostic exact mesh versus existing static point samples. No online truth injection.'}
    (out/'floor.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))

if __name__=='__main__':main()
