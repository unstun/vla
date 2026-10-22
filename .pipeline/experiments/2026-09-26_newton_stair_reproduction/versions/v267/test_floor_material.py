"""A one-ULP source seam must not become a physical boundary waiver."""
import numpy as np
from shapely import STRtree
from shapely.geometry import Polygon
from finite_floor_material import floor_material

tri=np.array([[[0,0,0],[1,0,0],[1,1,0]],[[0,0,0],[1,1,0],[0,1,0]]],float)
tree=STRtree([Polygon(t[:,:2]) for t in tri])
one=np.nextafter(np.float32(1),np.float32(np.inf));far=one
for _ in range(7):far=np.nextafter(far,np.float32(np.inf))
records=np.array([[.5,.5,-.01,1,0,0],[one,.5,-.01,1,0,0],
    [far,.5,-.01,1,0,0],[.5,.5,.01,1,0,0],[.5,.5,.01,0,0,1],
    [.5,.5,.260001,0,0,1],[.5,.5,.3,0,0,1]],dtype=np.float32)
result=floor_material(records,tri,tree,0.).tolist()
assert result==[True,True,False,False,True,False,False],result
assert not floor_material(records,tri,tree,1.).any()
empty=STRtree([]);assert not floor_material(records,np.empty((0,3,3)),empty,0.).any()
print('source_material_controls=9 failures=0')
