from pathlib import Path
import csv,json,os
os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from mesh_geometry import MeshGeometry
B=Path('/data/sun/vla_mppi_20261009');out=B/'generic_mechanisms_v260/evaluation/diagnosis'
mesh=MeshGeometry(np.fromfile(B/'support_coverage_v134/triangles.f64',dtype='<f8').reshape(-1,3,3))
for name in ('1_1','3_1'):
 a=np.genfromtxt(out/(name+'_visited.csv'),delimiter=',',names=True)
 print(name,'visited ranges', {k:[float(a[k].min()),float(a[k].max())] for k in ('x','y','z')},flush=True)
 r=np.genfromtxt(out/(name+'_rejected.csv'),delimiter=',',names=True)
 ground=r[(r['z']<.5)&(r['x']>6)&(r['y']>3)]
 for iy in np.arange(3.,7.51,.25):
  s=ground[(ground['y']>=iy)&(ground['y']<iy+.25)]
  if len(s):print('SLICE',name,iy,'n',len(s),'xspan',s['x'].min(),s['x'].max(),flush=True)
# Mesh all surface heights and triangle/normal witness for key corridor columns.
for y in (3.,4.,5.,5.5,5.8,6.,6.2,6.5):
 x=8.5
 print('MESH',x,y,mesh.heights(x,y),flush=True)
