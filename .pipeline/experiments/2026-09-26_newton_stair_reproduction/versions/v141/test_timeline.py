import json,tempfile,unittest
from pathlib import Path
from full_timeline import load_rows
class TimelineTests(unittest.TestCase):
 def test_recorded_startup_then_wall_navigation(self):
  original=[{'physics_time_s':.1,'pose':[1],'controller_phase':'crouch'},{'physics_time_s':.2,'pose':[2],'controller_phase':'stand'},{'physics_time_s':.3,'wall_monotonic_s':10.,'pose':[3]},{'physics_time_s':.4,'wall_monotonic_s':10.1,'pose':[4]}]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'video_states.json').write_text(json.dumps(original));rows=load_rows(p)
  startup=[r for r in rows if r['timeline_segment']=='startup sim'];nav=[r for r in rows if r['timeline_segment']=='navigation wall 1:1']
  self.assertTrue(startup and nav);self.assertEqual(rows[0]['pose'],[1]);self.assertTrue(all('wall_monotonic_s' not in r for r in startup));self.assertEqual(nav[0]['wall_monotonic_s'],10.)
  for i,r in enumerate(rows):self.assertAlmostEqual(r['display_time_s'],i/30);self.assertEqual(r['pose'],original[r['source_state_index']]['pose'])
 def test_nonmonotonic_clock_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'video_states.json').write_text(json.dumps([{'physics_time_s':.1},{'physics_time_s':.3,'wall_monotonic_s':10},{'physics_time_s':.4,'wall_monotonic_s':9}]))
   with self.assertRaises(ValueError):load_rows(p)
if __name__=='__main__':unittest.main()
