import unittest
import numpy as np
from upward_floor import upward_planes
class OriginalPlanes(unittest.TestCase):
 def test_lower_floor_is_not_replaced_by_overhead(self):
  p=np.array([[.02,.02,0,0,0,1],[.03,.03,1.5,0,0,1],[.02,.02,.5,1,0,0]],dtype=np.float32)
  a=upward_planes(p,.1,0.,0.,.05)
  self.assertEqual(sorted(a[:,2].tolist()),[0.,1.5])
 def test_ramp_projects_the_same_actual_plane(self):
  p=np.array([[.01,.01,.005,-.5,0,1],[.08,.01,.04,-.5,0,1]],dtype=np.float32)
  a=upward_planes(p,.1,0.,0.,.05)
  self.assertEqual(len(a),1);self.assertAlmostEqual(a[0,2],.025,6)
 def test_near_vertical_extrapolation_cannot_invent_height(self):
  p=np.array([[.001,.001,.2,1,0,.00001]],dtype=np.float32)
  self.assertEqual(len(upward_planes(p,.1,0.,0.,.05)),0)
 def test_nonfinite_and_downward_returns_do_not_grant_floor(self):
  p=np.array([[.02,.02,0,0,0,-1],[.02,.02,np.nan,0,0,1]],dtype=np.float32)
  self.assertEqual(len(upward_planes(p,.1,0.,0.,.05)),0)
if __name__=='__main__':unittest.main()
