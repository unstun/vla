import copy,unittest
import numpy as np
from curve_overlay import Selection,sample_spline

class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.data=dict(run_id='r',epoch=1,request_id='q',goal_id='g',route_id='p',command_id='c',generation=1,map_epoch='m',map_revision=1,traj_id=1,order=3,
          start_time={'sec':10,'nanosec':0},pos_pts=[dict(x=float(i),y=0.,z=.3) for i in range(4)],knots=[float(i) for i in range(-3,5)],emergency_stop=False)
        self.selection=Selection()
    def event(self,kind,data):return dict(event=kind,data=data,host_wall_s=20.)
    def admit(self,data=None):
        d=copy.deepcopy(data or self.data);d.update(consumer='controller',status='accepted');self.selection.consume(self.event('scan_admission',d))
    def command(self):
        d=copy.deepcopy(self.data);d['stamp']={'sec':10,'nanosec':0};self.selection.consume(self.event('raw_command',d))
    def test_requires_controller_admission_and_fresh_owner_output(self):
        self.selection.consume(self.event('bspline',self.data));self.command();self.assertIsNone(self.selection.current(10.05))
        self.admit();self.assertIsNotNone(self.selection.current(10.05));self.assertIsNone(self.selection.current(9.99));self.assertIsNone(self.selection.current(10.101))
    def test_admission_before_spline_and_cancel(self):
        self.admit();self.command();self.selection.consume(self.event('bspline',self.data));self.assertIsNotNone(self.selection.current(10.05))
        wrong=copy.deepcopy(self.data);wrong['generation']=2;self.selection.consume(self.event('scan_cancel',wrong));self.assertIsNotNone(self.selection.current(10.05))
        self.selection.consume(self.event('scan_cancel',self.data));self.assertIsNone(self.selection.current(10.05));self.admit();self.assertIsNone(self.selection.current(10.05))
    def test_emergency_curve_never_shown(self):
        self.data['emergency_stop']=True;self.admit();self.command();self.selection.consume(self.event('bspline',self.data));self.assertIsNone(self.selection.current(10.05))
    def test_recorded_spline_has_expected_endpoints(self):
        points=sample_spline(self.data);np.testing.assert_allclose(points[[0,-1]],[[1,0,.3],[2,0,.3]],atol=1e-6)
        self.data['knots'][4]=self.data['knots'][3]
        with self.assertRaises(ValueError):sample_spline(self.data)
if __name__=='__main__':unittest.main()
