import unittest
from stop_metrics import summarize

def row(t,x,cmd=0,mode='STAND_SETTLING'):
 return dict(physics_time_s=t,body_sensor={'position':[x,0,.3]},effective_command=[cmd,0,0],stance_mode=mode)
class Metrics(unittest.TestCase):
 def test_max_not_net_and_pd_window(self):
  result=summarize([row(1,.10),row(2,.22),row(3,.18,mode='STAND_TRANSITION'),row(4,.15,mode='FIXED_STAND')],[0,0,0],0)['first']
  self.assertAlmostEqual(result['max_displacement_cm'],12);self.assertAlmostEqual(result['net_displacement_cm'],5);self.assertEqual(result['pd_delay_s'],2);self.assertFalse(result['pd_entry_censored'])
 def test_failure_before_goal_is_missing(self):
  result=summarize([row(1,2),row(2,1)],[0,0,0],0);self.assertFalse(result['terminal_seen']);self.assertIsNone(result['first'])
 def test_restart_preserves_first_and_censoring(self):
  result=summarize([row(1,.10),row(2,.20),row(3,.30,cmd=.1),row(4,.04),row(5,.05,mode='STAND_TRANSITION')],[0,0,0],0)
  self.assertEqual(len(result['episodes']),2);self.assertTrue(result['first']['pd_entry_censored']);self.assertTrue(result['first']['command_restarted']);self.assertAlmostEqual(result['first']['max_displacement_cm'],10);self.assertEqual(result['restart_count'],1)
 def test_initial_factory_zero_excluded(self):
  result=summarize([row(1,.02,mode='FIXED_STAND'),row(2,.1,cmd=.2),row(3,.02),row(4,.03)],[0,0,0],2)
  self.assertEqual(result['first']['start_s'],3);self.assertTrue(result['first']['pd_entry_censored'])
 def test_no_zero_after_capture_is_missing(self):
  self.assertIsNone(summarize([row(1,.1,cmd=.2)],[0,0,0],0)['first'])
 def test_invalid_time_rejected(self):
  with self.assertRaises(AssertionError):summarize([row(2,.1),row(1,.2)],[0,0,0],0)
if __name__=='__main__':unittest.main()
