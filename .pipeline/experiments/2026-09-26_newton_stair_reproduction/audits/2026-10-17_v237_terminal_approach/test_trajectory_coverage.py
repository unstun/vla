import unittest
from trajectory_coverage import active_gaps

def curve(pub,origin,duration,emergency=0):
    return dict(publication_s=pub,start_s=origin,duration_s=duration,emergency=emergency)

class ActiveTrajectoryTest(unittest.TestCase):
    def test_replaced_long_curve_cannot_hide_short_curve_expiry(self):
        result=active_gaps([curve(0,0,10),curve(2,2,1),curve(5,5,5)],0,8)
        self.assertEqual(result,[dict(start_s=3.,end_s=5.,reason='expired_active_curve',duration_s=2.)])
    def test_replan_failure_without_replacement_keeps_old_curve(self):
        self.assertEqual(active_gaps([curve(0,0,5),curve(4,4,4)],0,7),[])
    def test_emergency_message_has_no_executable_coverage(self):
        result=active_gaps([curve(0,0,10),curve(2,2,10,1),curve(4,4,5)],0,6)
        self.assertEqual(result[0]['reason'],'emergency_stop');self.assertEqual(result[0]['duration_s'],2)
    def test_future_origin_and_missing_initial_curve_are_visible(self):
        result=active_gaps([curve(1,2,5)],0,4)
        self.assertEqual({r['reason'] for r in result},{'future_origin','no_initial_curve'})
    def test_regressed_publication_is_invalid(self):
        with self.assertRaises(ValueError):active_gaps([curve(2,2,5),curve(1,1,5)],0,8)

if __name__=='__main__':unittest.main()
