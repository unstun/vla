import unittest,numpy as np,math
from mesh_geometry import MeshGeometry

def plate(x0,x1,z):return np.array([[[x0,-2,z],[x1,-2,z],[x1,2,z]],[[x0,-2,z],[x1,2,z],[x0,2,z]]])
class OriginalMeshOracle(unittest.TestCase):
 def test_open_floor_and_real_cliff(self):
  m=MeshGeometry(plate(-2,2,0));self.assertTrue(m.pose(0,0,0,0)[0]);self.assertFalse(m.pose(1.8,0,0,0)[0])
 def test_tall_wall_remains_a_solid(self):
  wall=np.array([[[0,-2,0],[0,2,0],[0,2,1]],[[0,-2,0],[0,2,1],[0,-2,1]]])
  m=MeshGeometry(np.r_[plate(-2,2,0),wall]);self.assertFalse(m.pose(-.3,0,0,0)[0]);self.assertTrue(m.pose(-1,0,0,0)[0])
 def test_steps_connect_symmetrically_without_absolute_height_band(self):
  m=MeshGeometry(np.r_[plate(-2,-.2,0),plate(-.2,.2,.2),plate(.2,2,.4)])
  self.assertTrue(m.pose(0,0,.2,0)[0]);self.assertTrue(m.pose(0,0,.2,math.pi)[0])
 def test_large_drop_cannot_join_floor_components(self):
  m=MeshGeometry(np.r_[plate(-2,0,0),plate(0,2,.4)]);self.assertFalse(m.pose(-.2,0,0,0)[0]);self.assertFalse(m.pose(.2,0,.4,math.pi)[0])
 def test_stacked_storeys_are_distinct(self):
  m=MeshGeometry(np.r_[plate(-2,2,0),plate(-2,2,3)]);floor=m.floor_connectivity.floor(0,0,0)
  self.assertTrue(floor.covers(__import__('shapely').geometry.Point(0,0)));self.assertTrue(m.pose(0,0,0,0)[0]);self.assertTrue(m.pose(0,0,3,0)[0])
if __name__=='__main__':unittest.main()
