import unittest,numpy as np
from mesh_floor import mesh_floors

def plate(z,up=True,lo=0.,hi=1.):
 a=np.array([[[lo,lo,z],[hi,lo,z],[hi,hi,z]],[[lo,lo,z],[hi,hi,z],[lo,hi,z]]])
 return a if up else a[:,::-1]
class FiniteFloor(unittest.TestCase):
 def test_both_floor_and_body_headroom(self):
  r=mesh_floors(np.r_[plate(0),plate(.2,False),plate(.23)],.2,0,0)
  self.assertEqual(len(r),50)
  self.assertTrue(all(not q[4] if q[2]==0 else q[4] for q in r))
 def test_no_infinite_plane_extension(self):
  r=mesh_floors(plate(0,lo=.2,hi=.4),.1,0,0)
  self.assertEqual({q[:2] for q in r},{(2,2),(2,3),(3,2),(3,3)})
 def test_arbitrary_ramp_is_not_flattened(self):
  t=plate(0);t[:,:,2]=t[:,:,0]*.37
  r=mesh_floors(t,.2,0,0)
  for x,y,z,head,ok in r:self.assertAlmostEqual(z,(x+.5)*.2*.37);self.assertTrue(ok)
 def test_downward_faces_never_become_floors(self):
  self.assertEqual(mesh_floors(plate(0,False),.2,0,0),[])
if __name__=='__main__':unittest.main()
